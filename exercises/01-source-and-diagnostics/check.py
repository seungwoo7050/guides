#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def utf8_boundaries(text: str) -> list[int]:
    result = [0]
    total = 0
    for character in text:
        total += len(character.encode("utf-8"))
        result.append(total)
    return result


def line_starts(text: str) -> list[int]:
    data = text.encode("utf-8")
    result = [0]
    cursor = 0
    while cursor < len(data):
        if data[cursor : cursor + 2] == b"\r\n":
            cursor += 2
            result.append(cursor)
        elif data[cursor : cursor + 1] == b"\n":
            cursor += 1
            result.append(cursor)
        else:
            cursor += 1
    return result


def main() -> int:
    fixtures = json.loads((HERE / "fixtures/source-cases.json").read_text(encoding="utf-8"))
    assert fixtures["schema_version"] == 1
    by_name: dict[str, dict[str, object]] = {}
    for case in fixtures["cases"]:
        text = case["text"]
        assert len(text.encode("utf-8")) == case["byte_length"]
        assert utf8_boundaries(text) == case["codepoint_boundaries"]
        assert line_starts(text) == case["line_starts"]
        by_name[case["name"]] = case

    reference = json.loads((HERE / "reference/unicode-diagnostic.json").read_text(encoding="utf-8"))
    source = reference["source"]
    diagnostic = reference["diagnostic"]
    case = by_name[source["id"]]
    boundaries = set(case["codepoint_boundaries"])
    primary = diagnostic["primary"]
    assert primary["source_id"] == source["id"]
    assert primary["start"] in boundaries and primary["end"] in boundaries
    assert diagnostic["code"].startswith("MICA1") and diagnostic["phase"] == "lex"

    # A character-index implementation would start inside the four-byte emoji.
    known_bad_start = 1
    assert known_bad_start not in boundaries

    example = subprocess.run(
        [sys.executable, str(ROOT / "examples/diagnostic-renderer/render.py"), "--self-test"],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert example.returncode == 0 and "PASS" in example.stdout
    print("PASS lab01 UTF-8 boundaries CRLF line map diagnostic source identity known-bad")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
