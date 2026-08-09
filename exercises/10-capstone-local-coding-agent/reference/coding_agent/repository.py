from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from .errors import ContractError, ReconciliationRequired
from .types import RepositorySnapshot
from .util import sha256_bytes, value_digest


@dataclass(frozen=True)
class FileRead:
    path: str
    text: str
    digest: str
    snapshot_id: str
    byte_count: int


@dataclass(frozen=True)
class SearchHit:
    path: str
    line: int
    excerpt: str
    digest: str
    snapshot_id: str

    @property
    def citation(self) -> str:
        return f"repo:{self.path}@{self.digest}#L{self.line}"


@dataclass(frozen=True)
class InstructionRecord:
    path: str
    scope: str
    digest: str
    kind: str


@dataclass(frozen=True)
class CommandCandidate:
    command_id: str
    argv: tuple[str, ...]
    source: str
    confidence: str


@dataclass(frozen=True)
class RepositoryDiscovery:
    snapshot: RepositorySnapshot
    instructions: tuple[InstructionRecord, ...]
    manifests: tuple[str, ...]
    commands: tuple[CommandCandidate, ...]


_MANIFEST_NAMES = {
    "Cargo.toml",
    "Makefile",
    "go.mod",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
    "setup.cfg",
    "tox.ini",
}
_INSTRUCTION_NAMES = {"AGENTS.md", "CLAUDE.md"}


def _run_git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        [
            "git",
            "-c",
            "color.ui=false",
            "-c",
            "core.quotepath=false",
            "-C",
            os.fspath(root),
            *arguments,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise ContractError(f"git {' '.join(arguments)} failed: {message or result.returncode}")
    return result


def _decode_path(value: bytes) -> str:
    return value.decode("utf-8", "surrogateescape").replace("\\", "/")


def _nul_paths(value: bytes) -> tuple[str, ...]:
    return tuple(sorted(_decode_path(item) for item in value.split(b"\0") if item))


def resolve_repository_root(path: str | os.PathLike[str]) -> Path:
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_dir():
        raise ContractError(f"repository root is not a directory: {candidate}")
    result = _run_git(candidate, "rev-parse", "--show-toplevel", check=False)
    if result.returncode == 0:
        root = Path(result.stdout.decode("utf-8", "surrogateescape").strip()).resolve()
        if not root.is_dir():
            raise ContractError("Git reported a missing repository root")
        return root
    return candidate


def _read_identity_bytes(path: Path, root: Path) -> bytes:
    if path.is_symlink():
        try:
            return ("symlink:" + os.readlink(path)).encode("utf-8", "surrogateescape")
        except OSError as error:
            raise ReconciliationRequired(f"cannot read repository symlink {path}") from error
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, RuntimeError, OSError) as error:
        raise ReconciliationRequired(f"cannot resolve repository path {path}") from error
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ContractError(f"repository path escapes root: {path}") from error
    if not resolved.is_file():
        raise ContractError(f"repository path is not a regular file: {path}")
    return resolved.read_bytes()


def _git_file_paths(root: Path) -> tuple[str, ...]:
    result = _run_git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return _nul_paths(result.stdout)


def _plain_file_paths(root: Path) -> tuple[str, ...]:
    paths: list[str] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in {".git", ".guide", "__pycache__"} for part in relative.parts):
            continue
        if path.is_file() or path.is_symlink():
            paths.append(relative.as_posix())
    return tuple(sorted(paths))


def snapshot_repository(
    path: str | os.PathLike[str],
    *,
    max_files: int = 50_000,
    max_total_bytes: int = 250_000_000,
) -> RepositorySnapshot:
    root = resolve_repository_root(path)
    is_git = _run_git(root, "rev-parse", "--is-inside-work-tree", check=False).returncode == 0
    if is_git:
        files = _git_file_paths(root)
        head_result = _run_git(root, "rev-parse", "--verify", "HEAD", check=False)
        head = head_result.stdout.decode("ascii", "replace").strip() if head_result.returncode == 0 else None
        branch_result = _run_git(root, "symbolic-ref", "--short", "-q", "HEAD", check=False)
        branch = (
            branch_result.stdout.decode("utf-8", "surrogateescape").strip()
            if branch_result.returncode == 0
            else None
        )
        index = _run_git(root, "ls-files", "--stage", "-z").stdout
        index_tree = sha256_bytes(index)
        staged = _nul_paths(_run_git(root, "diff", "--cached", "--name-only", "-z", "--").stdout)
        unstaged = _nul_paths(_run_git(root, "diff", "--name-only", "-z", "--").stdout)
        untracked = _nul_paths(
            _run_git(root, "ls-files", "--others", "--exclude-standard", "-z").stdout
        )
    else:
        files = _plain_file_paths(root)
        head = branch = index_tree = None
        staged = unstaged = ()
        untracked = files
    if len(files) > max_files:
        raise ContractError(f"repository contains more than {max_files} visible files")
    file_digests: dict[str, str] = {}
    total_bytes = 0
    for relative in files:
        data = _read_identity_bytes(root / relative, root)
        total_bytes += len(data)
        if total_bytes > max_total_bytes:
            raise ContractError(f"repository snapshot exceeds {max_total_bytes} bytes")
        file_digests[relative] = sha256_bytes(data)
    identity = {
        "root": os.fspath(root),
        "head": head,
        "branch": branch,
        "index_tree": index_tree,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "files": file_digests,
    }
    return RepositorySnapshot(snapshot_id=value_digest(identity), files=file_digests, **{k: identity[k] for k in identity if k != "files"})


class RepositoryReader:
    def __init__(self, snapshot: RepositorySnapshot) -> None:
        self.snapshot = snapshot
        self.root = Path(snapshot.root).resolve()
        if not self.root.is_dir():
            raise ReconciliationRequired("snapshot repository root no longer exists")

    def resolve(self, relative: str) -> tuple[str, Path]:
        if not isinstance(relative, str) or not relative or "\x00" in relative:
            raise ContractError("repository path must be a non-empty string")
        normalized = PurePosixPath(relative.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ContractError("repository path escapes the root")
        path_text = normalized.as_posix()
        if path_text in {".git", "."} or path_text.startswith(".git/"):
            if path_text != ".":
                raise ContractError("Git metadata is not readable through repository tools")
        candidate = (self.root / path_text).resolve(strict=False)
        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise ContractError("repository path resolves outside the root") from error
        return path_text, candidate

    def list_files(self, prefix: str = ".", *, max_results: int = 10_000) -> tuple[str, ...]:
        path_text, _ = self.resolve(prefix)
        if max_results <= 0:
            raise ValueError("max_results must be positive")
        if path_text == ".":
            selected = sorted(self.snapshot.files)
        else:
            selected = sorted(
                path for path in self.snapshot.files if path == path_text or path.startswith(path_text.rstrip("/") + "/")
            )
        return tuple(selected[:max_results])

    def read_text(self, relative: str, *, max_bytes: int = 1_000_000) -> FileRead:
        path_text, candidate = self.resolve(relative)
        expected = self.snapshot.files.get(path_text)
        if expected is None:
            raise ReconciliationRequired(f"path was not present in snapshot: {path_text}")
        if candidate.is_symlink():
            raise ContractError(f"refusing to follow repository symlink: {path_text}")
        try:
            data = candidate.read_bytes()
        except OSError as error:
            raise ReconciliationRequired(f"cannot read snapshot path: {path_text}") from error
        actual = sha256_bytes(data)
        if actual != expected:
            raise ReconciliationRequired(f"snapshot path is stale: {path_text}")
        if len(data) > max_bytes:
            raise ContractError(f"repository file exceeds {max_bytes} bytes: {path_text}")
        if b"\x00" in data:
            raise ContractError(f"repository file is binary: {path_text}")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ContractError(f"repository file is not UTF-8: {path_text}") from error
        return FileRead(
            path=path_text,
            text=text,
            digest=actual,
            snapshot_id=self.snapshot.snapshot_id,
            byte_count=len(data),
        )

    def search(
        self,
        query: str,
        *,
        paths: tuple[str, ...] = (".",),
        case_sensitive: bool = False,
        max_results: int = 50,
        max_file_bytes: int = 1_000_000,
    ) -> tuple[SearchHit, ...]:
        if not isinstance(query, str) or not query or "\x00" in query:
            raise ContractError("search query must be a non-empty string")
        if max_results <= 0:
            raise ValueError("max_results must be positive")
        candidates: set[str] = set()
        for prefix in paths:
            candidates.update(self.list_files(prefix))
        needle = query if case_sensitive else query.casefold()
        hits: list[SearchHit] = []
        for path in sorted(candidates):
            try:
                read = self.read_text(path, max_bytes=max_file_bytes)
            except ContractError:
                continue
            for line_number, line in enumerate(read.text.splitlines(), start=1):
                haystack = line if case_sensitive else line.casefold()
                if needle in haystack:
                    hits.append(
                        SearchHit(
                            path=path,
                            line=line_number,
                            excerpt=line[:1000],
                            digest=read.digest,
                            snapshot_id=self.snapshot.snapshot_id,
                        )
                    )
                    if len(hits) >= max_results:
                        return tuple(hits)
        return tuple(hits)


def search_repository(
    snapshot: RepositorySnapshot,
    query: str,
    *,
    paths: tuple[str, ...] = (".",),
    case_sensitive: bool = False,
    max_results: int = 50,
) -> tuple[SearchHit, ...]:
    return RepositoryReader(snapshot).search(
        query,
        paths=paths,
        case_sensitive=case_sensitive,
        max_results=max_results,
    )


def _instruction_records(reader: RepositoryReader) -> tuple[InstructionRecord, ...]:
    records: list[InstructionRecord] = []
    for path in reader.list_files():
        pure = PurePosixPath(path)
        is_instruction = pure.name in _INSTRUCTION_NAMES or path == ".github/copilot-instructions.md"
        is_orientation = pure.name in {"README.md", "CONTRIBUTING.md"}
        if not is_instruction and not is_orientation:
            continue
        scope = pure.parent.as_posix()
        if scope == ".":
            scope = "**"
        else:
            scope += "/**"
        records.append(
            InstructionRecord(
                path=path,
                scope=scope,
                digest=reader.snapshot.files[path],
                kind="INSTRUCTION" if is_instruction else "ORIENTATION",
            )
        )
    return tuple(records)


def _commands(reader: RepositoryReader) -> tuple[CommandCandidate, ...]:
    paths = set(reader.snapshot.files)
    commands: dict[str, CommandCandidate] = {}

    def add(command_id: str, argv: tuple[str, ...], source: str, confidence: str = "manifest") -> None:
        commands.setdefault(command_id, CommandCandidate(command_id, argv, source, confidence))

    if "Makefile" in paths:
        makefile = reader.read_text("Makefile", max_bytes=500_000).text
        targets = set(re.findall(r"(?m)^([A-Za-z0-9_.-]+)\s*:(?![=])", makefile))
        for target in ("test", "check", "verify", "lint", "build"):
            if target in targets:
                add(f"make-{target}", ("make", target), "Makefile")
    if "pyproject.toml" in paths or "setup.cfg" in paths or "tox.ini" in paths:
        add("python-unittest", ("python3", "-m", "unittest", "discover"), "Python project manifest", "inferred")
    if "package.json" in paths:
        try:
            package = json.loads(reader.read_text("package.json", max_bytes=1_000_000).text)
        except json.JSONDecodeError:
            package = {}
        scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
        if isinstance(scripts, dict):
            for name in ("test", "lint", "build", "check"):
                if isinstance(scripts.get(name), str):
                    add(f"npm-{name}", ("npm", "run", name), "package.json")
    if "Cargo.toml" in paths:
        add("cargo-test", ("cargo", "test"), "Cargo.toml")
    if "go.mod" in paths:
        add("go-test", ("go", "test", "./..."), "go.mod")
    if "pom.xml" in paths:
        add("maven-test", ("mvn", "test"), "pom.xml")
    return tuple(commands[key] for key in sorted(commands))


def discover_repository(path: str | os.PathLike[str]) -> RepositoryDiscovery:
    snapshot = snapshot_repository(path)
    reader = RepositoryReader(snapshot)
    manifests = tuple(sorted(path for path in snapshot.files if PurePosixPath(path).name in _MANIFEST_NAMES))
    return RepositoryDiscovery(
        snapshot=snapshot,
        instructions=_instruction_records(reader),
        manifests=manifests,
        commands=_commands(reader),
    )
