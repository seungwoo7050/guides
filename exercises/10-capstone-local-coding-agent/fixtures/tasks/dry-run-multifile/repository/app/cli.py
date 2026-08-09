from __future__ import annotations

import argparse

from .service import apply_setting


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="settings")
    parser.add_argument("name")
    parser.add_argument("value")
    return parser


def run(argv: list[str], store: dict[str, str]) -> str:
    args = build_parser().parse_args(argv)
    return apply_setting(store, args.name, args.value)


if __name__ == "__main__":
    import sys

    print(run(sys.argv[1:], {}))
