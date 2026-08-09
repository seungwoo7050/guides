from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .checkpoint import OperationLedger
from .errors import ContractError, OperationConflict, PolicyDenied
from .git_adapter import GitAdapter
from .patching import PatchEngine, canonical_path
from .policy import PolicyEngine
from .process import ProcessRunner
from .types import CommandRequest, PatchArtifact, ToolReceipt, ToolRequest
from .util import value_digest


KnowledgeSearch = Callable[[str, Sequence[str], int], Sequence[Mapping[str, Any]]]


class ToolGateway:
    """The only model-facing dispatcher for repository, patch, and process effects.

    ``knowledge_search`` is dependency-injected so retrieval authority remains
    separate from repository-file authority.  It receives ``(query, scopes,
    limit)`` only after ``PolicyEngine`` approves every requested scope.
    """

    def __init__(
        self,
        workspace: Path,
        *,
        policy: PolicyEngine,
        patch_engine: PatchEngine,
        process_runner: ProcessRunner | None = None,
        git_adapter: GitAdapter | None = None,
        knowledge_search: KnowledgeSearch | None = None,
        state_dir: Path | None = None,
        max_read_bytes: int = 1_000_000,
        max_results: int = 200,
    ) -> None:
        self.workspace = workspace.resolve(strict=True)
        if policy.workspace != self.workspace or patch_engine.workspace != self.workspace:
            raise ContractError("gateway, policy, and patch engine must share one workspace")
        if process_runner is not None and process_runner.workspace != self.workspace:
            raise ContractError("process runner workspace differs from gateway workspace")
        if git_adapter is not None and git_adapter.workspace != self.workspace:
            raise ContractError("Git adapter workspace differs from gateway workspace")
        if isinstance(max_read_bytes, bool) or not isinstance(max_read_bytes, int) or max_read_bytes <= 0:
            raise ContractError("max_read_bytes must be a positive integer")
        if isinstance(max_results, bool) or not isinstance(max_results, int) or max_results <= 0:
            raise ContractError("max_results must be a positive integer")
        self.policy = policy
        self.patch_engine = patch_engine
        self.process_runner = process_runner
        self.git_adapter = git_adapter
        self.knowledge_search = knowledge_search
        self.max_read_bytes = max_read_bytes
        self.max_results = max_results
        self.ledger = OperationLedger(state_dir / "tool-operations.json") if state_dir is not None else None
        self._memory_operations: dict[str, tuple[str, ToolReceipt]] = {}

    def invoke(self, request: ToolRequest) -> ToolReceipt:
        if not request.request_id or not request.principal or not request.tool:
            raise ContractError("tool request identity, principal, and tool are required")
        if request.operation_id == "" or request.approval_id == "":
            raise ContractError("operation_id and approval_id must be null or non-empty")
        if not isinstance(request.arguments, Mapping):
            raise ContractError("tool arguments must be an object")
        tool = request.tool.lower()
        try:
            fingerprint = value_digest(
                {
                    "principal": request.principal,
                    "tool": tool,
                    "arguments": dict(request.arguments),
                    "approval_id": request.approval_id,
                }
            )
        except (TypeError, ValueError) as exc:
            raise ContractError("tool arguments must be canonical JSON values") from exc
        if request.operation_id:
            duplicate = self._lookup_operation(request.operation_id, fingerprint)
            if duplicate is not None:
                return ToolReceipt(**{**asdict(duplicate), "duplicate": True})

        output, effect, resource = self._dispatch(tool, request)
        receipt = ToolReceipt(
            receipt_id="receipt-" + value_digest(
                {"request_id": request.request_id, "fingerprint": fingerprint, "output": output}
            ).removeprefix("sha256:")[:24],
            tool=tool,
            status="OK",
            effect=effect,
            resource=resource,
            output=output,
            duplicate=False,
        )
        if request.operation_id:
            self._record_operation(request.operation_id, fingerprint, receipt)
        return receipt

    def _lookup_operation(self, operation_id: str, fingerprint: str) -> ToolReceipt | None:
        if self.ledger is not None:
            existing = self.ledger.begin(operation_id, fingerprint=fingerprint, details={"gateway": "ToolGateway"})
            if existing["fingerprint"] != fingerprint:
                raise OperationConflict("operation ID reused with different tool input")
            if existing.get("status") == "COMPLETED":
                return ToolReceipt(**existing["receipt"])
            return None
        existing = self._memory_operations.get(operation_id)
        if existing is None:
            return None
        previous_fingerprint, receipt = existing
        if previous_fingerprint != fingerprint:
            raise OperationConflict("operation ID reused with different tool input")
        return receipt

    def _record_operation(self, operation_id: str, fingerprint: str, receipt: ToolReceipt) -> None:
        if self.ledger is not None:
            self.ledger.complete(operation_id, receipt=asdict(receipt))
        else:
            self._memory_operations[operation_id] = (fingerprint, receipt)

    def _dispatch(self, tool: str, request: ToolRequest) -> tuple[Mapping[str, Any], str, str | None]:
        arguments = dict(request.arguments)
        purpose = arguments.pop("purpose", None)
        if purpose is not None and not isinstance(purpose, str):
            raise ContractError("tool purpose must be a string")
        if tool == "repository_status":
            self._expect_only(arguments, ())
            if self.git_adapter is None:
                raise ContractError("repository_status requires a GitAdapter")
            self._authorize_root_read(request.principal, purpose=purpose)
            return dict(self.git_adapter.status()), "READ", str(self.workspace)
        if tool == "show_diff":
            if self.git_adapter is None:
                raise ContractError("show_diff requires a GitAdapter")
            staged = arguments.pop("staged", False)
            paths = arguments.pop("paths", ())
            self._expect_only(arguments, ())
            if not isinstance(staged, bool) or not self._string_sequence(paths):
                raise ContractError("show_diff expects boolean staged and string paths")
            if paths:
                for path in paths:
                    self.policy.authorize_read(request.principal, path, purpose=purpose)
            else:
                self._authorize_root_read(request.principal, purpose=purpose)
            diff = self.git_adapter.diff(staged=staged, paths=paths)
            return {"diff": diff, "digest": value_digest({"diff": diff})}, "READ", str(self.workspace)
        if tool == "read_file":
            path = self._required_string(arguments, "path")
            limit = arguments.pop("max_bytes", self.max_read_bytes)
            start_line = arguments.pop("start_line", 1)
            end_line = arguments.pop("end_line", None)
            self._expect_only(arguments, ())
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0 or limit > self.max_read_bytes:
                raise ContractError("invalid read byte limit")
            if (
                isinstance(start_line, bool)
                or not isinstance(start_line, int)
                or start_line < 1
                or (
                    end_line is not None
                    and (isinstance(end_line, bool) or not isinstance(end_line, int) or end_line < start_line)
                )
            ):
                raise ContractError("invalid read line range")
            resource = self.policy.authorize_read(request.principal, path, purpose=purpose)
            item = dict(self.patch_engine.read(path, max_bytes=limit))
            lines = str(item["content"]).splitlines(keepends=True)
            item["content"] = "".join(lines[start_line - 1 : end_line])
            item["start_line"] = start_line
            item["end_line"] = min(len(lines), end_line if end_line is not None else len(lines))
            return item, "READ", resource
        if tool == "list_files":
            base = arguments.pop("path", ".")
            limit = arguments.pop("limit", arguments.pop("max_results", self.max_results))
            self._expect_only(arguments, ())
            if (
                not isinstance(base, str)
                or isinstance(limit, bool)
                or not isinstance(limit, int)
                or not 0 < limit <= self.max_results
            ):
                raise ContractError("invalid list_files arguments")
            return self._list_files(request.principal, base, limit, purpose=purpose)
        if tool == "search_text":
            query = self._required_string(arguments, "query")
            bases = arguments.pop("paths", None)
            base = arguments.pop("path", ".")
            limit = arguments.pop("limit", arguments.pop("max_results", self.max_results))
            case_sensitive = arguments.pop("case_sensitive", True)
            self._expect_only(arguments, ())
            if bases is None:
                bases = (base,)
            if (
                not self._string_sequence(bases)
                or not isinstance(case_sensitive, bool)
                or isinstance(limit, bool)
                or not isinstance(limit, int)
                or not 0 < limit <= self.max_results
            ):
                raise ContractError("invalid search_text arguments")
            return self._search_text(
                request.principal,
                query,
                bases,
                limit,
                case_sensitive=case_sensitive,
                purpose=purpose,
            )
        if tool == "search_knowledge":
            query = self._required_string(arguments, "query")
            scopes = arguments.pop("scopes", ())
            limit = arguments.pop("limit", min(20, self.max_results))
            self._expect_only(arguments, ())
            if (
                not self._string_sequence(scopes)
                or isinstance(limit, bool)
                or not isinstance(limit, int)
                or not 0 < limit <= self.max_results
            ):
                raise ContractError("invalid search_knowledge arguments")
            authorized = self.policy.authorize_knowledge(request.principal, scopes, purpose=purpose)
            if self.knowledge_search is None:
                raise ContractError("knowledge search provider is not configured")
            matches = tuple(dict(item) for item in self.knowledge_search(query, authorized, limit))
            if len(matches) > limit:
                raise ContractError("knowledge provider exceeded the requested result limit")
            return (
                {"query": query, "scopes": authorized, "matches": matches},
                "KNOWLEDGE_READ",
                ",".join(authorized),
            )
        if tool == "prepare_patch":
            snapshot_id = arguments.pop("snapshot_id", None)
            operations = arguments.pop("operations", None)
            patch_id = arguments.pop("patch_id", None)
            self._expect_only(arguments, ())
            if not isinstance(operations, Sequence) or isinstance(operations, (str, bytes)):
                raise ContractError("prepare_patch operations must be an array")
            if patch_id is not None and not isinstance(patch_id, str):
                raise ContractError("patch_id must be a string")
            if snapshot_id is None:
                snapshot_id = (
                    self.git_adapter.snapshot().snapshot_id
                    if self.git_adapter is not None
                    else "workspace-" + value_digest({"root": str(self.workspace)}).removeprefix("sha256:")[:20]
                )
            if not isinstance(snapshot_id, str) or not snapshot_id:
                raise ContractError("snapshot_id must be a non-empty string")
            artifact = self.patch_engine.prepare(snapshot_id, operations, patch_id=patch_id)
            for operation in artifact.operations:
                self.policy.authorize_write(request.principal, operation.path, purpose=purpose)
                if operation.new_path:
                    self.policy.authorize_write(request.principal, operation.new_path, purpose=purpose)
            return {"artifact": asdict(artifact)}, "PREPARE_WRITE", artifact.patch_id
        if tool == "apply_patch":
            if not request.operation_id:
                raise ContractError("apply_patch requires an operation_id")
            patch_id = self._required_string(arguments, "patch_id")
            self._expect_only(arguments, ())
            artifact = self.patch_engine.get(patch_id)
            # Deny first: an unauthorized caller must not trigger even a Git
            # snapshot read or consume a durable approval.
            for operation in artifact.operations:
                self.policy.authorize_write(request.principal, operation.path, purpose=purpose)
                if operation.new_path:
                    self.policy.authorize_write(request.principal, operation.new_path, purpose=purpose)
            if self.git_adapter is not None and self.git_adapter.snapshot().snapshot_id != artifact.snapshot_id:
                raise OperationConflict("repository changed after patch preparation")
            self.policy.authorize_patch(
                request.principal,
                artifact,
                approval_id=request.approval_id,
                operation_id=request.operation_id,
                purpose=purpose,
            )
            return dict(self.patch_engine.apply(artifact)), "WRITE", patch_id
        if tool == "restore_change_set":
            if not request.operation_id:
                raise ContractError("restore_change_set requires an operation_id")
            patch_id = arguments.pop("patch_id", arguments.pop("change_set_id", None))
            self._expect_only(arguments, ())
            if not isinstance(patch_id, str) or not patch_id:
                raise ContractError("restore_change_set requires change_set_id")
            artifact = self.patch_engine.get(patch_id)
            for operation in artifact.operations:
                self.policy.authorize_write(request.principal, operation.path, purpose=purpose)
                if operation.new_path:
                    self.policy.authorize_write(request.principal, operation.new_path, purpose=purpose)
            return dict(self.patch_engine.rollback(patch_id)), "WRITE", patch_id
        if tool == "run_check":
            if not request.operation_id:
                raise ContractError("run_check requires an operation_id")
            if self.process_runner is None:
                raise ContractError(f"{tool} requires a ProcessRunner")
            command_id = arguments.pop("command_id", arguments.pop("check_id", None))
            if not isinstance(command_id, str) or not command_id:
                raise ContractError(f"{tool} requires command_id or check_id")
            spec = self.process_runner.catalog.get(command_id)
            argv = arguments.pop("argv", spec.argv)
            cwd = arguments.pop("cwd", spec.cwd)
            environment = arguments.pop("environment", {})
            timeout = arguments.pop("timeout_seconds", 30.0)
            output_limit = arguments.pop("max_output_bytes", 100_000)
            network = arguments.pop("network", "deny")
            self._expect_only(arguments, ())
            if not self._string_sequence(argv) or not isinstance(cwd, str) or not isinstance(environment, Mapping):
                raise ContractError("invalid command arguments")
            command = CommandRequest(
                command_id=command_id,
                argv=tuple(argv),
                cwd=cwd,
                environment=dict(environment),
                timeout_seconds=timeout,
                max_output_bytes=output_limit,
                network=network,
            )
            self.policy.authorize_command(
                request.principal,
                command_id,
                network=network,
                purpose=purpose,
                argv=command.argv,
            )
            result = self.process_runner.run(command)
            output = asdict(result)
            output["request"] = {
                "argv": command.argv,
                "cwd": command.cwd,
                "environment_keys": tuple(sorted(command.environment)),
                "timeout_seconds": command.timeout_seconds,
                "max_output_bytes": command.max_output_bytes,
                "network": command.network,
            }
            output["network_enforcement"] = (
                "OS_WRAPPER" if self.process_runner.network_wrapper is not None else "CATALOG_POLICY_ONLY"
            )
            output["catalog_digest"] = self.process_runner.catalog.digest
            output["catalog_entry_digest"] = self.process_runner.catalog.entry_digest(command_id)
            return output, "PROCESS", command_id
        raise ContractError(f"unknown tool: {tool}")

    @staticmethod
    def _required_string(arguments: dict[str, Any], key: str) -> str:
        value = arguments.pop(key, None)
        if not isinstance(value, str) or not value:
            raise ContractError(f"{key} must be a non-empty string")
        return value

    @staticmethod
    def _expect_only(arguments: Mapping[str, Any], allowed: Sequence[str]) -> None:
        unexpected = set(arguments) - set(allowed)
        if unexpected:
            raise ContractError(f"unexpected tool arguments: {sorted(unexpected)!r}")

    @staticmethod
    def _string_sequence(value: Any) -> bool:
        return isinstance(value, (list, tuple)) and all(isinstance(item, str) and item for item in value)

    def _list_files(
        self, principal: str, base: str, limit: int, *, purpose: str | None
    ) -> tuple[Mapping[str, Any], str, str]:
        if base == ".":
            target = self.workspace
            resource = "."
            self._authorize_root_read(principal, purpose=purpose)
        else:
            resource = self.policy.authorize_read(principal, base, purpose=purpose)
            target = canonical_path(self.workspace, base, must_exist=True)
        if not target.is_dir():
            raise PolicyDenied("list_files target must be a directory")
        files: list[str] = []
        truncated = False
        for path in sorted(target.rglob("*"), key=lambda item: item.relative_to(self.workspace).as_posix()):
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(self.workspace).as_posix()
            try:
                self.policy.authorize_read(principal, relative, purpose=purpose)
            except PolicyDenied:
                continue
            if len(files) == limit:
                truncated = True
                break
            files.append(relative)
        return {"path": base, "files": tuple(files), "truncated": truncated}, "READ", resource

    def _search_text(
        self,
        principal: str,
        query: str,
        bases: Sequence[str],
        limit: int,
        *,
        case_sensitive: bool,
        purpose: str | None,
    ) -> tuple[Mapping[str, Any], str, str]:
        if len(query.encode("utf-8")) > 10_000:
            raise ContractError("search query is too large")
        matches: list[Mapping[str, Any]] = []
        scanned_bytes = 0
        resources: list[str] = []
        seen: set[str] = set()
        needle = query if case_sensitive else query.casefold()
        for base in bases:
            listing, _, resource = self._list_files(principal, base, self.max_results, purpose=purpose)
            resources.append(resource)
            for relative in listing["files"]:
                if relative in seen:
                    continue
                seen.add(relative)
                remaining = self.max_read_bytes - scanned_bytes
                if remaining <= 0:
                    return (
                        {"query": query, "matches": tuple(matches), "truncated": True},
                        "READ",
                        ",".join(resources),
                    )
                try:
                    item = self.patch_engine.read(relative, max_bytes=remaining)
                except PolicyDenied:
                    continue
                scanned_bytes += int(item["size"])
                for line_number, line in enumerate(str(item["content"]).splitlines(), 1):
                    haystack = line if case_sensitive else line.casefold()
                    if needle in haystack:
                        matches.append(
                            {
                                "path": relative,
                                "line": line_number,
                                "text": line[:500],
                                "digest": item["digest"],
                            }
                        )
                        if len(matches) == limit:
                            return (
                                {"query": query, "matches": tuple(matches), "truncated": True},
                                "READ",
                                ",".join(resources),
                            )
        return (
            {"query": query, "matches": tuple(matches), "truncated": False},
            "READ",
            ",".join(resources),
        )

    def _authorize_root_read(self, principal: str, *, purpose: str | None) -> None:
        if not any(
            grant
            for grant in self.policy._active_grants(principal, purpose=purpose)
            if any(scope.rstrip("/") in {"", "."} for scope in grant.read_paths)
        ):
            raise PolicyDenied("workspace-wide metadata/read is not granted")
