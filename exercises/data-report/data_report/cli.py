"""Command-line composition and filesystem boundary."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .aggregation import aggregate
from .loaders import load_records
from .model import DataReportError
from .rendering import render_json, render_text


# [Implementation 6]
# The CLI owns filesystem side effects and maps domain failures to process status.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-report",
        description="Aggregate validated CSV or JSON records by category.",
    )
    parser.add_argument("input", type=Path, help="input .csv or .json file")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
        help="report output format",
    )
    parser.add_argument("--output", type=Path, help="write the report to this file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)

    try:
        report = aggregate(load_records(arguments.input))
        rendered = (
            render_json(report)
            if arguments.output_format == "json"
            else render_text(report)
        )

        if arguments.output is None:
            sys.stdout.write(rendered)
        else:
            arguments.output.write_text(rendered, encoding="utf-8")
    except (DataReportError, OSError) as error:
        print(f"data-report: {error}", file=sys.stderr)
        return 2

    return 0
