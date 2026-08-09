#!/usr/bin/env python3
"""Public Mica conformance runner.

This runner validates observable CLI contracts. It intentionally does not
import learner implementation modules or inspect source structure.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
MANIFEST = FIXTURES / "manifest.json"
STAGE_ORDER = {
    "skeleton": 0,
    "source": 1,
    "lex": 2,
    "parse": 3,
    "check": 4,
    "run": 5,
    "all": 5,
    "vm": 6,
    "format": 7,
}


class ConformanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Result:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def die(message: str) -> None:
    raise ConformanceError(message)


def read_manifest() -> dict[str, Any]:
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die(f"cannot read fixture manifest: {exc}")
    if data.get("schema_version") != 1:
        die("unsupported fixture manifest schema")
    return data


def command_prefix(workspace: Path, command: str | None) -> list[str]:
    if command:
        parts = shlex.split(command)
        if not parts:
            die("--command must not be empty")
        first = Path(parts[0])
        if not first.is_absolute() and (workspace / first).exists():
            parts[0] = str((workspace / first).resolve())
        return parts
    return [sys.executable, "-m", "mica"]


def run_process(
    prefix: Sequence[str],
    args: Sequence[str],
    *,
    workspace: Path,
    timeout: float,
) -> Result:
    argv = [*prefix, *map(str, args)]
    env = os.environ.copy()
    src = workspace / "src"
    if src.is_dir():
        old = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(src) if not old else str(src) + os.pathsep + old
    try:
        proc = subprocess.run(
            argv,
            cwd=workspace,
            env=env,
            text=True,
            encoding="utf-8",
            errors="strict",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        die(f"timeout after {timeout}s: {' '.join(argv)}\nstdout={exc.stdout!r}\nstderr={exc.stderr!r}")
    except (OSError, UnicodeError) as exc:
        die(f"cannot execute {' '.join(argv)}: {exc}")
    if proc.returncode < 0:
        die(f"process crashed with signal {-proc.returncode}: {' '.join(argv)}")
    return Result(tuple(argv), proc.returncode, proc.stdout, proc.stderr)


def parse_json_result(result: Result) -> dict[str, Any]:
    text = result.stdout.strip()
    if not text:
        die(f"empty JSON stdout: {' '.join(result.argv)}\nstderr={result.stderr}")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        die(
            f"stdout is not exactly one JSON value: {' '.join(result.argv)}: {exc}\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )
    if not isinstance(value, dict):
        die(f"JSON root must be an object: {' '.join(result.argv)}")
    return value


def assert_envelope(payload: dict[str, Any], command: str, source: Path) -> int:
    if payload.get("schema_version") != 1:
        die(f"{command}: schema_version must be 1")
    if payload.get("command") != command:
        die(f"{command}: payload command is {payload.get('command')!r}")
    source_obj = payload.get("source")
    if not isinstance(source_obj, dict):
        die(f"{command}: source metadata missing")
    byte_length = len(source.read_bytes())
    if source_obj.get("byte_length") != byte_length:
        die(f"{command}: source.byte_length expected {byte_length}, got {source_obj.get('byte_length')!r}")
    if not isinstance(source_obj.get("id"), str) or not source_obj["id"]:
        die(f"{command}: source.id must be a non-empty string")
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, list):
        die(f"{command}: diagnostics must be an array")
    assert_diagnostics(diagnostics, byte_length)
    return byte_length


def assert_span(span: Any, byte_length: int, where: str) -> None:
    if not isinstance(span, dict):
        die(f"{where}: span must be an object")
    source_id = span.get("source_id")
    start = span.get("start")
    end = span.get("end")
    if not isinstance(source_id, str) or not source_id:
        die(f"{where}: source_id must be a non-empty string")
    if not isinstance(start, int) or isinstance(start, bool):
        die(f"{where}: span.start must be an integer")
    if not isinstance(end, int) or isinstance(end, bool):
        die(f"{where}: span.end must be an integer")
    if not 0 <= start <= end <= byte_length:
        die(f"{where}: invalid byte span [{start}, {end}) for source length {byte_length}")


def assert_diagnostics(diagnostics: list[Any], byte_length: int) -> None:
    seen: set[tuple[Any, ...]] = set()
    ordering: list[tuple[Any, ...]] = []
    severity_rank = {"error": 0, "warning": 1, "information": 2, "hint": 3}
    allowed_phase = {"lex", "parse", "resolution", "type", "flow", "runtime", "bytecode", "internal"}
    for index, item in enumerate(diagnostics):
        if not isinstance(item, dict):
            die(f"diagnostics[{index}] must be an object")
        code = item.get("code")
        severity = item.get("severity")
        phase = item.get("phase")
        message = item.get("message")
        if not isinstance(code, str) or len(code) != 8 or not code.startswith("MICA") or not code[4:].isdigit():
            die(f"diagnostics[{index}].code is not MICA####")
        if severity not in severity_rank:
            die(f"diagnostics[{index}].severity is invalid")
        if phase not in allowed_phase:
            die(f"diagnostics[{index}].phase is invalid")
        if not isinstance(message, str) or not message or "\n" in message:
            die(f"diagnostics[{index}].message must be a non-empty single line")
        primary = item.get("primary")
        assert_span(primary, byte_length, f"diagnostics[{index}].primary")
        for s_index, secondary in enumerate(item.get("secondary", [])):
            if not isinstance(secondary, dict):
                die(f"diagnostics[{index}].secondary[{s_index}] must be an object")
            assert_span(secondary.get("span"), byte_length, f"diagnostics[{index}].secondary[{s_index}].span")
        key = (code, primary["source_id"], primary["start"], primary["end"], message)
        if key in seen:
            die(f"duplicate diagnostic at index {index}: {code}")
        seen.add(key)
        ordering.append((primary["source_id"], primary["start"], primary["end"], severity_rank[severity], code, message))
    if ordering != sorted(ordering):
        die("diagnostics are not in deterministic source order")


def error_codes(payload: dict[str, Any]) -> list[str]:
    return [d["code"] for d in payload["diagnostics"] if d.get("severity") == "error"]


def assert_exit_and_codes(result: Result, payload: dict[str, Any], expected_exit: int, expected_codes: list[str]) -> None:
    if result.returncode != expected_exit:
        die(
            f"exit mismatch for {' '.join(result.argv)}: expected {expected_exit}, got {result.returncode}\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )
    codes = error_codes(payload)
    if codes != expected_codes:
        die(f"diagnostic codes mismatch for {' '.join(result.argv)}: expected {expected_codes}, got {codes}")
    if expected_exit == 0 and codes:
        die(f"successful command emitted error diagnostics: {codes}")
    if expected_exit == 1 and not codes:
        die("defined-error exit must include at least one error diagnostic")


def walk_ast(value: Any, byte_length: int, *, parent: tuple[int, int] | None = None, ids: set[int] | None = None) -> None:
    if ids is None:
        ids = set()
    if isinstance(value, dict):
        if {"kind", "id", "span"}.issubset(value):
            kind = value["kind"]
            node_id = value["id"]
            if not isinstance(kind, str) or not kind:
                die("AST node kind must be a non-empty string")
            if not isinstance(node_id, int) or isinstance(node_id, bool) or node_id < 0:
                die("AST node id must be a non-negative integer")
            if node_id in ids:
                die(f"duplicate AST node id: {node_id}")
            ids.add(node_id)
            assert_span(value["span"], byte_length, f"AST node {node_id}")
            start, end = value["span"]["start"], value["span"]["end"]
            if parent is not None and not (parent[0] <= start <= end <= parent[1]):
                die(f"AST child {node_id} span is outside parent")
            current = (start, end)
        else:
            current = parent
        for child in value.values():
            walk_ast(child, byte_length, parent=current, ids=ids)
    elif isinstance(value, list):
        for child in value:
            walk_ast(child, byte_length, parent=parent, ids=ids)


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def run_json_twice(prefix: Sequence[str], args: Sequence[str], *, workspace: Path, timeout: float) -> tuple[Result, dict[str, Any]]:
    first = run_process(prefix, args, workspace=workspace, timeout=timeout)
    first_payload = parse_json_result(first)
    second = run_process(prefix, args, workspace=workspace, timeout=timeout)
    second_payload = parse_json_result(second)
    if first.returncode != second.returncode or canonical_json(first_payload) != canonical_json(second_payload):
        die(f"non-deterministic result: {' '.join(first.argv)}")
    return first, first_payload


def stage_skeleton(prefix: Sequence[str], workspace: Path, timeout: float) -> None:
    source = FIXTURES / "valid/literal-main.mica"
    result = run_process(prefix, ["check", source, "--json"], workspace=workspace, timeout=timeout)
    payload = parse_json_result(result)
    assert_envelope(payload, "check", source)
    if result.returncode != 2:
        die(f"skeleton must fail explicitly with exit 2, got {result.returncode}")
    if "MICA0000" not in error_codes(payload):
        die("skeleton must report MICA0000")
    print("PASS skeleton explicit-unimplemented state")


def stage_source(prefix: Sequence[str], workspace: Path, timeout: float) -> None:
    source = FIXTURES / "valid/unicode-string.mica"
    result, payload = run_json_twice(prefix, ["lex", source, "--json"], workspace=workspace, timeout=timeout)
    byte_length = assert_envelope(payload, "lex", source)
    assert_exit_and_codes(result, payload, 0, [])
    tokens = payload.get("tokens")
    if not isinstance(tokens, list) or not tokens:
        die("source stage requires a non-empty token list")
    for index, token in enumerate(tokens):
        if not isinstance(token, dict):
            die(f"tokens[{index}] must be an object")
        assert_span(token.get("span"), byte_length, f"tokens[{index}].span")
    print("PASS source UTF-8 byte spans and deterministic output")


def stage_lex(prefix: Sequence[str], workspace: Path, timeout: float, manifest: dict[str, Any]) -> None:
    cases = [*manifest["valid"], *[c for c in manifest["invalid"] if c["stage"] == "lex"]]
    for case in cases:
        source = FIXTURES / case["file"]
        expected_exit = case.get("exit", 0)
        expected_codes = case.get("codes", [])
        result, payload = run_json_twice(prefix, ["lex", source, "--json"], workspace=workspace, timeout=timeout)
        byte_length = assert_envelope(payload, "lex", source)
        assert_exit_and_codes(result, payload, expected_exit, expected_codes)
        tokens = payload.get("tokens")
        if not isinstance(tokens, list) or not tokens:
            die(f"{case['file']}: tokens must be a non-empty array")
        starts: list[int] = []
        for index, token in enumerate(tokens):
            if not isinstance(token, dict):
                die(f"{case['file']}: tokens[{index}] must be an object")
            if not isinstance(token.get("kind"), str) or not isinstance(token.get("lexeme"), str):
                die(f"{case['file']}: token kind/lexeme must be strings")
            assert_span(token.get("span"), byte_length, f"{case['file']}: tokens[{index}]")
            starts.append(token["span"]["start"])
        if starts != sorted(starts):
            die(f"{case['file']}: tokens are not in source order")
        eof = tokens[-1]
        if eof.get("kind") != "EOF" or eof["span"]["start"] != byte_length or eof["span"]["end"] != byte_length:
            die(f"{case['file']}: final token must be zero-width EOF at byte length")
        print(f"PASS lex {case['file']}")


def stage_parse(prefix: Sequence[str], workspace: Path, timeout: float, manifest: dict[str, Any]) -> None:
    cases = [*manifest["valid"], *[c for c in manifest["invalid"] if c["stage"] == "parse"]]
    for case in cases:
        source = FIXTURES / case["file"]
        result, payload = run_json_twice(prefix, ["parse", source, "--json"], workspace=workspace, timeout=timeout)
        byte_length = assert_envelope(payload, "parse", source)
        assert_exit_and_codes(result, payload, case.get("exit", 0), case.get("codes", []))
        ast = payload.get("ast")
        if not isinstance(ast, dict) or ast.get("kind") != "Module":
            die(f"{case['file']}: parse output must contain Module AST")
        walk_ast(ast, byte_length)
        print(f"PASS parse {case['file']}")


def stage_check(prefix: Sequence[str], workspace: Path, timeout: float, manifest: dict[str, Any]) -> None:
    cases = [*manifest["valid"], *manifest["invalid"]]
    for case in cases:
        source = FIXTURES / case["file"]
        result, payload = run_json_twice(prefix, ["check", source, "--json"], workspace=workspace, timeout=timeout)
        assert_envelope(payload, "check", source)
        assert_exit_and_codes(result, payload, case.get("exit", 0), case.get("codes", []))
        print(f"PASS check {case['file']}")


def stage_run(prefix: Sequence[str], workspace: Path, timeout: float, manifest: dict[str, Any]) -> None:
    cases = [*manifest["valid"], *manifest["runtime"]]
    for case in cases:
        source = FIXTURES / case["file"]
        result, payload = run_json_twice(prefix, ["run", source, "--json"], workspace=workspace, timeout=timeout)
        assert_envelope(payload, "run", source)
        assert_exit_and_codes(result, payload, case.get("exit", 0), case.get("codes", []))
        if payload.get("stdout") != case.get("stdout", payload.get("stdout")):
            die(f"{case['file']}: program stdout mismatch")
        if payload.get("return_value") != case.get("return"):
            die(
                f"{case['file']}: return value mismatch: expected {case.get('return')!r}, "
                f"got {payload.get('return_value')!r}"
            )
        print(f"PASS run {case['file']}")


def stage_vm(prefix: Sequence[str], workspace: Path, timeout: float, manifest: dict[str, Any]) -> None:
    for case in manifest["bytecode_invalid"]:
        module = FIXTURES / case["file"]
        result, payload = run_json_twice(
            prefix, ["verify-bytecode", module, "--json"], workspace=workspace, timeout=timeout
        )
        # Bytecode input is JSON, but source metadata still identifies the file bytes.
        assert_envelope(payload, "verify-bytecode", module)
        assert_exit_and_codes(result, payload, 1, case["codes"])
        print(f"PASS bytecode verifier {case['file']}")


def stage_format(prefix: Sequence[str], workspace: Path, timeout: float, manifest: dict[str, Any]) -> None:
    for case in manifest["format"]:
        source = FIXTURES / case["file"]
        expected = (FIXTURES / case["expected"]).read_text(encoding="utf-8")
        first = run_process(prefix, ["format", source], workspace=workspace, timeout=timeout)
        if first.returncode != 0:
            die(f"formatter failed: {case['file']}\nstderr={first.stderr}")
        if first.stdout != expected:
            die(f"formatter output mismatch: {case['file']}\nexpected={expected!r}\ngot={first.stdout!r}")
        with tempfile.TemporaryDirectory(prefix="mica-format-") as tmp:
            formatted = Path(tmp) / "formatted.mica"
            formatted.write_text(first.stdout, encoding="utf-8")
            second = run_process(prefix, ["format", formatted], workspace=workspace, timeout=timeout)
            if second.returncode != 0 or second.stdout != first.stdout:
                die(f"formatter is not idempotent: {case['file']}")
            parsed = run_process(prefix, ["check", formatted, "--json"], workspace=workspace, timeout=timeout)
            payload = parse_json_result(parsed)
            assert_envelope(payload, "check", formatted)
            assert_exit_and_codes(parsed, payload, 0, [])
        print(f"PASS format {case['file']}")


def self_test() -> None:
    sample = FIXTURES / "valid/unicode-string.mica"
    data = sample.read_bytes()
    payload = {
        "schema_version": 1,
        "command": "check",
        "source": {"id": str(sample), "byte_length": len(data)},
        "diagnostics": [
            {
                "code": "MICA3003",
                "severity": "error",
                "phase": "resolution",
                "message": "sample",
                "primary": {"source_id": str(sample), "start": 0, "end": 0},
            }
        ],
    }
    assert_envelope(payload, "check", sample)
    if error_codes(payload) != ["MICA3003"]:
        die("runner self-test code extraction failed")
    ast = {"kind": "Module", "id": 0, "span": {"source_id": str(sample), "start": 0, "end": len(data)}, "functions": []}
    walk_ast(ast, len(data))
    print("PASS conformance runner self-test")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--command", help="implementation command; default: current Python -m mica")
    parser.add_argument("--stage", choices=sorted(STAGE_ORDER), default="all")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.workspace is None:
        die("--workspace is required unless --self-test is used")
    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        die(f"workspace is not a directory: {workspace}")
    if args.timeout <= 0:
        die("--timeout must be positive")
    prefix = command_prefix(workspace, args.command)
    manifest = read_manifest()

    if args.stage == "skeleton":
        stage_skeleton(prefix, workspace, args.timeout)
        return 0
    if args.stage == "vm":
        stage_vm(prefix, workspace, args.timeout, manifest)
        return 0
    if args.stage == "format":
        stage_format(prefix, workspace, args.timeout, manifest)
        return 0

    selected = STAGE_ORDER[args.stage]
    if selected >= STAGE_ORDER["source"]:
        stage_source(prefix, workspace, args.timeout)
    if selected >= STAGE_ORDER["lex"]:
        stage_lex(prefix, workspace, args.timeout, manifest)
    if selected >= STAGE_ORDER["parse"]:
        stage_parse(prefix, workspace, args.timeout, manifest)
    if selected >= STAGE_ORDER["check"]:
        stage_check(prefix, workspace, args.timeout, manifest)
    if selected >= STAGE_ORDER["run"]:
        stage_run(prefix, workspace, args.timeout, manifest)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConformanceError as exc:
        print(f"CONFORMANCE ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
