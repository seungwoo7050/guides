"""계층별 경로 진단 명령행 인터페이스를 제공합니다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .diagnose import diagnose, render_text
from .model import TraceFormatError, load_trace


# [Implementation 3] trace path와 출력 형식의 명령행 계약을 domain logic 밖에 둡니다.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="path-diagnosis",
        description="계층별 네트워크 증거에서 첫 실패와 다음 검사를 결정합니다.",
    )
    parser.add_argument("trace", type=Path, help="진단할 JSON trace 파일")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
        help="출력 형식",
    )
    return parser


# [Implementation 3-1] 입력 오류, 출력 채널과 건강·실패·형식 오류 exit status를 조립합니다.
def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        trace = load_trace(args.trace)
        result = diagnose(trace)
    except TraceFormatError as error:
        print(f"입력 오류: {error}", file=sys.stderr)
        return 2

    if args.output_format == "json":
        print(json.dumps(result.to_mapping(), ensure_ascii=False, sort_keys=True))
    else:
        print(render_text(result))
    return 0 if result.healthy else 1
