"""의도적 오답 구현의 CLI입니다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .diagnose import diagnose, render_text
from .model import TraceFormatError, load_trace


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        result = diagnose(load_trace(args.trace))
    except TraceFormatError as error:
        print(f"입력 오류: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(result.to_mapping(), ensure_ascii=False, sort_keys=True))
    else:
        print(render_text(result))
    return 0
