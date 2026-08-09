#!/usr/bin/env python3
"""Verify the distributed-systems guide as a publishable curriculum branch."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import py_compile
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from source_fingerprint import ROOT, fingerprint, source_files

MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")
MANIFEST = ROOT / "config" / "repository-files.txt"


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - error reporting path
        raise VerificationError(f"JSON parse failed: {path.relative_to(ROOT)}: {exc}") from exc


def run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        merged.update(env)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        rendered = " ".join(command)
        raise VerificationError(
            f"command failed ({completed.returncode}): {rendered}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def check_required_structure() -> None:
    required = [
        "README.md",
        "CONTRIBUTING.md",
        "LICENSE.md",
        "LICENSES/CC-BY-4.0.txt",
        "LICENSES/MIT.txt",
        "Makefile",
        "prepare.sh",
        "verify.sh",
        "config/guide.json",
        "docs/00-roadmap.md",
        "docs/06-capstone.md",
        "exercises/README.md",
        "capstone/starter/README.md",
        "capstone/starter/dskv/node.py",
        "capstone/tests/README.md",
        "reference/primary-sources.md",
        "scripts/source_fingerprint.py",
    ]
    for relative in required:
        require((ROOT / relative).is_file(), f"required file missing: {relative}")

    core_docs = [
        path for path in (ROOT / "docs").rglob("*.md")
        if "90-optional-paths" not in path.parts
    ]
    require(len(core_docs) >= 23, f"too few core documents: {len(core_docs)}")
    exercise_readmes = list((ROOT / "exercises").rglob("README.md"))
    require(len(exercise_readmes) >= 12, f"too few exercise guides: {len(exercise_readmes)}")

    guide = load_json(ROOT / "config" / "guide.json")
    require(guide.get("id") == "distributed-systems", "guide id mismatch")
    require(guide.get("capstone", {}).get("reference_implementation_included") is False, "capstone must not claim a reference implementation")


def parse_markdown_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        target = target[1:target.index(">")]
    elif " " in target and not target.startswith(EXTERNAL_PREFIXES):
        # Markdown permits an optional title after the URL.
        target = target.split(" ", 1)[0]
    return unquote(target)


def check_markdown_links() -> None:
    markdown_files = sorted(ROOT.rglob("*.md"))
    require(markdown_files, "no Markdown files found")
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        require(text.startswith("# "), f"Markdown must start with H1: {path.relative_to(ROOT)}")
        for raw in MARKDOWN_LINK_RE.findall(text):
            target = parse_markdown_target(raw)
            if not target or target.startswith("#") or target.startswith(EXTERNAL_PREFIXES):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (path.parent / path_part).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError as exc:
                raise VerificationError(f"link escapes repository: {path.relative_to(ROOT)} -> {raw}") from exc
            require(resolved.exists(), f"broken link: {path.relative_to(ROOT)} -> {raw}")


def check_json_fixtures() -> None:
    json_files = sorted(ROOT.rglob("*.json"))
    require(len(json_files) >= 12, f"too few JSON fixtures: {len(json_files)}")
    for path in json_files:
        data = load_json(path)
        if isinstance(data, dict) and "schema_version" in data:
            require(data["schema_version"] == 1, f"unsupported schema_version: {path.relative_to(ROOT)}")

    trace = load_json(ROOT / "exercises/01-model-and-time/01-causality-trace/trace.json")
    event_ids = [event["id"] for event in trace["events"]]
    require(len(event_ids) == len(set(event_ids)), "causality trace has duplicate event ids")
    sends: set[str] = set()
    for event in trace["events"]:
        if event["kind"] == "send":
            sends.add(event["message"])
        if event["kind"] == "receive":
            require(event["message"] in sends, f"receive appears before send: {event['message']}")

    election = load_json(ROOT / "exercises/03-consensus-and-membership/01-election-trace/election.json")
    require(election["quorum"] == len(election["cluster"]) // 2 + 1, "election quorum mismatch")

    histories = load_json(ROOT / "exercises/05-validation/01-linearizability/histories.json")
    for history in histories["histories"]:
        ids = [operation["id"] for operation in history["operations"]]
        require(len(ids) == len(set(ids)), f"duplicate operation id in {history['id']}")
        for operation in history["operations"]:
            require(operation["invoke"] >= 0, f"negative invoke in {history['id']}")
            if operation.get("complete") is not None:
                require(operation["complete"] >= operation["invoke"], f"completion before invocation in {history['id']}")

    plan = load_json(ROOT / "exercises/05-validation/02-simulation-plan/plan-template.json")
    require("TODO" in json.dumps(plan), "simulation plan must remain a learner template")


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_python_sources() -> None:
    python_files = sorted(ROOT.rglob("*.py"))
    require(len(python_files) >= 12, f"too few Python files: {len(python_files)}")
    for path in python_files:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            raise VerificationError(f"Python compile failed: {path.relative_to(ROOT)}: {exc.msg}") from exc


def check_examples() -> None:
    logical_out = run([
        sys.executable,
        "examples/logical-clocks/logical_clocks.py",
        "exercises/01-model-and-time/01-causality-trace/trace.json",
    ])
    logical = json.loads(logical_out.stdout)
    require(logical["cuts"]["cut-1"]["consistent"] is True, "cut-1 must be consistent")
    require(logical["cuts"]["cut-2"]["consistent"] is False, "cut-2 must expose a missing causal predecessor")
    event = {item["id"]: item for item in logical["events"]}
    require(event["a4"]["vector"] == {"A": 4, "B": 3, "C": 3}, "unexpected final vector clock")

    network_command = [
        sys.executable,
        "examples/deterministic-network/simulation.py",
        "examples/deterministic-network/schedule.json",
    ]
    first = json.loads(run(network_command).stdout)
    second = json.loads(run(network_command).stdout)
    require(first == second, "deterministic network output changed between identical runs")
    require(first["digest"] == second["digest"], "deterministic network digest mismatch")
    require(len(first["nodes"]["B"]["inbox"]) == 2, "duplicate message schedule was not reproduced")
    require(len(first["nodes"]["C"]["inbox"]) == 0, "dropped message reached C")

    linear_out = run([
        sys.executable,
        "examples/linearizable-register/checker.py",
        "exercises/05-validation/01-linearizability/histories.json",
    ])
    results = {item["id"]: item for item in json.loads(linear_out.stdout)}
    expected = {
        "completed-write-then-read": True,
        "stale-read-after-completion": False,
        "overlapping-write-and-reads": True,
        "new-then-old-during-one-write": False,
        "pending-write-observed": True,
        "two-overlapping-writes": True,
    }
    require({key: results[key]["linearizable"] for key in expected} == expected, "linearizability fixture classification mismatch")
    require(results["pending-write-observed"]["included_pending"] == ["w1"], "pending write policy mismatch")


def check_capstone_starter() -> None:
    starter = ROOT / "capstone" / "starter"
    sys.path.insert(0, str(starter))
    try:
        from dskv import ClientRequest, Command, MemoryStorage, Node  # type: ignore

        node = Node("A", ["B", "C"], MemoryStorage(), election_timeout=3)
        try:
            node.tick(3)
        except NotImplementedError:
            pass
        else:
            raise VerificationError("canonical starter Node.tick must remain intentionally incomplete")

        request = ClientRequest(
            client_id="c",
            sequence=1,
            command=Command("put", "x", 1, client_id="c", sequence=1, fingerprint="put:x:1"),
        )
        try:
            node.submit(request, 0)
        except NotImplementedError:
            pass
        else:
            raise VerificationError("canonical starter Node.submit must remain intentionally incomplete")
    finally:
        sys.path.pop(0)
        for name in list(sys.modules):
            if name == "dskv" or name.startswith("dskv."):
                sys.modules.pop(name, None)

    storage_test = run([
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "capstone/tests",
        "-p",
        "test_01_storage_contract.py",
        "-v",
    ], env={"CAPSTONE_ROOT": str(starter)})
    require("OK" in storage_test.stderr or "OK" in storage_test.stdout, "starter storage contract test did not pass")

    node_source = (starter / "dskv" / "node.py").read_text(encoding="utf-8")
    require(node_source.count("NotImplementedError") >= 3, "starter protocol TODOs were unexpectedly completed")
    for design in (starter / "design").glob("*.md"):
        require("TODO" in design.read_text(encoding="utf-8"), f"starter design template has no TODO: {design.name}")


def expected_manifest_paths() -> list[str]:
    excluded = {"config/repository-files.txt"}
    return [
        path.relative_to(ROOT).as_posix()
        for path in source_files()
        if path.relative_to(ROOT).as_posix() not in excluded
    ]


def check_manifest() -> None:
    require(MANIFEST.is_file(), "repository manifest missing")
    actual = [line.strip() for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    expected = expected_manifest_paths()
    require(actual == expected, "config/repository-files.txt does not match source tree")


def check_prepared_fingerprint() -> None:
    marker_path = ROOT / ".guide" / "distributed-systems" / "prepared.json"
    require(marker_path.is_file(), "prepare marker missing")
    marker = load_json(marker_path)
    current = fingerprint()
    require(marker.get("guide") == "distributed-systems", "prepare marker guide mismatch")
    require(marker.get("source_sha256") == current["source_sha256"], "source changed after prepare; run make prepare again")
    require(marker.get("file_count") == current["file_count"], "prepared file count mismatch")


def check_no_unexpected_placeholders() -> None:
    allowed_prefixes = (
        "capstone/starter/design/",
        "capstone/starter/dskv/node.py",
        "exercises/05-validation/02-simulation-plan/plan-template.json",
    )
    for path in source_files():
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith(allowed_prefixes):
            continue
        if path.suffix not in {".md", ".py", ".json", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        placeholder_token = "PLACE" + "HOLDER"
        require(placeholder_token not in text, f"unexpected unfinished token: {relative}")
        # TODO in prose can legitimately discuss the marker, so only reject common unfinished tokens.
        unresolved_token = "TBD" + "_UNRESOLVED"
        require(unresolved_token not in text, f"unresolved token: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="skip prepared fingerprint check")
    args = parser.parse_args()

    if sys.version_info < (3, 12):
        raise VerificationError("Python 3.12 이상이 필요합니다.")

    checks = [
        ("structure", check_required_structure),
        ("links", check_markdown_links),
        ("json", check_json_fixtures),
        ("python", check_python_sources),
        ("examples", check_examples),
        ("capstone-starter", check_capstone_starter),
        ("manifest", check_manifest),
        ("placeholders", check_no_unexpected_placeholders),
    ]
    if not args.quick:
        checks.append(("prepared-fingerprint", check_prepared_fingerprint))

    for name, check in checks:
        check()
        print(f"OK {name}")

    print(f"VERIFY OK files={len(source_files())} mode={'quick' if args.quick else 'full'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
