from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .capstone import FixtureCapstone
from .runtime import InjectedCrash


GUIDE_ROOT = Path(__file__).resolve().parents[4]


def _json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="coding-agent")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run a deterministic local fixture")
    run.add_argument("--task-fixture", required=True)
    run.add_argument("--session", type=Path, required=True)
    run.add_argument("--crash-after-effect", choices=("apply_patch", "run_check"))
    for name in ("inspect", "resume", "status", "diff", "cancel"):
        item = commands.add_parser(name)
        item.add_argument("--session", type=Path, required=True)
    export = commands.add_parser("export")
    export.add_argument("--session", type=Path, required=True)
    export.add_argument("--destination", type=Path, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    capstone = FixtureCapstone(GUIDE_ROOT)
    try:
        if args.command == "run":
            result = capstone.run(
                args.session,
                task_id=args.task_fixture,
                crash_after_effect=args.crash_after_effect,
            )
            _json({"session_id": result.session_id, "status": result.state, "verification": result.verification})
            return 0 if result.state == "SUCCEEDED" else 1
        if args.command == "resume":
            result = capstone.run(args.session, resume=True)
            _json({"session_id": result.session_id, "status": result.state, "verification": result.verification})
            return 0 if result.state == "SUCCEEDED" else 1
        if args.command == "status":
            _json(capstone.status(args.session))
            return 0
        if args.command == "inspect":
            status = dict(capstone.status(args.session))
            manifest = json.loads((args.session / "session.json").read_text(encoding="utf-8"))
            events = Path(manifest["state_dir"]) / "events.jsonl"
            status["events"] = sum(1 for _ in events.open(encoding="utf-8"))
            status["evaluation"] = json.loads(
                (args.session / "evaluation-report.json").read_text(encoding="utf-8")
            ) if (args.session / "evaluation-report.json").exists() else None
            _json(status)
            return 0
        if args.command == "diff":
            print(capstone.diff(args.session), end="")
            return 0
        if args.command == "cancel":
            _json(capstone.cancel(args.session))
            return 0
        if args.command == "export":
            _json({"destination": str(capstone.export(args.session, args.destination))})
            return 0
    except InjectedCrash as exc:
        print(f"injected crash: {exc}", file=sys.stderr)
        return 75
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"coding-agent error: {exc}", file=sys.stderr)
        return 2
    return 2
