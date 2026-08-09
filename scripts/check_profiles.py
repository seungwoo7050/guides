#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_EXERCISES = [
    '01-service-classification',
    '02-iaas-failure-domains',
    '03-managed-service-contract',
    '04-faas-event-lifecycle',
    '05-saas-tenant-isolation',
    '06-cost-and-exit',
]


def run(command: list[str], *, expect_success: bool, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    if expect_success and completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise SystemExit(f'expected success: {command}')
    if not expect_success and completed.returncode == 0:
        sys.stderr.write(completed.stdout)
        raise SystemExit(f'expected failure: {command}')


def main() -> int:
    checker = str(ROOT / 'scripts' / 'check_artifact.py')
    for exercise in DOCUMENT_EXERCISES:
        base = ROOT / 'exercises' / exercise
        contract = str(base / 'contract.json')
        run([sys.executable, checker, str(base / 'reference'), contract], expect_success=True)
        run([sys.executable, checker, str(base / 'template'), contract], expect_success=False)

    capstone = ROOT / 'projects' / 'multitenant-document-processing-saas'
    run([sys.executable, checker, str(capstone / 'reference'), str(capstone / 'contract.json')], expect_success=True)
    run([sys.executable, checker, str(capstone / 'template'), str(capstone / 'contract.json')], expect_success=False)

    tests = ROOT / 'exercises' / '07-local-cloud-model' / 'tests'
    for profile, success in [('reference', True), ('skeleton', False)]:
        env = os.environ.copy()
        env['CLOUD_MODEL_PROFILE'] = profile
        run([sys.executable, '-m', 'unittest', 'discover', '-s', str(tests), '-v'], expect_success=success, env=env)

    print('profiles OK: references pass, templates and vulnerable model are rejected')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
