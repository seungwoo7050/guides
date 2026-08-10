from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .diagnostic import Diagnostic
from .source import SourceText, Span


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mica")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("lex", "parse", "check", "lint"):
        command = sub.add_parser(name)
        command.add_argument("file", type=Path)
        command.add_argument("--json", action="store_true", dest="as_json")
    run_command = sub.add_parser("run")
    run_command.add_argument("file", type=Path)
    run_command.add_argument("--engine", choices=("interpreter", "vm"), default="interpreter")
    run_command.add_argument("--json", action="store_true", dest="as_json")
    for name in ("verify-bytecode", "disassemble"):
        command = sub.add_parser(name)
        command.add_argument("file", type=Path)
        command.add_argument("--json", action="store_true", dest="as_json")
    format_command = sub.add_parser("format")
    format_command.add_argument("file", type=Path)
    sub.add_parser("serve")
    return parser


def _unimplemented(command: str, source: SourceText | None, as_json: bool) -> int:
    source_id = source.source_id if source else "<command>"
    length = source.byte_length if source else 0
    diagnostic = Diagnostic(
        code="MICA0000",
        severity="error",
        phase="internal",
        message=f"{command} is not implemented in the capstone skeleton",
        primary=Span(source_id, 0, 0),
    )
    if as_json:
        payload = {
            "schema_version": 1,
            "command": command,
            "source": {"id": source_id, "byte_length": length},
            "diagnostics": [diagnostic.to_json()],
        }
        if command == "run":
            payload.update({"stdout": "", "return_value": None})
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"error[MICA0000]: {diagnostic.message}", file=sys.stderr)
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source: SourceText | None = None
    if hasattr(args, "file"):
        try:
            source = SourceText.read(args.file)
        except (OSError, UnicodeError) as exc:
            print(f"mica: cannot read source: {exc}", file=sys.stderr)
            return 2
    return _unimplemented(args.command, source, bool(getattr(args, "as_json", False)))
