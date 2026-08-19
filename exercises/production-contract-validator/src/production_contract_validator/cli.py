from __future__ import annotations

import argparse
from pathlib import Path

from .validator import validate_contract


# [Implementation 7] CLI exit and report contract
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a production service contract.")
    parser.add_argument("contract", type=Path)
    args = parser.parse_args(argv)
    errors = validate_contract(args.contract)
    if errors:
        print(f"invalid production contract: {len(errors)} issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"valid production contract: {args.contract}")
    return 0
