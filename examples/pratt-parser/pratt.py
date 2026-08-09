#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Any

TOKEN = re.compile(r"\s*(?:(\d+)|(.))")


@dataclass(frozen=True)
class Tok:
    kind: str
    text: str
    index: int


def lex(text: str) -> list[Tok]:
    tokens: list[Tok] = []
    pos = 0
    while pos < len(text):
        match = TOKEN.match(text, pos)
        if match is None:
            raise ValueError(f"cannot tokenize at {pos}")
        if match.group(1) is not None:
            tokens.append(Tok("INT", match.group(1), pos))
        else:
            char = match.group(2)
            if char not in "+-*/()":
                raise ValueError(f"unexpected character {char!r} at {match.start(2)}")
            tokens.append(Tok(char, char, match.start(2)))
        pos = match.end()
    tokens.append(Tok("EOF", "", len(text)))
    return tokens


class Parser:
    INFIX = {
        "+": (10, 11),
        "-": (10, 11),
        "*": (20, 21),
        "/": (20, 21),
    }

    def __init__(self, tokens: list[Tok]) -> None:
        self.tokens = tokens
        self.cursor = 0

    @property
    def current(self) -> Tok:
        return self.tokens[self.cursor]

    def bump(self) -> Tok:
        token = self.current
        self.cursor += 1
        return token

    def parse(self) -> dict[str, Any]:
        expression = self.parse_expr(0)
        if self.current.kind != "EOF":
            raise ValueError(f"trailing token {self.current.text!r} at {self.current.index}")
        return expression

    def parse_expr(self, min_bp: int) -> dict[str, Any]:
        before = self.cursor
        token = self.bump()
        if token.kind == "INT":
            left: dict[str, Any] = {"kind": "Int", "value": int(token.text)}
        elif token.kind == "-":
            left = {"kind": "Neg", "value": self.parse_expr(30)}
        elif token.kind == "(":
            left = self.parse_expr(0)
            if self.current.kind != ")":
                raise ValueError(f"expected ')' at {self.current.index}")
            self.bump()
        else:
            raise ValueError(f"expected expression at {token.index}, got {token.kind}")

        if self.cursor <= before:
            raise AssertionError("parser made no progress")

        while True:
            binding = self.INFIX.get(self.current.kind)
            if binding is None:
                break
            left_bp, right_bp = binding
            if left_bp < min_bp:
                break
            op = self.bump().kind
            right = self.parse_expr(right_bp)
            left = {"kind": "Binary", "op": op, "left": left, "right": right}
        return left


def parse(text: str) -> dict[str, Any]:
    return Parser(lex(text)).parse()


def self_test() -> None:
    assert parse("1 + 2 * 3") == {
        "kind": "Binary", "op": "+", "left": {"kind": "Int", "value": 1},
        "right": {"kind": "Binary", "op": "*", "left": {"kind": "Int", "value": 2}, "right": {"kind": "Int", "value": 3}},
    }
    tree = parse("8 - 3 - 2")
    assert tree["left"]["op"] == "-" and tree["right"] == {"kind": "Int", "value": 2}
    assert parse("-(1 + 2)")["kind"] == "Neg"
    for bad in ("1 +", "(1 + 2", "1 @ 2"):
        try:
            parse(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid expression accepted: {bad}")
    print("PASS Pratt parser")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("expression", nargs="?", default="1 + 2 * 3")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(json.dumps(parse(args.expression), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
