"""완성한 프로토콜 모듈을 연결할 명령줄 인터페이스입니다."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m protocol_inspector",
        description="프로토콜 실습 모듈을 명령줄에서 실행합니다.",
    )
    parser.add_subparsers(dest="command", required=True, title="하위 명령")
    return parser


def main() -> int:
    build_parser().parse_args()
    raise NotImplementedError("완성 예제의 출력 계약을 참고해 하위 명령을 연결하세요")
