#!/usr/bin/env python3
from __future__ import annotations

import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "exercises/08-mica-capstone"
CODE = re.compile(r"^MICA[0-9]{4}$")


def main() -> int:
    failures: list[str] = []
    try:
        manifest: dict[str, Any] = json.loads((CAP / "fixtures/manifest.json").read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR manifest parse: {exc}", file=sys.stderr)
        return 1
    if manifest.get("schema_version") != 1:
        failures.append("manifest schema_version must be 1")

    spec_codes = set(re.findall(r"`(MICA[0-9]{4})`", (CAP / "spec/diagnostics.md").read_text(encoding="utf-8")))
    seen_files: set[str] = set()
    case_count = 0
    for category in ("valid", "invalid", "runtime", "format", "bytecode_invalid"):
        cases = manifest.get(category)
        if not isinstance(cases, list) or not cases:
            failures.append(f"manifest category missing/empty: {category}")
            continue
        for case in cases:
            case_count += 1
            if not isinstance(case, dict) or not isinstance(case.get("file"), str):
                failures.append(f"{category}: invalid case object")
                continue
            filename = case["file"]
            if filename in seen_files:
                failures.append(f"duplicate fixture in manifest: {filename}")
            seen_files.add(filename)
            path = CAP / "fixtures" / filename
            if not path.is_file():
                failures.append(f"fixture missing: {filename}")
            for code in case.get("codes", []):
                if not isinstance(code, str) or not CODE.fullmatch(code):
                    failures.append(f"invalid diagnostic code in {filename}: {code!r}")
                elif code not in spec_codes:
                    failures.append(f"diagnostic code not documented: {code}")
            if category == "format":
                expected = CAP / "fixtures" / case.get("expected", "")
                if not expected.is_file():
                    failures.append(f"format expected file missing: {case.get('expected')}")

    for schema in sorted((CAP / "spec").glob("*.schema.json")):
        try:
            value = json.loads(schema.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append(f"invalid JSON schema {schema.name}: {exc}")
            continue
        if value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            failures.append(f"{schema.name}: unexpected JSON Schema draft")

    grammar = (CAP / "spec/grammar.ebnf").read_text(encoding="utf-8")
    for symbol in ("program", "function_decl", "statement", "expression", "primary"):
        if not re.search(rf"(?m)^{symbol}\s*=", grammar):
            failures.append(f"grammar missing rule: {symbol}")

    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".guide", ".workspaces", "__pycache__"} for part in path.parts):
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"Python syntax error {path.relative_to(ROOT)}: {exc.msg}")

    runner = CAP / "check_submission.py"
    commands = [
        [sys.executable, str(runner), "--self-test"],
        [sys.executable, str(runner), "--workspace", str(CAP / "skeleton"), "--stage", "skeleton"],
    ]
    for command in commands:
        proc = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if proc.returncode != 0:
            failures.append(
                f"capstone command failed: {' '.join(command)}\nstdout={proc.stdout}\nstderr={proc.stderr}"
            )

    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    print(f"PASS capstone cases={case_count} documented_codes={len(spec_codes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
