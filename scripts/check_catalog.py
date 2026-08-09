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
    'id', 'title', 'group', 'summary', 'common', 'required', 'required_any',
    'recommended', 'advanced', 'linear_paths', 'exit_capabilities'
}
TRACK_GROUPS = {'common', 'web', 'infra-security', 'mobile', 'ai-data', 'systems', 'game'}
PATH_FIELDS = {'id', 'title', 'branches'}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def check_nonempty_strings(value: object, field: str, owner: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        fail(f'{owner}.{field}: non-empty list required', errors)
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            fail(f'{owner}.{field}[{index}]: non-empty string required', errors)


def load_document(path: Path, label: str, errors: list[str]) -> dict | None:
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f'{label}: cannot read valid JSON ({exc})', errors)
        return None
    if not isinstance(document, dict):
        fail(f'{label}: top-level object required', errors)
        return None
    return document


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
                if isinstance(dep, str) and dep in branch_by_id:
                    visit(dep)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for branch_id in branch_by_id:
        visit(branch_id)


def main() -> int:
    errors: list[str] = []
    branches_doc = load_document(
        ROOT / 'catalog' / 'branches.json', 'branches catalog', errors
    )
    tracks_doc = load_document(
        ROOT / 'catalog' / 'tracks.json', 'tracks catalog', errors
    )
    if branches_doc is None or tracks_doc is None:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1

    if branches_doc.get('schema_version') != 1:
        fail('branches schema_version must be 1', errors)
    if tracks_doc.get('schema_version') != 2:
        fail('tracks schema_version must be 2', errors)

    branches = branches_doc.get('branches')
    tracks = tracks_doc.get('tracks')
    if not isinstance(branches, list) or not branches:
        fail('branches must be a non-empty list', errors)
        branches = []
    if not isinstance(tracks, list) or not tracks:
        fail('tracks must be a non-empty list', errors)
        tracks = []

    branch_ids = [
        b.get('id') for b in branches
        if isinstance(b, dict) and isinstance(b.get('id'), str)
    ]
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
            fail(f'{owner}.status: target-state catalog requires stable', errors)
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
            valid_refs: list[str] = []
            for index, ref in enumerate(refs):
                if not isinstance(ref, str):
                    fail(f'{owner}.{field}[{index}]: branch id string required', errors)
                else:
                    valid_refs.append(ref)
            if len(valid_refs) != len(set(valid_refs)):
                fail(f'{owner}.{field}: duplicate references', errors)
            for ref in valid_refs:
                if ref not in branch_by_id:
                    fail(f'{owner}.{field}: unknown branch {ref}', errors)
                if ref == branch_id:
                    fail(f'{owner}.{field}: self reference', errors)

    if branch_by_id:
        detect_cycles(branch_by_id, errors)

    track_ids = [
        t.get('id') for t in tracks
        if isinstance(t, dict) and isinstance(t.get('id'), str)
    ]
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
        if t.get('group') not in TRACK_GROUPS:
            fail(f'{owner}.group: invalid group {t.get("group")!r}', errors)
        track_refs: dict[str, list[str]] = {}
        for field in ('common', 'required', 'recommended', 'advanced'):
            refs = t.get(field)
            if not isinstance(refs, list):
                fail(f'{owner}.{field}: list required', errors)
                track_refs[field] = []
                continue
            valid_refs: list[str] = []
            for index, ref in enumerate(refs):
                if not isinstance(ref, str):
                    fail(f'{owner}.{field}[{index}]: branch id string required', errors)
                else:
                    valid_refs.append(ref)
            track_refs[field] = valid_refs
            if len(valid_refs) != len(set(valid_refs)):
                fail(f'{owner}.{field}: duplicate references', errors)
            for ref in valid_refs:
                if ref not in branch_by_id:
                    fail(f'{owner}.{field}: unknown branch {ref}', errors)
                else:
                    used_branches.add(ref)
        groups = t.get('required_any')
        valid_groups: list[list[str]] = []
        if not isinstance(groups, list):
            fail(f'{owner}.required_any: list required', errors)
        else:
            for index, group in enumerate(groups):
                if not isinstance(group, list) or not group:
                    fail(f'{owner}.required_any[{index}]: non-empty list required', errors)
                    continue
                valid_group: list[str] = []
                for ref_index, ref in enumerate(group):
                    if not isinstance(ref, str):
                        fail(
                            f'{owner}.required_any[{index}][{ref_index}]: '
                            'branch id string required',
                            errors,
                        )
                    else:
                        valid_group.append(ref)
                valid_groups.append(valid_group)
                if len(valid_group) != len(set(valid_group)):
                    fail(f'{owner}.required_any[{index}]: duplicate references', errors)
                for ref in valid_group:
                    if ref not in branch_by_id:
                        fail(f'{owner}.required_any[{index}]: unknown branch {ref}', errors)
                    else:
                        used_branches.add(ref)
        paths = t.get('linear_paths')
        if not isinstance(paths, list) or not paths:
            fail(f'{owner}.linear_paths: non-empty list required', errors)
        else:
            path_ids: list[str] = []
            for index, path in enumerate(paths):
                path_owner = f'{owner}.linear_paths[{index}]'
                if not isinstance(path, dict):
                    fail(f'{path_owner}: object required', errors)
                    continue
                missing_path = PATH_FIELDS - set(path)
                extra_path = set(path) - PATH_FIELDS
                if missing_path:
                    fail(f'{path_owner}: missing fields {sorted(missing_path)}', errors)
                if extra_path:
                    fail(f'{path_owner}: unexpected fields {sorted(extra_path)}', errors)
                path_id = path.get('id')
                if not isinstance(path_id, str) or not ID_RE.fullmatch(path_id):
                    fail(f'{path_owner}.id: invalid path id', errors)
                else:
                    path_ids.append(path_id)
                if not isinstance(path.get('title'), str) or not path['title'].strip():
                    fail(f'{path_owner}.title: non-empty string required', errors)
                refs = path.get('branches')
                if not isinstance(refs, list) or not refs:
                    fail(f'{path_owner}.branches: non-empty list required', errors)
                    continue
                valid_refs: list[str] = []
                for ref_index, ref in enumerate(refs):
                    if not isinstance(ref, str):
                        fail(
                            f'{path_owner}.branches[{ref_index}]: '
                            'branch id string required',
                            errors,
                        )
                    else:
                        valid_refs.append(ref)
                if len(valid_refs) != len(set(valid_refs)):
                    fail(f'{path_owner}.branches: duplicate references', errors)
                for ref in valid_refs:
                    if ref not in branch_by_id:
                        fail(f'{path_owner}.branches: unknown branch {ref}', errors)
                    else:
                        used_branches.add(ref)
                positions = {ref: position for position, ref in enumerate(valid_refs)}
                required_in_path = set(track_refs['common']) | set(track_refs['required'])
                missing_from_path = sorted(required_in_path - set(positions))
                if missing_from_path:
                    fail(
                        f'{path_owner}.branches: common/required branches missing '
                        f'{missing_from_path}',
                        errors,
                    )
                for group_index, group in enumerate(valid_groups):
                    if group and not (set(group) & set(positions)):
                        fail(
                            f'{path_owner}.branches: required_any[{group_index}] '
                            'has no represented choice',
                            errors,
                        )
                advanced_in_path = sorted(set(track_refs['advanced']) & set(positions))
                if advanced_in_path:
                    fail(
                        f'{path_owner}.branches: advanced branches belong after '
                        f'track completion {advanced_in_path}',
                        errors,
                    )
                for ref in valid_refs:
                    branch = branch_by_id.get(ref)
                    if not branch:
                        continue
                    dependencies = branch.get('requires')
                    if not isinstance(dependencies, list):
                        continue
                    for dependency in dependencies:
                        if not isinstance(dependency, str):
                            continue
                        if dependency not in positions:
                            fail(
                                f'{path_owner}.branches: {ref} requires missing {dependency}',
                                errors,
                            )
                        elif positions[dependency] >= positions[ref]:
                            fail(
                                f'{path_owner}.branches: {dependency} must precede {ref}',
                                errors,
                            )
            for path_id, count in Counter(path_ids).items():
                if count > 1:
                    fail(f'{owner}.linear_paths: duplicate path id {path_id}', errors)

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
