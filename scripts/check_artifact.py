#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def check(root: Path, contract_path: Path) -> list[str]:
    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    errors: list[str] = []
    required_files = contract.get('required_files', [])
    for relative in required_files:
        path = root / relative
        if not path.is_file():
            errors.append(f'missing file: {relative}')
    forbidden = contract.get('forbidden_tokens', ['TODO', '<작성>', 'TBD'])
    for relative in required_files:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        for token in forbidden:
            if token in text:
                errors.append(f'{relative}: unresolved token {token!r}')
        minimum = int(contract.get('minimum_bytes', {}).get(relative, 0))
        if len(text.encode('utf-8')) < minimum:
            errors.append(f'{relative}: {len(text.encode("utf-8"))} bytes < minimum {minimum}')
        for heading in contract.get('required_headings', {}).get(relative, []):
            if heading not in text:
                errors.append(f'{relative}: missing heading {heading!r}')
        for phrase in contract.get('required_phrases', {}).get(relative, []):
            if phrase not in text:
                errors.append(f'{relative}: missing required phrase {phrase!r}')
    for relative, required_keys in contract.get('json_required_keys', {}).items():
        path = root / relative
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            errors.append(f'{relative}: invalid JSON: {exc}')
            continue
        if not isinstance(data, dict):
            errors.append(f'{relative}: top-level JSON object required')
            continue
        for key in required_keys:
            if key not in data:
                errors.append(f'{relative}: missing JSON key {key!r}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('contract', type=Path)
    args = parser.parse_args()
    errors = check(args.root.resolve(), args.contract.resolve())
    if errors:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print(f'artifact OK: {args.root}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
