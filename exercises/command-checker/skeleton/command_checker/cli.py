"""1단계에서 패키지 진입점과 CLI 계약을 구현합니다."""

from __future__ import annotations

import argparse
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    raise NotImplementedError("stage 01: ArgumentParser를 구성하십시오.")


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    raise NotImplementedError("stage 01: 명령줄 인자를 검증하십시오.")


def main(argv: Sequence[str] | None = None) -> int:
    raise NotImplementedError("stage 01: CLI 진입점을 구현하십시오.")
