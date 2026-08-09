#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SOURCE))

from model_project.core import attention, read_json  # noqa: E402
from model_project.release import build_release, infer_payload  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Modern-model release candidate protocol")
    subparsers = parser.add_subparsers(dest="command", required=True)
    attention_parser = subparsers.add_parser("attention")
    attention_parser.add_argument("--base", type=Path, required=True)
    attention_parser.add_argument("--tokens", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--fixtures", type=Path, required=True)
    build_parser.add_argument("--output", type=Path, required=True)
    infer_parser = subparsers.add_parser("infer")
    infer_parser.add_argument("--bundle", type=Path, required=True)
    infer_parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "attention":
            tokens = [int(value) for value in args.tokens.split(",")]
            result = attention(tokens, read_json(args.base))
            print(json.dumps(result, sort_keys=True))
        elif args.command == "build":
            build_release(args.fixtures, args.output)
            print(json.dumps({"output": str(args.output), "status": "built"}, sort_keys=True))
        else:
            print(json.dumps(infer_payload(args.bundle, read_json(args.input)), sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
