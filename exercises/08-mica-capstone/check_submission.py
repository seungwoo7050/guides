#!/usr/bin/env python3
"""Public Mica conformance runner.

This runner validates observable CLI contracts. It intentionally does not
import learner implementation modules or inspect source structure.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
MANIFEST = FIXTURES / "manifest.json"
MAX_STREAM_BYTES = 1_048_576
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


@dataclass(frozen=True)
class SourceContext:
    source_id: str
    data: bytes
    boundaries: frozenset[int]

    @property
    def byte_length(self) -> int:
        return len(self.data)


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
    def stop_group(proc: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            time.sleep(0.01)
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            proc = subprocess.Popen(
                argv,
                cwd=workspace,
                env=env,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
        except OSError as exc:
            die(f"cannot execute {' '.join(argv)}: {exc}")
        deadline = time.monotonic() + timeout
        failure: str | None = None
        while proc.poll() is None:
            if stdout_file.tell() > MAX_STREAM_BYTES:
                failure = f"stdout limit exceeded ({MAX_STREAM_BYTES} bytes)"
                break
            if stderr_file.tell() > MAX_STREAM_BYTES:
                failure = f"stderr limit exceeded ({MAX_STREAM_BYTES} bytes)"
                break
            if time.monotonic() >= deadline:
                failure = f"timeout after {timeout}s"
                break
            time.sleep(0.01)
        if failure is not None:
            stop_group(proc)
            proc.wait(timeout=2)
        else:
            # The command is complete, but a descendant may still hold inherited
            # descriptors or continue running. The submission process group is
            # disposable, so clean any descendants before reading captured data.
            stop_group(proc)
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout_bytes = stdout_file.read(MAX_STREAM_BYTES + 1)
        stderr_bytes = stderr_file.read(MAX_STREAM_BYTES + 1)
    if len(stdout_bytes) > MAX_STREAM_BYTES:
        failure = f"stdout limit exceeded ({MAX_STREAM_BYTES} bytes)"
    if len(stderr_bytes) > MAX_STREAM_BYTES:
        failure = f"stderr limit exceeded ({MAX_STREAM_BYTES} bytes)"
    try:
        stdout = stdout_bytes.decode("utf-8", errors="strict")
        stderr = stderr_bytes.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        die(f"process output is not UTF-8: {' '.join(argv)}: {exc}")
    if failure is not None:
        die(f"{failure}: {' '.join(argv)}\nstdout={stdout[:4096]!r}\nstderr={stderr[:4096]!r}")
    returncode = proc.returncode
    if returncode is None:
        die(f"process did not terminate: {' '.join(argv)}")
    if returncode < 0:
        die(f"process crashed with signal {-returncode}: {' '.join(argv)}")
    return Result(tuple(argv), returncode, stdout, stderr)


def parse_json_result(result: Result) -> dict[str, Any]:
    text = result.stdout.strip()
    if not text:
        die(f"empty JSON stdout: {' '.join(result.argv)}\nstderr={result.stderr}")
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    try:
        value = json.loads(text, parse_constant=reject_constant)
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        die(
            f"stdout is not exactly one JSON value: {' '.join(result.argv)}: {exc}\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )
    if not isinstance(value, dict):
        die(f"JSON root must be an object: {' '.join(result.argv)}")
    stack: list[Any] = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, float) and not math.isfinite(item):
            die(f"non-finite JSON number: {' '.join(result.argv)}")
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return value


def source_context(source: Path, source_id: str) -> SourceContext:
    data = source.read_bytes()
    text = data.decode("utf-8")
    boundaries = {0}
    cursor = 0
    for character in text:
        cursor += len(character.encode("utf-8"))
        boundaries.add(cursor)
    return SourceContext(source_id, data, frozenset(boundaries))


def assert_envelope(payload: dict[str, Any], command: str, source: Path) -> SourceContext:
    if payload.get("schema_version") != 1:
        die(f"{command}: schema_version must be 1")
    if payload.get("command") != command:
        die(f"{command}: payload command is {payload.get('command')!r}")
    source_obj = payload.get("source")
    if not isinstance(source_obj, dict):
        die(f"{command}: source metadata missing")
    source_id = source_obj.get("id")
    if not isinstance(source_id, str) or not source_id:
        die(f"{command}: source.id must be a non-empty string")
    context = source_context(source, source_id)
    if source_obj.get("byte_length") != context.byte_length:
        die(
            f"{command}: source.byte_length expected {context.byte_length}, "
            f"got {source_obj.get('byte_length')!r}"
        )
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, list):
        die(f"{command}: diagnostics must be an array")
    assert_diagnostics(diagnostics, context)
    return context


def assert_span(span: Any, context: SourceContext, where: str) -> None:
    if not isinstance(span, dict):
        die(f"{where}: span must be an object")
    source_id = span.get("source_id")
    start = span.get("start")
    end = span.get("end")
    if source_id != context.source_id:
        die(f"{where}: source_id does not match envelope source.id")
    if not isinstance(start, int) or isinstance(start, bool):
        die(f"{where}: span.start must be an integer")
    if not isinstance(end, int) or isinstance(end, bool):
        die(f"{where}: span.end must be an integer")
    if not 0 <= start <= end <= context.byte_length:
        die(f"{where}: invalid byte span [{start}, {end}) for source length {context.byte_length}")
    if start not in context.boundaries or end not in context.boundaries:
        die(f"{where}: span splits a UTF-8 code point")


def expected_phase(code: str) -> str:
    number = int(code[4:])
    if number < 1000 or number == 9001:
        return "internal"
    if 1000 <= number < 2000:
        return "lex"
    if 2000 <= number < 3000:
        return "parse"
    if 3000 <= number < 3100:
        return "resolution"
    if 3100 <= number < 3200:
        return "type"
    if 3200 <= number < 3300:
        return "flow"
    if 4000 <= number < 5000:
        return "runtime"
    if 5000 <= number < 6000:
        return "bytecode"
    if 6000 <= number < 7000:
        return "lint"
    return "internal"


def assert_diagnostics(diagnostics: list[Any], context: SourceContext) -> None:
    seen: set[tuple[Any, ...]] = set()
    ordering: list[tuple[Any, ...]] = []
    severity_rank = {"error": 0, "warning": 1, "information": 2, "hint": 3}
    allowed_phase = {"lex", "parse", "resolution", "type", "flow", "runtime", "bytecode", "lint", "internal"}
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
        if phase != expected_phase(code):
            die(f"diagnostics[{index}]: code {code} requires phase {expected_phase(code)}, got {phase}")
        if not isinstance(message, str) or not message or "\n" in message:
            die(f"diagnostics[{index}].message must be a non-empty single line")
        primary = item.get("primary")
        assert_span(primary, context, f"diagnostics[{index}].primary")
        secondary_items = item.get("secondary", [])
        if not isinstance(secondary_items, list):
            die(f"diagnostics[{index}].secondary must be an array")
        for s_index, secondary in enumerate(secondary_items):
            if not isinstance(secondary, dict):
                die(f"diagnostics[{index}].secondary[{s_index}] must be an object")
            if not isinstance(secondary.get("label"), str) or not secondary["label"]:
                die(f"diagnostics[{index}].secondary[{s_index}].label must be non-empty")
            assert_span(secondary.get("span"), context, f"diagnostics[{index}].secondary[{s_index}].span")
        fixes = item.get("fixes", [])
        if not isinstance(fixes, list):
            die(f"diagnostics[{index}].fixes must be an array")
        for f_index, fix in enumerate(fixes):
            if not isinstance(fix, dict) or fix.get("applicability") not in {
                "machine-applicable", "maybe-incorrect", "has-placeholders"
            }:
                die(f"diagnostics[{index}].fixes[{f_index}] has invalid applicability")
            edits = fix.get("edits")
            if not isinstance(edits, list) or not edits:
                die(f"diagnostics[{index}].fixes[{f_index}].edits must be non-empty")
            ranges: list[tuple[int, int]] = []
            for e_index, edit in enumerate(edits):
                if not isinstance(edit, dict) or not isinstance(edit.get("replacement"), str):
                    die(f"diagnostics[{index}].fixes[{f_index}].edits[{e_index}] is invalid")
                edit_span = {key: edit.get(key) for key in ("source_id", "start", "end")}
                assert_span(edit_span, context, f"diagnostics[{index}].fixes[{f_index}].edits[{e_index}]")
                ranges.append((edit["start"], edit["end"]))
            if ranges != sorted(ranges) or any(left[1] > right[0] for left, right in zip(ranges, ranges[1:])):
                die(f"diagnostics[{index}].fixes[{f_index}] edits overlap or are unsorted")
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


AST_FIELDS: dict[str, tuple[str, ...]] = {
    "Module": ("functions",),
    "FunctionDecl": ("name", "parameters", "return_type", "body"),
    "Parameter": ("name", "type"),
    "BlockStmt": ("statements",),
    "LetStmt": ("name", "type", "initializer"),
    "VarStmt": ("name", "type", "initializer"),
    "AssignStmt": ("target", "value"),
    "ExprStmt": ("expression",),
    "IfStmt": ("condition", "then_branch", "else_branch"),
    "WhileStmt": ("condition", "body"),
    "ReturnStmt": ("value",),
    "CallExpr": ("callee", "arguments"),
    "NameExpr": ("name",),
    "IntLiteral": ("value",),
    "BoolLiteral": ("value",),
    "StringLiteral": ("value",),
    "UnaryExpr": ("operator", "operand"),
    "BinaryExpr": ("operator", "left", "right"),
    "ErrorExpr": ("diagnostic_code",),
    "ErrorStmt": ("diagnostic_code",),
}


def walk_ast(
    value: Any,
    context: SourceContext,
    *,
    parent: tuple[int, int] | None = None,
    nodes: dict[int, dict[str, Any]] | None = None,
) -> dict[int, dict[str, Any]]:
    if nodes is None:
        nodes = {}
    if isinstance(value, dict):
        marker_fields = {"kind", "id", "span"}.intersection(value)
        if marker_fields:
            if marker_fields != {"kind", "id", "span"}:
                die("partial AST node must contain kind, id and span together")
            kind = value["kind"]
            node_id = value["id"]
            if not isinstance(kind, str) or not kind:
                die("AST node kind must be a non-empty string")
            if kind not in AST_FIELDS:
                die(f"unknown normalized AST kind: {kind}")
            missing = [field for field in AST_FIELDS[kind] if field not in value]
            if missing:
                die(f"AST {kind} is missing required fields: {missing}")
            if not isinstance(node_id, int) or isinstance(node_id, bool) or node_id < 0:
                die("AST node id must be a non-negative integer")
            if node_id in nodes:
                die(f"duplicate AST node id: {node_id}")
            nodes[node_id] = value
            assert_span(value["span"], context, f"AST node {node_id}")
            start, end = value["span"]["start"], value["span"]["end"]
            if parent is not None and not (parent[0] <= start <= end <= parent[1]):
                die(f"AST child {node_id} span is outside parent")
            current = (start, end)
        else:
            current = parent
        for child in value.values():
            walk_ast(child, context, parent=current, nodes=nodes)
    elif isinstance(value, list):
        for child in value:
            walk_ast(child, context, parent=parent, nodes=nodes)
    return nodes


def ast_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ast_projection(item) for key, item in value.items() if key not in {"id", "span"}}
    if isinstance(value, list):
        return [ast_projection(item) for item in value]
    return value


def canonical_json(payload: dict[str, Any]) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        die(f"payload cannot be canonicalized as strict JSON: {exc}")


def run_json_twice(prefix: Sequence[str], args: Sequence[str], *, workspace: Path, timeout: float) -> tuple[Result, dict[str, Any]]:
    first = run_process(prefix, args, workspace=workspace, timeout=timeout)
    first_payload = parse_json_result(first)
    second = run_process(prefix, args, workspace=workspace, timeout=timeout)
    second_payload = parse_json_result(second)
    if first.returncode != second.returncode or canonical_json(first_payload) != canonical_json(second_payload):
        die(f"non-deterministic result: {' '.join(first.argv)}")
    return first, first_payload


def read_golden(relative: str) -> Any:
    path = FIXTURES / relative
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die(f"cannot read golden fixture {relative}: {exc}")


def validate_tokens(tokens: Any, context: SourceContext, where: str) -> list[dict[str, Any]]:
    if not isinstance(tokens, list) or not tokens:
        die(f"{where}: tokens must be a non-empty array")
    previous_end = 0
    syntax_count = 0
    validated: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        if not isinstance(token, dict):
            die(f"{where}: tokens[{index}] must be an object")
        kind = token.get("kind")
        channel = token.get("channel")
        lexeme = token.get("lexeme")
        if not isinstance(kind, str) or not kind:
            die(f"{where}: tokens[{index}].kind must be non-empty")
        if channel not in {"syntax", "trivia"}:
            die(f"{where}: tokens[{index}].channel must be syntax or trivia")
        if not isinstance(lexeme, str):
            die(f"{where}: tokens[{index}].lexeme must be a string")
        assert_span(token.get("span"), context, f"{where}: tokens[{index}].span")
        start, end = token["span"]["start"], token["span"]["end"]
        if start < previous_end:
            die(f"{where}: token spans overlap or are out of order")
        if kind != "EOF":
            if start == end:
                die(f"{where}: non-EOF token has an empty span")
            try:
                actual_lexeme = context.data[start:end].decode("utf-8")
            except UnicodeError as exc:
                die(f"{where}: token slice is not UTF-8: {exc}")
            if actual_lexeme != lexeme:
                die(f"{where}: token lexeme does not match its source byte slice")
            if channel == "syntax":
                syntax_count += 1
        previous_end = end
        validated.append(token)
    eof = validated[-1]
    if eof.get("kind") != "EOF" or eof.get("channel") != "syntax" or eof.get("lexeme") != "":
        die(f"{where}: final token must be syntax EOF with empty lexeme")
    if eof["span"]["start"] != context.byte_length or eof["span"]["end"] != context.byte_length:
        die(f"{where}: final EOF must be at source byte length")
    if syntax_count == 0:
        die(f"{where}: EOF-only token stream is not a successful lexer result")
    return validated


def token_projection(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "kind": token["kind"],
            "channel": token["channel"],
            "lexeme": token["lexeme"],
            "start": token["span"]["start"],
            "end": token["span"]["end"],
        }
        for token in tokens
    ]


def validate_ast(ast: Any, context: SourceContext, where: str, *, require_program: bool) -> dict[int, dict[str, Any]]:
    if not isinstance(ast, dict) or ast.get("kind") != "Module":
        die(f"{where}: output must contain Module AST")
    nodes = walk_ast(ast, context)
    span = ast["span"]
    if span["start"] != 0 or span["end"] != context.byte_length:
        die(f"{where}: Module span must cover the complete source")
    functions = ast.get("functions")
    if require_program and (not isinstance(functions, list) or not functions):
        die(f"{where}: successful Module.functions must be non-empty")
    return nodes


def validate_semantic(
    semantic: Any,
    nodes: dict[int, dict[str, Any]],
    *,
    where: str,
) -> None:
    if not isinstance(semantic, dict):
        die(f"{where}: semantic summary must be an object")
    for field in ("symbols", "references", "types", "functions"):
        if not isinstance(semantic.get(field), list):
            die(f"{where}: semantic.{field} must be an array")
    symbols: dict[str, dict[str, Any]] = {}
    for index, symbol in enumerate(semantic["symbols"]):
        if not isinstance(symbol, dict):
            die(f"{where}: semantic.symbols[{index}] must be an object")
        symbol_id = symbol.get("id")
        if not isinstance(symbol_id, str) or not symbol_id or symbol_id in symbols:
            die(f"{where}: semantic symbol id must be unique and non-empty")
        if not all(isinstance(symbol.get(field), str) and symbol[field] for field in ("name", "kind", "type")):
            die(f"{where}: semantic symbol name/kind/type is invalid")
        if not isinstance(symbol.get("mutable"), bool):
            die(f"{where}: semantic symbol mutable must be boolean")
        if symbol.get("declaration_node") not in nodes:
            die(f"{where}: semantic symbol declaration_node is not in AST")
        symbols[symbol_id] = symbol
    reference_nodes: set[int] = set()
    for index, reference in enumerate(semantic["references"]):
        if not isinstance(reference, dict) or reference.get("node") not in nodes:
            die(f"{where}: semantic.references[{index}] has unknown AST node")
        if reference.get("symbol") not in symbols:
            die(f"{where}: semantic.references[{index}] has unknown symbol")
        reference_nodes.add(reference["node"])
    typed_nodes: set[int] = set()
    for index, item in enumerate(semantic["types"]):
        if not isinstance(item, dict) or item.get("node") not in nodes:
            die(f"{where}: semantic.types[{index}] has unknown AST node")
        if not isinstance(item.get("type"), str) or not item["type"]:
            die(f"{where}: semantic.types[{index}] has invalid type")
        typed_nodes.add(item["node"])
    for node_id, node in nodes.items():
        if node["kind"] == "NameExpr" and node_id not in reference_nodes:
            die(f"{where}: NameExpr {node_id} has no symbol reference")
        if (node["kind"].endswith("Expr") or node["kind"].endswith("Literal")) and node_id not in typed_nodes:
            die(f"{where}: expression node {node_id} has no type")
    function_nodes = {node_id for node_id, node in nodes.items() if node["kind"] == "FunctionDecl"}
    summarized: set[int] = set()
    for index, function in enumerate(semantic["functions"]):
        if not isinstance(function, dict) or function.get("symbol") not in symbols:
            die(f"{where}: semantic.functions[{index}] has unknown symbol")
        declaration = symbols[function["symbol"]]["declaration_node"]
        if declaration not in function_nodes:
            die(f"{where}: semantic.functions[{index}] does not reference a FunctionDecl")
        if not isinstance(function.get("return_type"), str) or not isinstance(function.get("all_paths_return"), bool):
            die(f"{where}: semantic.functions[{index}] is malformed")
        if function["return_type"] != "Unit" and not function["all_paths_return"]:
            die(f"{where}: non-Unit function is not all-path-return")
        summarized.add(declaration)
    if summarized != function_nodes:
        die(f"{where}: each FunctionDecl requires one flow summary")


def semantic_projection(semantic: dict[str, Any], nodes: dict[int, dict[str, Any]]) -> dict[str, Any]:
    symbols = {symbol["id"]: symbol for symbol in semantic["symbols"]}

    def node_key(node_id: int) -> dict[str, Any]:
        node = nodes[node_id]
        return {"kind": node["kind"], "start": node["span"]["start"], "end": node["span"]["end"]}

    symbol_projection = []
    for symbol in symbols.values():
        symbol_projection.append({
            "name": symbol["name"],
            "kind": symbol["kind"],
            "type": symbol["type"],
            "mutable": symbol["mutable"],
            "declaration": node_key(symbol["declaration_node"]),
        })
    reference_projection = []
    for reference in semantic["references"]:
        target = symbols[reference["symbol"]]
        reference_projection.append({
            "reference": node_key(reference["node"]),
            "target_name": target["name"],
            "target_declaration_start": nodes[target["declaration_node"]]["span"]["start"],
        })
    type_projection = [
        {"node": node_key(item["node"]), "type": item["type"]} for item in semantic["types"]
    ]
    function_projection = []
    for function in semantic["functions"]:
        target = symbols[function["symbol"]]
        function_projection.append({
            "declaration_start": nodes[target["declaration_node"]]["span"]["start"],
            "return_type": function["return_type"],
            "all_paths_return": function["all_paths_return"],
        })
    key = lambda item: canonical_json(item)
    return {
        "symbols": sorted(symbol_projection, key=key),
        "references": sorted(reference_projection, key=key),
        "types": sorted(type_projection, key=key),
        "functions": sorted(function_projection, key=key),
    }


def validate_runtime_value(value: Any, where: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict) or set(value) != {"type", "value"}:
        die(f"{where}: return_value must be null or a tagged value")
    type_name = value["type"]
    raw = value["value"]
    if type_name == "Int" and (not isinstance(raw, int) or isinstance(raw, bool) or not -(2**63) <= raw <= 2**63 - 1):
        die(f"{where}: Int return value must be signed i64")
    if type_name == "Bool" and not isinstance(raw, bool):
        die(f"{where}: Bool return value must be boolean")
    if type_name == "String" and not isinstance(raw, str):
        die(f"{where}: String return value must be a string")
    if type_name == "Unit" and raw is not None:
        die(f"{where}: Unit return value must be null")
    if type_name not in {"Int", "Bool", "String", "Unit"}:
        die(f"{where}: unknown return value type {type_name!r}")


def runtime_projection(result: Result, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "exit": result.returncode,
        "stdout": payload.get("stdout"),
        "return_value": payload.get("return_value"),
        "codes": error_codes(payload),
    }


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
    context = assert_envelope(payload, "lex", source)
    assert_exit_and_codes(result, payload, 0, [])
    validate_tokens(payload.get("tokens"), context, "source stage")
    print("PASS source UTF-8 byte spans and deterministic output")


def stage_lex(prefix: Sequence[str], workspace: Path, timeout: float, manifest: dict[str, Any]) -> None:
    cases = [*manifest["valid"], *[c for c in manifest["invalid"] if c["stage"] == "lex"]]
    for case in cases:
        source = FIXTURES / case["file"]
        expected_exit = case.get("exit", 0)
        expected_codes = case.get("codes", [])
        result, payload = run_json_twice(prefix, ["lex", source, "--json"], workspace=workspace, timeout=timeout)
        context = assert_envelope(payload, "lex", source)
        assert_exit_and_codes(result, payload, expected_exit, expected_codes)
        tokens = validate_tokens(payload.get("tokens"), context, case["file"])
        golden = case.get("golden", {}).get("tokens")
        if golden and token_projection(tokens) != read_golden(golden):
            die(f"{case['file']}: token projection differs from golden reference")
        print(f"PASS lex {case['file']}")


def stage_parse(prefix: Sequence[str], workspace: Path, timeout: float, manifest: dict[str, Any]) -> None:
    cases = [*manifest["valid"], *[c for c in manifest["invalid"] if c["stage"] == "parse"]]
    for case in cases:
        source = FIXTURES / case["file"]
        result, payload = run_json_twice(prefix, ["parse", source, "--json"], workspace=workspace, timeout=timeout)
        context = assert_envelope(payload, "parse", source)
        assert_exit_and_codes(result, payload, case.get("exit", 0), case.get("codes", []))
        ast = payload.get("ast")
        validate_ast(ast, context, case["file"], require_program=case.get("exit", 0) == 0)
        golden = case.get("golden", {}).get("ast")
        if golden and ast_projection(ast) != read_golden(golden):
            die(f"{case['file']}: normalized AST differs from golden reference")
        print(f"PASS parse {case['file']}")


def stage_check(prefix: Sequence[str], workspace: Path, timeout: float, manifest: dict[str, Any]) -> None:
    cases = [*manifest["valid"], *manifest["invalid"]]
    for case in cases:
        source = FIXTURES / case["file"]
        result, payload = run_json_twice(prefix, ["check", source, "--json"], workspace=workspace, timeout=timeout)
        context = assert_envelope(payload, "check", source)
        assert_exit_and_codes(result, payload, case.get("exit", 0), case.get("codes", []))
        if case.get("exit", 0) == 0:
            ast = payload.get("ast")
            nodes = validate_ast(ast, context, case["file"], require_program=True)
            validate_semantic(payload.get("semantic"), nodes, where=case["file"])
            golden = case.get("golden", {}).get("semantic")
            if golden and semantic_projection(payload["semantic"], nodes) != read_golden(golden):
                die(f"{case['file']}: semantic summary differs from golden reference")
        print(f"PASS check {case['file']}")


def stage_run(prefix: Sequence[str], workspace: Path, timeout: float, manifest: dict[str, Any]) -> None:
    cases = [*manifest["valid"], *manifest["runtime"]]
    for case in cases:
        source = FIXTURES / case["file"]
        result, payload = run_json_twice(prefix, ["run", source, "--json"], workspace=workspace, timeout=timeout)
        assert_envelope(payload, "run", source)
        assert_exit_and_codes(result, payload, case.get("exit", 0), case.get("codes", []))
        if "stdout" not in payload or not isinstance(payload["stdout"], str):
            die(f"{case['file']}: run payload must contain string stdout")
        if "return_value" not in payload:
            die(f"{case['file']}: run payload must contain return_value")
        validate_runtime_value(payload["return_value"], case["file"])
        if payload["stdout"] != case.get("stdout", payload["stdout"]):
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
    vm_cases = [case for case in [*manifest["valid"], *manifest["runtime"]] if case.get("vm")]
    if not vm_cases:
        die("manifest must select at least one VM differential case")
    for case in vm_cases:
        source = FIXTURES / case["file"]
        disassembled, disassembly_payload = run_json_twice(
            prefix, ["disassemble", source, "--json"], workspace=workspace, timeout=timeout
        )
        assert_envelope(disassembly_payload, "disassemble", source)
        assert_exit_and_codes(disassembled, disassembly_payload, 0, [])
        module = disassembly_payload.get("module")
        text = disassembly_payload.get("text")
        if not isinstance(module, dict) or not isinstance(text, str) or not text:
            die(f"{case['file']}: disassemble requires non-empty text and module object")
        for opcode in case.get("required_opcodes", []):
            if opcode not in text:
                die(f"{case['file']}: disassembly is missing required opcode {opcode}")
        with tempfile.TemporaryDirectory(prefix="mica-bytecode-") as tmp:
            module_path = Path(tmp) / "module.json"
            module_path.write_text(
                json.dumps(module, ensure_ascii=False, sort_keys=True, allow_nan=False), encoding="utf-8"
            )
            verified, verified_payload = run_json_twice(
                prefix, ["verify-bytecode", module_path, "--json"], workspace=workspace, timeout=timeout
            )
            assert_envelope(verified_payload, "verify-bytecode", module_path)
            assert_exit_and_codes(verified, verified_payload, 0, [])

        outcomes: dict[str, dict[str, Any]] = {}
        for engine in ("interpreter", "vm"):
            result, payload = run_json_twice(
                prefix, ["run", source, "--engine", engine, "--json"], workspace=workspace, timeout=timeout
            )
            assert_envelope(payload, "run", source)
            assert_exit_and_codes(result, payload, case.get("exit", 0), case.get("codes", []))
            if "stdout" not in payload or "return_value" not in payload:
                die(f"{case['file']}: {engine} run payload is incomplete")
            validate_runtime_value(payload["return_value"], f"{case['file']} {engine}")
            outcomes[engine] = runtime_projection(result, payload)
        if outcomes["interpreter"] != outcomes["vm"]:
            die(f"{case['file']}: interpreter/VM outcome mismatch")
        expected = {
            "exit": case.get("exit", 0),
            "stdout": case.get("stdout", ""),
            "return_value": case.get("return"),
            "codes": case.get("codes", []),
        }
        if outcomes["interpreter"] != expected:
            die(f"{case['file']}: VM differential result differs from manifest")
        print(f"PASS VM compile verify disassemble differential {case['file']}")


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
            formatted_context = assert_envelope(payload, "check", formatted)
            assert_exit_and_codes(parsed, payload, 0, [])
            formatted_nodes = validate_ast(payload.get("ast"), formatted_context, case["file"], require_program=True)
            validate_semantic(payload.get("semantic"), formatted_nodes, where=case["file"])
            original = run_process(prefix, ["check", source, "--json"], workspace=workspace, timeout=timeout)
            original_payload = parse_json_result(original)
            original_context = assert_envelope(original_payload, "check", source)
            assert_exit_and_codes(original, original_payload, 0, [])
            original_nodes = validate_ast(
                original_payload.get("ast"), original_context, case["file"], require_program=True
            )
            validate_semantic(original_payload.get("semantic"), original_nodes, where=case["file"])
            if ast_projection(original_payload["ast"]) != ast_projection(payload["ast"]):
                die(f"formatter changed normalized AST: {case['file']}")
        print(f"PASS format {case['file']}")
    lint_cases = manifest.get("lint")
    if not isinstance(lint_cases, list) or not lint_cases:
        die("manifest lint category must be non-empty for formatter+linter path")
    for case in lint_cases:
        source = FIXTURES / case["file"]
        result, payload = run_json_twice(prefix, ["lint", source, "--json"], workspace=workspace, timeout=timeout)
        assert_envelope(payload, "lint", source)
        assert_exit_and_codes(result, payload, case.get("exit", 0), [])
        actual_codes = [item["code"] for item in payload["diagnostics"]]
        if actual_codes != case.get("codes", []):
            die(f"{case['file']}: lint codes mismatch: expected {case.get('codes')}, got {actual_codes}")
        unsafe = set(case.get("unsafe_no_machine_fix", []))
        for diagnostic in payload["diagnostics"]:
            if diagnostic["code"] in unsafe and any(
                fix.get("applicability") == "machine-applicable" for fix in diagnostic.get("fixes", [])
            ):
                die(f"{case['file']}: unsafe lint {diagnostic['code']} offered a machine-applicable fix")
        print(f"PASS lint diagnostics and fix safety {case['file']}")


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
    context = assert_envelope(payload, "check", sample)
    if error_codes(payload) != ["MICA3003"]:
        die("runner self-test code extraction failed")
    span = {"source_id": str(sample), "start": 0, "end": len(data)}
    ast = {
        "kind": "Module",
        "id": 0,
        "span": span,
        "functions": [{
            "kind": "FunctionDecl",
            "id": 1,
            "span": span,
            "name": "main",
            "parameters": [],
            "return_type": "Int",
            "body": {
                "kind": "BlockStmt",
                "id": 2,
                "span": span,
                "statements": [{
                    "kind": "ReturnStmt",
                    "id": 3,
                    "span": span,
                    "value": {"kind": "IntLiteral", "id": 4, "span": span, "value": 0},
                }],
            },
        }],
    }
    walk_ast(ast, context)
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
