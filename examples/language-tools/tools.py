#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from typing import Any

TOKEN = re.compile(
    r"(?P<space>\s+)|(?P<comment>//[^\n]*)|(?P<string>\"(?:\\.|[^\"\\])*\")|"
    r"(?P<operator>->|==|!=|<=|>=|&&|\|\||[+\-*/%=<>!])|"
    r"(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)|(?P<integer>[0-9]+)|(?P<punct>[{}();,:])"
)


def tokenize(source: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    position = 0
    while position < len(source):
        match = TOKEN.match(source, position)
        if match is None:
            raise ValueError(f"unsupported character at {position}: {source[position]!r}")
        position = match.end()
        if match.lastgroup != "space":
            assert match.lastgroup is not None
            tokens.append((match.lastgroup, match.group()))
    return tokens


def syntax_projection(source: str) -> list[str]:
    return [text for kind, text in tokenize(source) if kind != "comment"]


def format_mica(source: str) -> str:
    tokens = tokenize(source)
    lines: list[str] = []
    current = ""
    indent = 0

    def emit() -> None:
        nonlocal current
        if current.strip():
            lines.append("    " * indent + current.strip())
        current = ""

    for kind, token in tokens:
        if kind == "comment":
            if current and not current.endswith(" "):
                current += " "
            current += token
            emit()
        elif token == "{":
            current = current.rstrip() + " {"
            emit()
            indent += 1
        elif token == "}":
            emit()
            indent -= 1
            if indent < 0:
                raise ValueError("unmatched closing brace")
            current = "}"
            emit()
        elif token == ";":
            current = current.rstrip() + ";"
            emit()
        elif token == ":":
            current = current.rstrip() + ": "
        elif token == ",":
            current = current.rstrip() + ", "
        elif kind == "operator":
            if token == "!":
                current = current.rstrip() + "!"
            else:
                current = current.rstrip() + f" {token} "
        elif token == "(":
            if current.rstrip().endswith(("if", "while")):
                current = current.rstrip() + " ("
            else:
                current = current.rstrip() + "("
        elif token == ")":
            current = current.rstrip() + ")"
        else:
            if current and not current.endswith((" ", "(", "!")):
                current += " "
            current += token
    emit()
    if indent != 0:
        raise ValueError("unclosed brace")
    return "\n".join(lines) + "\n"


def lint(model: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for symbol in model.get("symbols", []):
        if symbol["kind"] == "local" and symbol["references"] == 0:
            fix = None
            if symbol.get("initializer_pure"):
                fix = {"applicability": "machine-applicable", "replacement": ""}
            diagnostics.append({
                "code": "MICAL001",
                "severity": "warning",
                "phase": "lint",
                "span": symbol["span"],
                "message": f"unused local {symbol['name']}",
                "fix": fix,
            })
        if symbol.get("shadows") is not None:
            diagnostics.append({
                "code": "MICAL003",
                "severity": "warning",
                "phase": "lint",
                "span": symbol["span"],
                "message": f"{symbol['name']} shadows {symbol['shadows']}",
                "fix": None,
            })
    for statement in model.get("unreachable", []):
        diagnostics.append({
            "code": "MICAL002",
            "severity": "warning",
            "phase": "lint",
            "span": statement["span"],
            "message": "unreachable statement",
            "fix": None if statement.get("effectful", True) else {"applicability": "maybe-incorrect", "replacement": ""},
        })
    diagnostics.sort(key=lambda item: (item["span"]["start"], item["code"]))
    return diagnostics


def utf16_position(text: str, offset: int) -> dict[str, int]:
    if not 0 <= offset <= len(text):
        raise ValueError("offset outside document")
    prefix = text[:offset]
    line = prefix.count("\n")
    current_line = prefix.rsplit("\n", 1)[-1]
    character = len(current_line.encode("utf-16-le")) // 2
    return {"line": line, "character": character}


class DocumentStore:
    def __init__(self) -> None:
        self._documents: dict[str, tuple[int, str]] = {}

    def open(self, uri: str, version: int, text: str) -> None:
        self._documents[uri] = (version, text)

    def change(self, uri: str, version: int, text: str) -> None:
        current, _ = self._documents[uri]
        if version <= current:
            raise ValueError("document version must increase")
        self._documents[uri] = (version, text)

    def publish(self, uri: str, version: int, diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
        current, _ = self._documents[uri]
        if version != current:
            return {"published": False, "reason": "stale-version", "version": version}
        return {"published": True, "diagnostics": diagnostics, "version": version}


def self_test() -> None:
    source = "fn main()->Int{// keep\nlet x:Int=1+2;return x;}"
    expected = "fn main() -> Int {\n    // keep\n    let x: Int = 1 + 2;\n    return x;\n}\n"
    formatted = format_mica(source)
    assert formatted == expected
    assert format_mica(formatted) == formatted
    assert syntax_projection(source) == syntax_projection(formatted)
    assert "// keep" in formatted
    model = {
        "symbols": [{"kind": "local", "name": "x", "references": 0, "initializer_pure": False, "shadows": None, "span": {"start": 20, "end": 21}}],
        "unreachable": [{"effectful": True, "span": {"start": 30, "end": 40}}],
    }
    diagnostics = lint(model)
    assert [item["code"] for item in diagnostics] == ["MICAL001", "MICAL002"]
    assert all(item["fix"] is None for item in diagnostics)
    assert utf16_position("a🙂b\n", 2) == {"line": 0, "character": 3}
    store = DocumentStore()
    store.open("file:///demo.mica", 1, "a🙂b")
    store.change("file:///demo.mica", 2, "a🙂c")
    assert store.publish("file:///demo.mica", 1, [])["reason"] == "stale-version"
    assert store.publish("file:///demo.mica", 2, [])["published"] is True
    print("PASS language tools comment idempotence lint unsafe-fix Unicode stale-version")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(json.dumps({"position": utf16_position("a🙂b", 2)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
