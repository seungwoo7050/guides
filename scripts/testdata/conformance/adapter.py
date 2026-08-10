#!/usr/bin/env python3
"""Fixture-backed Mica checker test double.

This program is deliberately *not* a Mica reference implementation.  It reads
the public fixture manifest and emits deterministic, structurally realistic
payloads so that ``check_submission.py`` can test its own acceptance and
rejection paths.  Inputs outside the public fixtures receive only a small
syntactic projection suitable for formatter round-trip checks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[3]
CAPSTONE = ROOT / "exercises" / "08-mica-capstone"
FIXTURES = CAPSTONE / "fixtures"
MANIFEST = FIXTURES / "manifest.json"

MUTANTS = {
    "none",
    "eof-only",
    "empty-module",
    "partial-node",
    "wrong-source-id",
    "split-utf8",
    "wrong-phase",
    "nan",
    "wrong-run",
    "accept-invalid-bytecode",
    "vm-mismatch",
    "non-idempotent-format",
    "unsafe-lint-fix",
    "timeout",
    "output-flood",
}

KEYWORDS = {
    "fn": "FN",
    "let": "LET",
    "var": "VAR",
    "if": "IF",
    "else": "ELSE",
    "while": "WHILE",
    "return": "RETURN",
    "true": "TRUE",
    "false": "FALSE",
}
TWO_CHAR_TOKENS = {
    "->": "ARROW",
    "==": "EQ_EQ",
    "!=": "BANG_EQ",
    "<=": "LESS_EQ",
    ">=": "GREATER_EQ",
    "&&": "AMP_AMP",
    "||": "PIPE_PIPE",
}
ONE_CHAR_TOKENS = {
    "(": "LEFT_PAREN",
    ")": "RIGHT_PAREN",
    "{": "LEFT_BRACE",
    "}": "RIGHT_BRACE",
    ",": "COMMA",
    ":": "COLON",
    ";": "SEMICOLON",
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    "%": "PERCENT",
    "=": "EQUAL",
    "!": "BANG",
    "<": "LESS",
    ">": "GREATER",
}


def read_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def fixture_case(path: Path, manifest: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    try:
        relative = path.resolve().relative_to(FIXTURES.resolve()).as_posix()
    except ValueError:
        return None
    for category in ("valid", "invalid", "runtime", "format", "bytecode_invalid"):
        for case in manifest.get(category, []):
            if case.get("file") == relative:
                return category, case
    return None


def source_metadata(path: Path, data: bytes) -> dict[str, Any]:
    return {"id": str(path.resolve()), "byte_length": len(data)}


def span(source_id: str, start: int, end: int) -> dict[str, Any]:
    return {"source_id": source_id, "start": start, "end": end}


def char_byte_offsets(text: str) -> list[int]:
    offsets = [0]
    total = 0
    for character in text:
        total += len(character.encode("utf-8"))
        offsets.append(total)
    return offsets


def phase_for_code(code: str) -> str:
    number = int(code[4:])
    if 1000 <= number < 2000:
        return "lex"
    if 2000 <= number < 3000:
        return "parse"
    if 3000 <= number < 3100:
        return "resolution"
    if 3100 <= number < 3200:
        return "type"
    if 3200 <= number < 4000:
        return "flow"
    if 4000 <= number < 5000:
        return "runtime"
    if 5000 <= number < 6000:
        return "bytecode"
    if 6000 <= number < 7000:
        return "lint"
    return "internal"


def diagnostic_span(code: str, text: str, offsets: list[int]) -> tuple[int, int]:
    needles = {
        "MICA1001": "@",
        "MICA1002": '"missing end',
        "MICA1003": "\\q",
        "MICA1004": "9223372036854775808",
        "MICA2001": "return value",
        "MICA2002": "else",
        "MICA3001": "value",
        "MICA3002": "value",
        "MICA3003": "missing",
        "MICA3004": "value =",
        "MICA3101": "true",
        "MICA3102": "false",
        "MICA3103": "add(1)",
        "MICA3105": "1",
        "MICA3106": "false",
        "MICA3201": "choose",
        "MICA3202": "main",
        "MICA4001": "/",
        "MICA4002": "+ 1",
        "MICA4003": "recurse",
        "MICA4004": "while",
    }
    needle = needles.get(code, "")
    start_char = text.find(needle) if needle else 0
    if start_char < 0:
        start_char = 0
        end_char = 0
    else:
        end_char = start_char + len(needle)
    return offsets[start_char], offsets[end_char]


def make_diagnostics(
    codes: Iterable[str], path: Path, text: str, *, mutant: str
) -> list[dict[str, Any]]:
    source_id = str(path.resolve())
    offsets = char_byte_offsets(text)
    diagnostics: list[dict[str, Any]] = []
    for code in codes:
        start, end = diagnostic_span(code, text, offsets)
        phase = phase_for_code(code)
        if mutant == "wrong-phase":
            phase = "runtime" if phase != "runtime" else "lex"
        diagnostics.append(
            {
                "code": code,
                "severity": "error",
                "phase": phase,
                "message": f"fixture-backed diagnostic {code}",
                "primary": span(source_id, start, end),
                "secondary": [],
                "notes": [],
                "fixes": [],
            }
        )
    diagnostics.sort(
        key=lambda item: (
            item["primary"]["start"],
            item["primary"]["end"],
            item["code"],
        )
    )
    return diagnostics


def expected_for(command: str, case_info: tuple[str, dict[str, Any]] | None) -> tuple[int, list[str]]:
    if case_info is None:
        return 0, []
    category, case = case_info
    if command == "lex":
        if category == "invalid" and case.get("stage") == "lex":
            return int(case.get("exit", 1)), list(case.get("codes", []))
        return 0, []
    if command == "parse":
        if category == "invalid" and case.get("stage") in {"lex", "parse"}:
            return int(case.get("exit", 1)), list(case.get("codes", []))
        return 0, []
    if command == "check":
        if category == "invalid":
            return int(case.get("exit", 1)), list(case.get("codes", []))
        return 0, []
    if command == "run":
        if category in {"invalid", "runtime"}:
            return int(case.get("exit", 1)), list(case.get("codes", []))
        return 0, []
    raise AssertionError(f"unexpected command: {command}")


def tokenize(path: Path, text: str, *, mutant: str) -> list[dict[str, Any]]:
    source_id = str(path.resolve())
    offsets = char_byte_offsets(text)
    tokens: list[dict[str, Any]] = []
    index = 0
    while index < len(text):
        character = text[index]
        if character.isspace():
            index += 1
            continue
        if text.startswith("//", index):
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline
            continue

        start = index
        pair = text[index : index + 2]
        if pair in TWO_CHAR_TOKENS:
            index += 2
            kind = TWO_CHAR_TOKENS[pair]
        elif character.isalpha() or character == "_":
            index += 1
            while index < len(text) and (text[index].isalnum() or text[index] == "_"):
                index += 1
            lexeme = text[start:index]
            kind = KEYWORDS.get(lexeme, "IDENTIFIER")
        elif character.isdigit():
            index += 1
            while index < len(text) and text[index].isdigit():
                index += 1
            kind = "INTEGER"
        elif character == '"':
            index += 1
            escaped = False
            while index < len(text):
                current = text[index]
                index += 1
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    break
            kind = "STRING"
        elif character in ONE_CHAR_TOKENS:
            index += 1
            kind = ONE_CHAR_TOKENS[character]
        else:
            index += 1
            kind = "ERROR"

        tokens.append(
            {
                "kind": kind,
                "channel": "syntax",
                "lexeme": text[start:index],
                "span": span(source_id, offsets[start], offsets[index]),
            }
        )

    eof = {
        "kind": "EOF",
        "channel": "syntax",
        "lexeme": "",
        "span": span(source_id, offsets[-1], offsets[-1]),
    }
    if mutant == "eof-only":
        return [eof]
    tokens.append(eof)

    if mutant == "wrong-source-id" and tokens:
        tokens[0]["span"]["source_id"] = "mutant://wrong-source"
    if mutant == "split-utf8":
        data = text.encode("utf-8")
        continuation = next((i for i, byte in enumerate(data) if byte & 0xC0 == 0x80), None)
        if continuation is not None:
            target = next(
                (
                    token
                    for token in tokens[:-1]
                    if token["span"]["start"] < continuation < token["span"]["end"]
                ),
                None,
            )
            if target is not None:
                target["span"]["start"] = continuation
    return tokens


def matching_brace(text: str, open_brace: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    for index in range(open_brace, len(text)):
        character = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return index
    return len(text) - 1 if text else 0


class AstBuilder:
    def __init__(self, path: Path, text: str) -> None:
        self.source_id = str(path.resolve())
        self.text = text
        self.offsets = char_byte_offsets(text)
        self.next_id = 0

    def new_node(self, kind: str, start_char: int, end_char: int, **fields: Any) -> dict[str, Any]:
        node = {
            "kind": kind,
            "id": self.next_id,
            "span": span(self.source_id, self.offsets[start_char], self.offsets[end_char]),
            **fields,
        }
        self.next_id += 1
        return node

    def expression(self, raw_start: int, raw_end: int) -> dict[str, Any]:
        while raw_start < raw_end and self.text[raw_start].isspace():
            raw_start += 1
        while raw_end > raw_start and self.text[raw_end - 1].isspace():
            raw_end -= 1
        value = self.text[raw_start:raw_end]
        if re.fullmatch(r"[0-9]+", value):
            return self.new_node("IntLiteral", raw_start, raw_end, value=int(value))
        if value in {"true", "false"}:
            return self.new_node("BoolLiteral", raw_start, raw_end, value=value == "true")
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            return self.new_node("NameExpr", raw_start, raw_end, name=value)
        integer = re.search(r"[0-9]+", value)
        if integer is not None:
            start = raw_start + integer.start()
            end = raw_start + integer.end()
            return self.new_node("IntLiteral", start, end, value=int(integer.group()))
        identifier = re.search(r"[A-Za-z_][A-Za-z0-9_]*", value)
        if identifier is not None:
            start = raw_start + identifier.start()
            end = raw_start + identifier.end()
            if identifier.group() in {"true", "false"}:
                return self.new_node(
                    "BoolLiteral",
                    start,
                    end,
                    value=identifier.group() == "true",
                )
            return self.new_node("NameExpr", start, end, name=identifier.group())
        return self.new_node(
            "ErrorExpr",
            raw_start,
            raw_end,
            diagnostic_code="MICA2002",
        )

    def statements(self, body_start: int, body_end: int) -> list[dict[str, Any]]:
        statements: list[dict[str, Any]] = []
        region = self.text[body_start:body_end]
        declaration_re = re.compile(
            r"\b(let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(Int|Bool|String|Unit)\s*=\s*([^;]+);"
        )
        for match in declaration_re.finditer(region):
            absolute_start = body_start + match.start()
            absolute_end = body_start + match.end()
            expression_start = body_start + match.start(4)
            expression_end = body_start + match.end(4)
            initializer = self.expression(expression_start, expression_end)
            statements.append(
                self.new_node(
                    "VarStmt" if match.group(1) == "var" else "LetStmt",
                    absolute_start,
                    absolute_end,
                    name=match.group(2),
                    mutable=match.group(1) == "var",
                    type=match.group(3),
                    initializer=initializer,
                )
            )

        for match in re.finditer(r"\breturn\s+([^;]+);", region):
            absolute_start = body_start + match.start()
            absolute_end = body_start + match.end()
            expression_start = body_start + match.start(1)
            expression_end = body_start + match.end(1)
            value = self.expression(expression_start, expression_end)
            statements.append(
                self.new_node("ReturnStmt", absolute_start, absolute_end, value=value)
            )

        for match in re.finditer(r"\bprint_(?:int|string)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*;", region):
            absolute_start = body_start + match.start()
            absolute_end = body_start + match.end()
            name_start = body_start + match.start(1)
            name_end = body_start + match.end(1)
            reference = self.new_node("NameExpr", name_start, name_end, name=match.group(1))
            statements.append(
                self.new_node(
                    "ExprStmt",
                    absolute_start,
                    absolute_end,
                    expression=reference,
                )
            )

        statements.sort(key=lambda node: (node["span"]["start"], node["id"]))
        return statements

    def build(self) -> dict[str, Any]:
        module = self.new_node("Module", 0, len(self.text), functions=[])
        function_re = re.compile(
            r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*->\s*(Int|Bool|String|Unit)\s*\{",
            re.DOTALL,
        )
        functions: list[dict[str, Any]] = []
        for match in function_re.finditer(self.text):
            open_brace = match.end() - 1
            close_brace = matching_brace(self.text, open_brace)
            parameters: list[dict[str, Any]] = []
            parameter_base = match.start(2)
            for parameter in re.finditer(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(Int|Bool|String|Unit)", match.group(2)
            ):
                start = parameter_base + parameter.start()
                end = parameter_base + parameter.end()
                parameters.append(
                    self.new_node(
                        "Parameter",
                        start,
                        end,
                        name=parameter.group(1),
                        type=parameter.group(2),
                    )
                )
            body = self.new_node(
                "BlockStmt",
                open_brace,
                close_brace + 1,
                statements=self.statements(open_brace + 1, close_brace),
            )
            functions.append(
                self.new_node(
                    "FunctionDecl",
                    match.start(),
                    close_brace + 1,
                    name=match.group(1),
                    parameters=parameters,
                    return_type=match.group(3),
                    body=body,
                )
            )
        module["functions"] = functions
        return module


def iter_ast_nodes(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if {"kind", "id", "span"}.issubset(value):
            yield value
        for child in value.values():
            yield from iter_ast_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_ast_nodes(child)


def brace_depths(text: str) -> tuple[list[int], list[int]]:
    depths: list[int] = []
    depth = 0
    for character in text:
        depths.append(depth)
        if character == "{":
            depth += 1
        elif character == "}":
            depth = max(0, depth - 1)
    depths.append(depth)
    return depths, char_byte_offsets(text)


def char_index_for_byte(offsets: list[int], byte_offset: int) -> int:
    low = 0
    high = len(offsets)
    while low < high:
        middle = (low + high) // 2
        if offsets[middle] < byte_offset:
            low = middle + 1
        else:
            high = middle
    return min(low, len(offsets) - 1)


def semantic_summary(ast: dict[str, Any], text: str) -> dict[str, Any]:
    nodes = list(iter_ast_nodes(ast))
    functions = [node for node in nodes if node["kind"] == "FunctionDecl"]
    declarations = [node for node in nodes if node["kind"] in {"LetStmt", "VarStmt"}]
    references = [node for node in nodes if node["kind"] == "NameExpr"]
    symbols: list[dict[str, Any]] = []
    function_facts: list[dict[str, Any]] = []
    declaration_symbols: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for function in functions:
        symbol_id = f"s{len(symbols)}"
        parameter_types = ", ".join(item["type"] for item in function["parameters"])
        symbol = {
            "id": symbol_id,
            "name": function["name"],
            "kind": "function",
            "type": f"fn({parameter_types}) -> {function['return_type']}",
            "mutable": False,
            "declaration_node": function["id"],
        }
        symbols.append(symbol)
        has_return = any(
            node["kind"] == "ReturnStmt"
            and function["span"]["start"] <= node["span"]["start"]
            and node["span"]["end"] <= function["span"]["end"]
            for node in nodes
        )
        function_facts.append(
            {
                "symbol": symbol_id,
                "return_type": function["return_type"],
                "all_paths_return": has_return,
            }
        )

    for declaration in declarations:
        symbol = {
            "id": f"s{len(symbols)}",
            "name": declaration["name"],
            "kind": "local",
            "type": declaration["type"],
            "mutable": declaration["mutable"],
            "declaration_node": declaration["id"],
        }
        symbols.append(symbol)
        declaration_symbols.append((declaration, symbol))

    depths, offsets = brace_depths(text)
    reference_facts: list[dict[str, Any]] = []
    for reference in references:
        ref_start = reference["span"]["start"]
        ref_char = char_index_for_byte(offsets, ref_start)
        ref_depth = depths[ref_char]
        candidates: list[tuple[int, int, dict[str, Any]]] = []
        for declaration, symbol in declaration_symbols:
            declaration_start = declaration["span"]["start"]
            declaration_char = char_index_for_byte(offsets, declaration_start)
            declaration_depth = depths[declaration_char]
            if (
                symbol["name"] == reference["name"]
                and declaration_start < ref_start
                and declaration_depth <= ref_depth
            ):
                candidates.append((declaration_depth, declaration_start, symbol))
        if candidates:
            symbol = max(candidates, key=lambda item: (item[0], item[1]))[2]
            reference_facts.append({"node": reference["id"], "symbol": symbol["id"]})

    types: list[dict[str, Any]] = []
    for node in nodes:
        inferred: str | None = None
        if node["kind"] == "IntLiteral":
            inferred = "Int"
        elif node["kind"] == "BoolLiteral":
            inferred = "Bool"
        elif node["kind"] in {"LetStmt", "VarStmt"}:
            inferred = node["type"]
        elif node["kind"] == "FunctionDecl":
            inferred = f"fn() -> {node['return_type']}"
        elif node["kind"] == "NameExpr":
            fact = next((item for item in reference_facts if item["node"] == node["id"]), None)
            if fact is not None:
                inferred = next(symbol["type"] for symbol in symbols if symbol["id"] == fact["symbol"])
        elif node["kind"] == "ErrorExpr":
            inferred = "Error"
        if inferred is not None:
            types.append({"node": node["id"], "type": inferred})

    return {
        "symbols": symbols,
        "references": reference_facts,
        "types": types,
        "functions": function_facts,
    }


def mutate_ast(ast: dict[str, Any], mutant: str) -> None:
    if mutant == "empty-module":
        ast["functions"] = []
    elif mutant == "partial-node" and ast.get("functions"):
        ast["functions"][0]["body"]["statements"].append(
            {"kind": "ReturnStmt", "value": {"kind": "IntLiteral", "value": 0}}
        )
    elif mutant == "wrong-source-id":
        ast["span"]["source_id"] = "mutant://wrong-source"


def envelope(command: str, path: Path, data: bytes, diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "command": command,
        "source": source_metadata(path, data),
        "diagnostics": diagnostics,
    }


def apply_nan(payload: dict[str, Any], mutant: str) -> None:
    if mutant == "nan":
        payload["mutant_non_finite"] = float("nan")


def emit_json(payload: dict[str, Any], exit_code: int) -> int:
    json.dump(payload, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return exit_code


def command_lex(args: argparse.Namespace, manifest: dict[str, Any]) -> int:
    path = args.file.resolve()
    data = path.read_bytes()
    text = data.decode("utf-8")
    case_info = fixture_case(path, manifest)
    exit_code, codes = expected_for("lex", case_info)
    diagnostics = make_diagnostics(codes, path, text, mutant=args.mutant)
    payload = envelope("lex", path, data, diagnostics)
    payload["tokens"] = tokenize(path, text, mutant=args.mutant)
    apply_nan(payload, args.mutant)
    return emit_json(payload, exit_code)


def command_parse_or_check(
    command: str, args: argparse.Namespace, manifest: dict[str, Any]
) -> int:
    path = args.file.resolve()
    data = path.read_bytes()
    text = data.decode("utf-8")
    case_info = fixture_case(path, manifest)
    exit_code, codes = expected_for(command, case_info)
    diagnostics = make_diagnostics(codes, path, text, mutant=args.mutant)
    ast = AstBuilder(path, text).build()
    mutate_ast(ast, args.mutant)
    payload = envelope(command, path, data, diagnostics)
    payload["ast"] = ast
    if command == "check" and exit_code == 0:
        payload["semantic"] = semantic_summary(ast, text)
    apply_nan(payload, args.mutant)
    return emit_json(payload, exit_code)


def command_run(args: argparse.Namespace, manifest: dict[str, Any]) -> int:
    path = args.file.resolve()
    data = path.read_bytes()
    text = data.decode("utf-8")
    case_info = fixture_case(path, manifest)
    exit_code, codes = expected_for("run", case_info)
    diagnostics = make_diagnostics(codes, path, text, mutant=args.mutant)
    stdout = ""
    return_value: Any = {"type": "Int", "value": 0}
    if case_info is not None:
        _, case = case_info
        stdout = case.get("stdout", "")
        return_value = case.get("return")
    if args.mutant == "wrong-run":
        stdout = "mutant output\n"
        return_value = {"type": "Int", "value": -1}
    if args.mutant == "vm-mismatch" and args.engine == "vm":
        stdout = stdout + "vm mismatch\n"
        if return_value is not None:
            return_value = {"type": "Int", "value": -99}
    payload = envelope("run", path, data, diagnostics)
    payload.update(
        {
            "engine": args.engine,
            "stdout": stdout,
            "return_value": return_value,
        }
    )
    apply_nan(payload, args.mutant)
    return emit_json(payload, exit_code)


def bytecode_module(path: Path, case_info: tuple[str, dict[str, Any]] | None) -> dict[str, Any]:
    return_value: Any = {"type": "Int", "value": 0}
    if case_info is not None:
        _, case = case_info
        if case.get("return") is not None:
            return_value = case["return"]
    constant = return_value if isinstance(return_value, dict) else {"type": "Int", "value": 0}
    return {
        "version": 1,
        "constants": [constant],
        "entry": 0,
        "functions": [
            {
                "name": "main",
                "parameter_types": [],
                "return_type": constant.get("type", "Int"),
                "local_types": [],
                "instructions": [
                    {"op": "CONST", "index": 0},
                    {"op": "RETURN"},
                ],
                "source_map": {
                    "0": {"source_id": str(path.resolve()), "start": 0, "end": 0},
                    "1": {"source_id": str(path.resolve()), "start": 0, "end": 0},
                },
            }
        ],
    }


def disassembly_text(module: dict[str, Any], required_opcodes: Iterable[str]) -> str:
    function = module["functions"][0]
    required = " ".join(required_opcodes)
    return (
        f"function {function['name']}() -> {function['return_type']}\n"
        "locals []\n"
        "0000 CONST 0    ; [] -> [Int]\n"
        "0001 RETURN     ; [Int] -> []\n"
        f"fixture-required-opcodes {required}\n"
    )


def command_disassemble(args: argparse.Namespace, manifest: dict[str, Any]) -> int:
    path = args.file.resolve()
    data = path.read_bytes()
    case_info = fixture_case(path, manifest)
    module = bytecode_module(path, case_info)
    required_opcodes = case_info[1].get("required_opcodes", []) if case_info is not None else []
    text = disassembly_text(module, required_opcodes)
    if not args.json:
        sys.stdout.write(text)
        return 0
    payload = envelope("disassemble", path, data, [])
    payload.update({"module": module, "text": text})
    apply_nan(payload, args.mutant)
    return emit_json(payload, 0)


def command_verify_bytecode(args: argparse.Namespace, manifest: dict[str, Any]) -> int:
    path = args.file.resolve()
    data = path.read_bytes()
    text = data.decode("utf-8")
    case_info = fixture_case(path, manifest)
    codes: list[str] = []
    exit_code = 0
    if case_info is not None and case_info[0] == "bytecode_invalid":
        codes = list(case_info[1].get("codes", []))
        exit_code = 1
    else:
        try:
            module = json.loads(text)
        except json.JSONDecodeError:
            module = None
        if not isinstance(module, dict) or module.get("version") != 1:
            codes = ["MICA5001"]
            exit_code = 1
    if args.mutant == "accept-invalid-bytecode":
        codes = []
        exit_code = 0
    diagnostics = make_diagnostics(codes, path, text, mutant=args.mutant)
    payload = envelope("verify-bytecode", path, data, diagnostics)
    payload["valid"] = exit_code == 0
    apply_nan(payload, args.mutant)
    return emit_json(payload, exit_code)


def canonical_format(path: Path, text: str, manifest: dict[str, Any], mutant: str) -> str:
    case_info = fixture_case(path, manifest)
    if case_info is not None and case_info[0] == "format":
        expected = case_info[1].get("expected")
        if isinstance(expected, str):
            return (FIXTURES / expected).read_text(encoding="utf-8")
    if mutant == "non-idempotent-format":
        return text.rstrip("\n") + " \n"
    return text


def command_format(args: argparse.Namespace, manifest: dict[str, Any]) -> int:
    path = args.file.resolve()
    text = path.read_text(encoding="utf-8")
    sys.stdout.write(canonical_format(path, text, manifest, args.mutant))
    return 0


def lint_diagnostics(path: Path, text: str, mutant: str) -> list[dict[str, Any]]:
    source_id = str(path.resolve())
    offsets = char_byte_offsets(text)
    diagnostics: list[dict[str, Any]] = []
    declarations = list(
        re.finditer(r"\b(?:let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*:[^=;]+=[^;]+;", text)
    )
    seen: set[str] = set()
    for declaration in declarations:
        name = declaration.group(1)
        name_start = declaration.start(1)
        name_end = declaration.end(1)
        primary = span(source_id, offsets[name_start], offsets[name_end])
        occurrences = len(re.findall(rf"\b{re.escape(name)}\b", text))
        if occurrences == 1:
            diagnostics.append(
                {
                    "code": "MICA6001",
                    "severity": "warning",
                    "phase": "lint",
                    "message": f"unused local {name}",
                    "primary": primary,
                    "secondary": [],
                    "notes": [],
                    "fixes": [],
                }
            )
        if name in seen:
            diagnostics.append(
                {
                    "code": "MICA6003",
                    "severity": "warning",
                    "phase": "lint",
                    "message": f"local {name} shadows an earlier declaration",
                    "primary": primary,
                    "secondary": [],
                    "notes": ["rename requires symbol-aware edits"],
                    "fixes": [],
                }
            )
        seen.add(name)

    unreachable_re = re.compile(r"\breturn\b[^;]*;(?P<gap>\s*)(?P<statement>(?!\})[^}\n][^;]*;)")
    for match in unreachable_re.finditer(text):
        start_char = match.start("statement")
        end_char = match.end("statement")
        diagnostics.append(
            {
                "code": "MICA6002",
                "severity": "warning",
                "phase": "lint",
                "message": "unreachable statement",
                "primary": span(source_id, offsets[start_char], offsets[end_char]),
                "secondary": [],
                "notes": ["effectful unreachable code has no automatic fix"],
                "fixes": [],
            }
        )

    if mutant == "unsafe-lint-fix":
        unsafe = next(
            (item for item in diagnostics if item["code"] in {"MICA6002", "MICA6003"}),
            None,
        )
        if unsafe is None:
            unsafe = {
                "code": "MICA6002",
                "severity": "warning",
                "phase": "lint",
                "message": "mutant unsafe fix",
                "primary": span(source_id, 0, 0),
                "secondary": [],
                "notes": [],
                "fixes": [],
            }
            diagnostics.append(unsafe)
        unsafe["fixes"] = [
            {
                "title": "delete the whole program",
                "applicability": "machine-applicable",
                "edits": [
                    {
                        "source_id": source_id,
                        "start": 0,
                        "end": len(text.encode("utf-8")),
                        "replacement": "",
                    }
                ],
            }
        ]

    diagnostics.sort(
        key=lambda item: (
            item["primary"]["start"],
            item["primary"]["end"],
            item["code"],
        )
    )
    return diagnostics


def command_lint(args: argparse.Namespace) -> int:
    path = args.file.resolve()
    data = path.read_bytes()
    text = data.decode("utf-8")
    diagnostics = lint_diagnostics(path, text, args.mutant)
    payload = envelope("lint", path, data, diagnostics)
    payload["fixed_source"] = text if args.fix else None
    apply_nan(payload, args.mutant)
    return emit_json(payload, 0)


def add_file_command(subparsers: Any, name: str) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name)
    parser.add_argument("file", type=Path)
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mutant",
        choices=sorted(MUTANTS),
        default=os.environ.get("MICA_ADAPTER_MUTANT", "none"),
        help="emit one intentionally broken behavior for runner regression tests",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("lex", "parse", "check"):
        command = add_file_command(subparsers, name)
        command.add_argument("--json", action="store_true")
    run = add_file_command(subparsers, "run")
    run.add_argument("--engine", choices=("interpreter", "vm"), default="interpreter")
    run.add_argument("--json", action="store_true")
    verify = add_file_command(subparsers, "verify-bytecode")
    verify.add_argument("--json", action="store_true")
    disassemble = add_file_command(subparsers, "disassemble")
    disassemble.add_argument("--json", action="store_true")
    add_file_command(subparsers, "format")
    lint = add_file_command(subparsers, "lint")
    lint.add_argument("--json", action="store_true")
    lint.add_argument("--fix", action="store_true")
    args = parser.parse_args(argv)
    if args.mutant not in MUTANTS:
        parser.error(f"unknown MICA_ADAPTER_MUTANT value: {args.mutant}")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mutant == "timeout":
        time.sleep(30)
    if args.mutant == "output-flood":
        sys.stdout.write("x" * (2 * 1024 * 1024))
        sys.stdout.flush()
        return 0

    manifest = read_manifest()
    if args.command == "lex":
        return command_lex(args, manifest)
    if args.command in {"parse", "check"}:
        return command_parse_or_check(args.command, args, manifest)
    if args.command == "run":
        return command_run(args, manifest)
    if args.command == "verify-bytecode":
        return command_verify_bytecode(args, manifest)
    if args.command == "disassemble":
        return command_disassemble(args, manifest)
    if args.command == "format":
        return command_format(args, manifest)
    if args.command == "lint":
        return command_lint(args)
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
