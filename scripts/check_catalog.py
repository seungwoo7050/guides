#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
KINDS = {'common-foundation', 'language-entry', 'field-entry', 'specialization'}
BRANCH_FIELDS = {
    'id', 'title', 'kind', 'summary', 'requires', 'recommends', 'connects',
    'continues_to', 'owns', 'excludes', 'exit_capabilities', 'url', 'status'
}
TRACK_FIELDS = {
    'id', 'title', 'summary', 'common', 'required', 'required_any',
    'recommended', 'advanced', 'exit_capabilities'
}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def check_nonempty_strings(value: object, field: str, owner: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        fail(f'{owner}.{field}: non-empty list required', errors)
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            fail(f'{owner}.{field}[{index}]: non-empty string required', errors)


def detect_cycles(branch_by_id: dict[str, dict], errors: list[str]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            start = stack.index(node)
            fail('requires cycle: ' + ' -> '.join(stack[start:] + [node]), errors)
            return
        visiting.add(node)
        stack.append(node)
        requires = branch_by_id[node].get('requires')
        if isinstance(requires, list):
            for dep in requires:
                # Unknown references are reported by the field validator. Skipping
                # them here keeps cycle detection from hiding that useful error
                # behind an implementation-level KeyError.
                if dep in branch_by_id:
                    visit(dep)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for branch_id in branch_by_id:
        visit(branch_id)


def main() -> int:
    errors: list[str] = []
    branches_doc = json.loads((ROOT / 'catalog' / 'branches.json').read_text(encoding='utf-8'))
    tracks_doc = json.loads((ROOT / 'catalog' / 'tracks.json').read_text(encoding='utf-8'))

    if branches_doc.get('schema_version') != 1:
        fail('branches schema_version must be 1', errors)
    if tracks_doc.get('schema_version') != 1:
        fail('tracks schema_version must be 1', errors)

    branches = branches_doc.get('branches')
    tracks = tracks_doc.get('tracks')
    if not isinstance(branches, list) or not branches:
        fail('branches must be a non-empty list', errors)
        branches = []
    if not isinstance(tracks, list) or not tracks:
        fail('tracks must be a non-empty list', errors)
        tracks = []

    branch_ids = [b.get('id') for b in branches if isinstance(b, dict)]
    for branch_id, count in Counter(branch_ids).items():
        if count > 1:
            fail(f'duplicate branch id: {branch_id}', errors)
    branch_by_id = {b['id']: b for b in branches if isinstance(b, dict) and isinstance(b.get('id'), str)}

    for b in branches:
        if not isinstance(b, dict):
            fail('branch entry must be an object', errors)
            continue
        owner = f"branch[{b.get('id', '?')}]"
        missing = BRANCH_FIELDS - set(b)
        extra = set(b) - BRANCH_FIELDS
        if missing:
            fail(f'{owner}: missing fields {sorted(missing)}', errors)
        if extra:
            fail(f'{owner}: unexpected fields {sorted(extra)}', errors)
        branch_id = b.get('id')
        if not isinstance(branch_id, str) or not ID_RE.fullmatch(branch_id):
            fail(f'{owner}.id: invalid branch id', errors)
            continue
        if b.get('kind') not in KINDS:
            fail(f'{owner}.kind: invalid kind {b.get("kind")!r}', errors)
        if b.get('status') != 'stable':
            fail(f'{owner}.status: final catalog requires stable', errors)
        expected_url = f'https://github.com/seungwoo7050/guides/tree/{branch_id}'
        if b.get('url') != expected_url:
            fail(f'{owner}.url: expected {expected_url}', errors)
        for field in ('title', 'summary'):
            if not isinstance(b.get(field), str) or not b[field].strip():
                fail(f'{owner}.{field}: non-empty string required', errors)
        for field in ('owns', 'excludes', 'exit_capabilities'):
            check_nonempty_strings(b.get(field), field, owner, errors)
        for field in ('requires', 'recommends', 'connects', 'continues_to'):
            refs = b.get(field)
            if not isinstance(refs, list):
                fail(f'{owner}.{field}: list required', errors)
                continue
            if len(refs) != len(set(refs)):
                fail(f'{owner}.{field}: duplicate references', errors)
            for ref in refs:
                if ref not in branch_by_id:
                    fail(f'{owner}.{field}: unknown branch {ref}', errors)
                if ref == branch_id:
                    fail(f'{owner}.{field}: self reference', errors)

    if branch_by_id:
        detect_cycles(branch_by_id, errors)

    track_ids = [t.get('id') for t in tracks if isinstance(t, dict)]
    for track_id, count in Counter(track_ids).items():
        if count > 1:
            fail(f'duplicate track id: {track_id}', errors)

    used_branches: set[str] = set()
    for t in tracks:
        if not isinstance(t, dict):
            fail('track entry must be an object', errors)
            continue
        owner = f"track[{t.get('id', '?')}]"
        missing = TRACK_FIELDS - set(t)
        extra = set(t) - TRACK_FIELDS
        if missing:
            fail(f'{owner}: missing fields {sorted(missing)}', errors)
        if extra:
            fail(f'{owner}: unexpected fields {sorted(extra)}', errors)
        track_id = t.get('id')
        if not isinstance(track_id, str) or not ID_RE.fullmatch(track_id):
            fail(f'{owner}.id: invalid track id', errors)
        for field in ('title', 'summary'):
            if not isinstance(t.get(field), str) or not t[field].strip():
                fail(f'{owner}.{field}: non-empty string required', errors)
        for field in ('common', 'required', 'recommended', 'advanced'):
            refs = t.get(field)
            if not isinstance(refs, list):
                fail(f'{owner}.{field}: list required', errors)
                continue
            if len(refs) != len(set(refs)):
                fail(f'{owner}.{field}: duplicate references', errors)
            for ref in refs:
                if ref not in branch_by_id:
                    fail(f'{owner}.{field}: unknown branch {ref}', errors)
                else:
                    used_branches.add(ref)
        groups = t.get('required_any')
        if not isinstance(groups, list):
            fail(f'{owner}.required_any: list required', errors)
        else:
            for index, group in enumerate(groups):
                if not isinstance(group, list) or not group:
                    fail(f'{owner}.required_any[{index}]: non-empty list required', errors)
                    continue
                if len(group) != len(set(group)):
                    fail(f'{owner}.required_any[{index}]: duplicate references', errors)
                for ref in group:
                    if ref not in branch_by_id:
                        fail(f'{owner}.required_any[{index}]: unknown branch {ref}', errors)
                    else:
                        used_branches.add(ref)
        check_nonempty_strings(t.get('exit_capabilities'), 'exit_capabilities', owner, errors)

    unused = sorted(set(branch_by_id) - used_branches)
    if unused:
        fail(f'branches absent from every track: {unused}', errors)

    if errors:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print(f'catalog OK: {len(branches)} branches, {len(tracks)} tracks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
