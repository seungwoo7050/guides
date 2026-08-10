#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load_tools() -> Any:
    path = ROOT / "examples/language-tools/tools.py"
    spec = importlib.util.spec_from_file_location("guide_language_tools", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    tools = load_tools()
    source = (HERE / "fixtures/messy-with-comment.mica").read_text(encoding="utf-8")
    expected = (HERE / "reference/formatted.mica").read_text(encoding="utf-8")
    formatted = tools.format_mica(source)
    assert formatted == expected
    assert tools.format_mica(formatted) == formatted
    assert tools.syntax_projection(source) == tools.syntax_projection(formatted)
    assert "// keep this comment" in formatted

    lint_model = json.loads((HERE / "fixtures/lint-model.json").read_text(encoding="utf-8"))
    lint_reference = json.loads((HERE / "reference/lint.json").read_text(encoding="utf-8"))
    diagnostics = tools.lint(lint_model)
    assert diagnostics == lint_reference["diagnostics"]
    assert [item["code"] for item in diagnostics] == ["MICAL001", "MICAL003", "MICAL002"]
    assert all(item["fix"] is None for item in diagnostics)

    transcript = json.loads((HERE / "reference/lsp-transcript.json").read_text(encoding="utf-8"))
    events = transcript["events"]
    store = tools.DocumentStore()
    store.open(transcript["uri"], events[0]["version"], events[0]["text"])
    assert tools.utf16_position(events[0]["text"], events[1]["codepoint_offset"]) == events[1]["position"]
    store.change(transcript["uri"], events[2]["version"], events[2]["text"])
    stale = store.publish(transcript["uri"], events[3]["version"], [])
    current = store.publish(transcript["uri"], events[4]["version"], [])
    assert stale["published"] is False and stale["reason"] == events[3]["reason"]
    assert current["published"] is True
    print("PASS lab07 exact-format comment idempotence projection lint-order unsafe-fix Unicode stale-LSP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
