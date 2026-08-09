#!/usr/bin/env python3
"""Mandatory, dependency-free repository and learning-artifact verification."""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote

from source_fingerprint import UnsafeTreeError, fingerprint, source_records

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK_RE = re.compile(r'!?(?:\[[^\]]*\])\(([^)]+)\)')
HEADING_RE = re.compile(r'^\s{0,3}(#{1,6})\s+(.+?)\s*$')
HTML_ID_RE = re.compile(r'\bid=["\']([^"\']+)["\']')
FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
EXCLUDED_DIRS = frozenset({'.git', '.guide', '.workspace', '__pycache__'})
STAGED_EXERCISES = (
    '01-platform-product',
    '02-platform-contract',
    '03-reconciliation',
    '04-iac-state',
    '05-workload-contract',
    '06-self-service',
    '07-delivery-gitops',
    '08-identity-policy',
    '09-multitenancy',
    '10-platform-slo',
    '11-migration',
    '12-capstone-plan',
)
REQUIRED_IGNORE_PATTERNS = {
    '.guide/', '.workspace/', '__pycache__/', '*.pyc', '.DS_Store',
    '.env', '.env.*', '.venv/', '.pytest_cache/', '*.log', '*.tmp',
    '*.tfstate', '*.tfstate.*', '*.tfplan', '*.plan', '.terraform/', '.tofu/',
    '*.bin', '*.tfvars', '*.tfvars.json', 'kubeconfig*', '*.kubeconfig',
    '*.pem', '*.key', '*.p12', '*.pfx', 'id_rsa*', 'id_ed25519*', 'reports/',
}


class VerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerificationError(message)


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def strict_json(path: Path) -> Any:
    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                fail(f'JSON duplicate key: {display_path(path)}: {key}')
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        fail(f'JSON non-finite number: {display_path(path)}: {value}')

    try:
        return json.loads(
            path.read_text(encoding='utf-8'),
            object_pairs_hook=reject_duplicate,
            parse_constant=reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        fail(f'JSON syntax error: {display_path(path)}: {exc}')


def relative_files() -> list[str]:
    try:
        return [record.relative for record in source_records(ROOT)]
    except UnsafeTreeError as exc:
        fail(str(exc))


def require_files(paths: Iterable[str]) -> None:
    for relative in paths:
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            fail(f'missing regular file: {relative}')


def check_required_structure() -> None:
    require_files([
        'README.md', 'CONTRIBUTING.md', 'LICENSE.md',
        'LICENSES/MIT.txt', 'LICENSES/CC-BY-4.0.txt',
        'Makefile', 'prepare.sh', 'verify.sh',
        'scripts/verify_submission.py', 'scripts/verify_repository.py',
        'scripts/verify_isolated.py', 'scripts/source_fingerprint.py',
        'config/repository-files.txt', 'reference/source-index.md',
        'reference/glossary.md', 'docs/00-roadmap.md', 'docs/17-capstone.md',
    ])

    core_docs = sorted((ROOT / 'docs').glob('[0-9][0-9]-*.md'))
    if len(core_docs) != 18:
        fail(f'core docs must be 00 through 17 (18 files), found {len(core_docs)}')
    if len(list((ROOT / 'docs/90-optional-labs').glob('*.md'))) < 6:
        fail('at least six optional-lab documents are required')
    if len(list((ROOT / 'docs/runbooks').glob('*.md'))) < 8:
        fail('at least eight runbook documents are required')

    actual_staged = {
        path.name for path in (ROOT / 'exercises').iterdir()
        if path.is_dir() and re.match(r'^(?:0[1-9]|1[0-2])-', path.name)
    }
    if actual_staged != set(STAGED_EXERCISES):
        fail(f'staged exercise set differs: {sorted(actual_staged)}')
    for name in STAGED_EXERCISES:
        base = Path('exercises') / name
        require_files([
            (base / 'README.md').as_posix(),
            (base / 'contract.json').as_posix(),
            (base / 'skeleton/submission.json').as_posix(),
            (base / 'reference/submission.json').as_posix(),
            (base / 'known_bad/submission.json').as_posix(),
        ])

    require_files([
        'exercises/13-platform-control-plane/README.md',
        'scripts/verify_platform_model.py',
        'scripts/test_verify_platform_model.py',
        'projects/internal-developer-platform/README.md',
        'scripts/verify_capstone.py',
    ])

    model_lab = ROOT / 'exercises/13-platform-control-plane'
    for rel in ('README.md', 'contract.json', 'skeleton/platform_model.py', 'reference/platform_model.py'):
        if not (model_lab / rel).is_file():
            fail(f'13-platform-control-plane: 파일 누락 {rel}')


def check_manifest() -> None:
    manifest_path = ROOT / 'config/repository-files.txt'
    lines = manifest_path.read_text(encoding='utf-8').splitlines()
    expected = [line.strip() for line in lines if line.strip()]
    if expected != sorted(set(expected)):
        fail('repository manifest must be sorted and contain no duplicates')
    for relative in expected:
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or path.as_posix() != relative:
            fail(f'unsafe path in repository manifest: {relative}')
    actual = relative_files()
    if expected != actual:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        fail(
            'repository manifest differs from files: '
            f'missing={missing[:12]} extra={extra[:12]}'
        )


def _fence_and_visible_lines(text: str, relative: Path) -> list[str]:
    visible: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line_number, line in enumerate(text.splitlines(), 1):
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character = None
                fence_length = 0
            continue
        if fence_character is None:
            visible.append(line)
    if fence_character is not None:
        fail(f'unclosed Markdown code fence: {relative}')
    return visible


def _github_slug(value: str) -> str:
    value = re.sub(r'<[^>]+>', '', value)
    value = re.sub(r'[`*_~]', '', value).strip().lower()
    value = re.sub(r'[^\w\s-]', '', value, flags=re.UNICODE)
    return re.sub(r'\s', '-', value)


def _unique_anchor(base: str, used: set[str], next_suffix: dict[str, int]) -> str:
    candidate = base
    if candidate in used:
        suffix = next_suffix.get(base, 1)
        candidate = f'{base}-{suffix}'
        while candidate in used:
            suffix += 1
            candidate = f'{base}-{suffix}'
        next_suffix[base] = suffix + 1
    else:
        next_suffix.setdefault(base, 1)
    used.add(candidate)
    return candidate


def _anchors(path: Path) -> set[str]:
    visible = _fence_and_visible_lines(path.read_text(encoding='utf-8'), path.relative_to(ROOT))
    anchors: set[str] = set()
    generated: set[str] = set()
    next_suffix: dict[str, int] = {}
    for line in visible:
        heading = HEADING_RE.match(line)
        if heading:
            text = re.sub(r'\s+#+\s*$', '', heading.group(2))
            base = _github_slug(text)
            anchors.add(_unique_anchor(base, generated, next_suffix))
        anchors.update(HTML_ID_RE.findall(line))
    return anchors


def _link_target(raw: str) -> str:
    value = raw.strip()
    if value.startswith('<') and '>' in value:
        return value[1:value.index('>')]
    if re.search(r'\s+["\']', value):
        return re.split(r'\s+["\']', value, maxsplit=1)[0]
    return value


def check_markdown() -> tuple[int, int]:
    markdown_files = [
        path for path in sorted(ROOT.rglob('*.md'))
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts)
    ]
    anchor_cache: dict[Path, set[str]] = {}
    link_count = 0
    for path in markdown_files:
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding='utf-8')
        visible = _fence_and_visible_lines(text, relative)
        first_nonempty = next((line for line in visible if line.strip()), '')
        if not first_nonempty.startswith('# '):
            fail(f'Markdown must start with an H1: {relative}')
        for raw in MARKDOWN_LINK_RE.findall('\n'.join(visible)):
            target = _link_target(raw)
            if not target or target.startswith(('http://', 'https://', 'mailto:')):
                continue
            link_count += 1
            decoded = unquote(target)
            file_part, separator, fragment = decoded.partition('#')
            resolved = path if not file_part else (path.parent / file_part).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f'{relative}: link escapes repository: {raw}')
            if not resolved.exists():
                fail(f'{relative}: broken internal link: {raw}')
            if separator and fragment and resolved.is_file() and resolved.suffix.lower() == '.md':
                anchors = anchor_cache.setdefault(resolved, _anchors(resolved))
                if fragment not in anchors:
                    fail(f'{relative}: missing Markdown anchor {fragment!r} in {resolved.relative_to(ROOT)}')
    return len(markdown_files), link_count


def check_json() -> int:
    paths = [
        path for path in sorted(ROOT.rglob('*.json'))
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts)
    ]
    for path in paths:
        strict_json(path)
    return len(paths)


def _value_type(value: Any) -> str:
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, str):
        return 'string'
    if isinstance(value, int) and not isinstance(value, bool):
        return 'integer'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return 'number'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, dict):
        return 'object'
    return type(value).__name__


def validate_schema(instance: Any, schema: dict[str, Any], pointer: str = '$') -> None:
    expected_type = schema.get('type')
    if expected_type is not None:
        allowed = [expected_type] if isinstance(expected_type, str) else expected_type
        actual = _value_type(instance)
        if actual not in allowed and not (actual == 'integer' and 'number' in allowed):
            fail(f'schema mismatch at {pointer}: expected {allowed}, got {actual}')
    if 'const' in schema and instance != schema['const']:
        fail(f'schema const mismatch at {pointer}')
    if 'enum' in schema and instance not in schema['enum']:
        fail(f'schema enum mismatch at {pointer}: {instance!r}')
    if isinstance(instance, str):
        if len(instance) < schema.get('minLength', 0):
            fail(f'schema minLength mismatch at {pointer}')
        if 'pattern' in schema and re.fullmatch(schema['pattern'], instance) is None:
            fail(f'schema pattern mismatch at {pointer}: {instance!r}')
    if isinstance(instance, list):
        if len(instance) < schema.get('minItems', 0):
            fail(f'schema minItems mismatch at {pointer}')
        if 'items' in schema:
            for index, item in enumerate(instance):
                validate_schema(item, schema['items'], f'{pointer}/{index}')
    if isinstance(instance, dict):
        required = schema.get('required', [])
        missing = [key for key in required if key not in instance]
        if missing:
            fail(f'schema required fields missing at {pointer}: {missing}')
        properties = schema.get('properties', {})
        if schema.get('additionalProperties') is False:
            unknown = sorted(set(instance) - set(properties))
            if unknown:
                fail(f'schema unknown fields at {pointer}: {unknown}')
        for key, value in instance.items():
            if key in properties:
                validate_schema(value, properties[key], f'{pointer}/{key}')


def check_platform_api_schema() -> None:
    schema_path = ROOT / 'examples/platform-api/service-environment.schema.json'
    example_path = ROOT / 'examples/platform-api/service-environment.example.json'
    schema = strict_json(schema_path)
    example = strict_json(example_path)
    if not isinstance(schema, dict) or schema.get('$schema') != 'https://json-schema.org/draft/2020-12/schema':
        fail('platform API schema must declare JSON Schema draft 2020-12')
    validate_schema(example, schema)
    mutant = json.loads(json.dumps(example))
    mutant['spec']['releaseDigest'] = 'sha256:not-a-digest'
    try:
        validate_schema(mutant, schema)
    except VerificationError:
        pass
    else:
        fail('platform API schema accepted the known-bad digest mutant')


def _strip_yaml_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if character == '\\' and quote == '"':
            escaped = True
            continue
        if character in {'"', "'"}:
            if quote is None:
                quote = character
            elif quote == character:
                quote = None
            continue
        if character == '#' and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index]
    if quote is not None:
        fail('unterminated quote in YAML')
    return value


def _mapping_colon(value: str) -> int | None:
    quote: str | None = None
    depth = 0
    for index, character in enumerate(value):
        if character in {'"', "'"}:
            if quote is None:
                quote = character
            elif quote == character:
                quote = None
            continue
        if quote is not None:
            continue
        if character in '[{':
            depth += 1
        elif character in ']}':
            depth -= 1
            if depth < 0:
                return None
        elif character == ':' and depth == 0:
            if index + 1 == len(value) or value[index + 1].isspace():
                return index
    return None


def _flow_balance(
    value: str,
    stack: list[str],
    relative: str,
    line_number: int,
) -> None:
    quote: str | None = None
    escaped = False
    index = 0
    closing = {'[': ']', '{': '}'}
    while index < len(value):
        character = value[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if quote == '"' and character == '\\':
            escaped = True
            index += 1
            continue
        if quote == "'" and character == "'" and index + 1 < len(value) and value[index + 1] == "'":
            index += 2
            continue
        if character in {'"', "'"}:
            if quote is None:
                quote = character
            elif quote == character:
                quote = None
            index += 1
            continue
        if quote is None:
            if character in closing:
                stack.append(closing[character])
            elif character in ']}':
                if not stack or stack[-1] != character:
                    fail(f'unbalanced YAML flow collection: {relative}:{line_number}')
                stack.pop()
        index += 1


def check_yaml_subset(paths: Iterable[Path] | None = None) -> int:
    selected_paths = sorted(paths) if paths is not None else sorted([*ROOT.rglob('*.yaml'), *ROOT.rglob('*.yml')])
    document_count = 0
    for path in selected_paths:
        relative_path = Path(display_path(path))
        if any(part in EXCLUDED_DIRS for part in relative_path.parts):
            continue
        relative = relative_path.as_posix()
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeError as exc:
            fail(f'YAML must be UTF-8: {relative}: {exc}')
        if '\t' in text:
            fail(f'YAML tabs are not allowed: {relative}')
        documents: list[set[str]] = [set()]
        top_seen: set[str] = set()
        flow_stack: list[str] = []
        meaningful = False
        document_index = 0
        parent_stack: list[tuple[int, str]] = []
        seen_mapping_keys: dict[tuple[int, tuple[str, ...]], set[str]] = {}
        sequence_counts: dict[tuple[int, tuple[str, ...], int], int] = {}
        for line_number, raw in enumerate(text.splitlines(), 1):
            value = _strip_yaml_comment(raw).rstrip()
            if not value.strip() or value.lstrip().startswith(('%YAML', '%TAG')):
                continue
            if value == '---':
                if meaningful:
                    documents.append(set())
                    top_seen = set()
                    meaningful = False
                    document_index += 1
                    parent_stack = []
                    seen_mapping_keys = {}
                    sequence_counts = {}
                continue
            if value == '...':
                continue
            indentation = len(value) - len(value.lstrip(' '))
            if indentation % 2:
                fail(f'YAML indentation must use two-space levels: {relative}:{line_number}')
            while parent_stack and parent_stack[-1][0] >= indentation:
                parent_stack.pop()
            parent = tuple(token for _, token in parent_stack)
            content = value[indentation:]
            is_sequence = content.startswith('-')
            if content.startswith('-'):
                if content != '-' and not content.startswith('- '):
                    fail(f'invalid YAML sequence marker: {relative}:{line_number}')
                content = content[1:].lstrip()
                sequence_scope = (document_index, parent, indentation)
                sequence_index = sequence_counts.get(sequence_scope, 0)
                sequence_counts[sequence_scope] = sequence_index + 1
                item_token = f'[{sequence_index}]'
                parent_stack.append((indentation, item_token))
                parent = (*parent, item_token)
                if not content:
                    meaningful = True
                    continue
            colon = _mapping_colon(content)
            if colon is None:
                if not raw.lstrip().startswith('- '):
                    fail(f'unsupported or invalid YAML line: {relative}:{line_number}')
            else:
                key = content[:colon].strip()
                if not key:
                    fail(f'empty YAML key: {relative}:{line_number}')
                scalar = content[colon + 1:].strip()
                if scalar and _mapping_colon(scalar) is not None:
                    fail(f'unquoted YAML scalar contains mapping delimiter: {relative}:{line_number}')
                scope = (document_index, parent)
                seen = seen_mapping_keys.setdefault(scope, set())
                if key in seen:
                    fail(f'duplicate YAML key in one mapping: {relative}:{line_number}: {key}')
                seen.add(key)
                if not scalar:
                    parent_stack.append((indentation, key))
                if indentation == 0 and not is_sequence:
                    if key in top_seen:
                        fail(f'duplicate top-level YAML key: {relative}:{line_number}: {key}')
                    top_seen.add(key)
                    documents[-1].add(key)
            _flow_balance(content, flow_stack, relative, line_number)
            meaningful = True
        if flow_stack:
            fail(f'unbalanced YAML flow collection: {relative}')
        if not meaningful and not any(documents):
            fail(f'empty YAML file: {relative}')
        for index, keys in enumerate(documents, 1):
            if not {'apiVersion', 'kind'}.issubset(keys):
                fail(f'YAML document needs apiVersion and kind: {relative} document {index}')
            document_count += 1
    return document_count


def check_shell_python_and_modes() -> tuple[int, int]:
    shell_paths = [ROOT / 'prepare.sh', ROOT / 'verify.sh']
    for path in shell_paths:
        result = subprocess.run(['sh', '-n', str(path)], capture_output=True, text=True)
        if result.returncode != 0:
            fail(f'shell syntax error: {path.relative_to(ROOT)}: {result.stderr.strip()}')

    python_count = 0
    executable_count = 0
    for record in source_records(ROOT):
        relative = Path(record.relative)
        data = record.path.read_bytes()
        if len(data) > 2 * 1024 * 1024:
            fail(f'file exceeds 2 MiB repository limit: {record.relative}')
        should_execute = record.relative in {'prepare.sh', 'verify.sh'}
        if relative.suffix == '.py':
            python_count += 1
            try:
                compile(data, record.relative, 'exec')
            except (SyntaxError, ValueError) as exc:
                fail(f'Python syntax error: {record.relative}: {exc}')
            should_execute = data.startswith(b'#!')
        is_executable = bool(record.mode & stat.S_IXUSR)
        if should_execute and not is_executable:
            fail(f'missing executable mode: {record.relative}')
        if is_executable:
            executable_count += 1
            if not should_execute:
                fail(f'unexpected executable mode on data/document file: {record.relative}')
    return python_count, executable_count


def check_ignore_and_secrets() -> None:
    ignore_lines = {
        line.strip() for line in (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    }
    missing = sorted(REQUIRED_IGNORE_PATTERNS - ignore_lines)
    if missing:
        fail(f'.gitignore is missing safety patterns: {missing}')

    forbidden_names = re.compile(
        r'(^|/)(?:\.env(?:\..*)?|kubeconfig[^/]*|[^/]+\.kubeconfig|'
        r'id_(?:rsa|ed25519)(?:\..*)?|[^/]+\.tfstate(?:\..*)?|'
        r'[^/]+\.tfvars(?:\.json)?|[^/]+\.(?:pem|key|p12|pfx|tfplan|plan|bin))$'
    )
    secret_patterns = {
        'private key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
        'AWS access key': re.compile(rb'\bAKIA[0-9A-Z]{16}\b'),
        'GitHub token': re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{36,}\b'),
        'Slack token': re.compile(rb'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    }
    for record in source_records(ROOT):
        if forbidden_names.search(record.relative):
            fail(f'secret/state-like file must not be committed: {record.relative}')
        data = record.path.read_bytes()
        for label, pattern in secret_patterns.items():
            if pattern.search(data):
                fail(f'possible {label} in {record.relative}')


def run_checked(command: list[str], label: str, expected: int = 0, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    for key in ('PYTHONHOME', 'PYTHONPATH', 'PYTHONSTARTUP', 'PYTHONINSPECT'):
        environment.pop(key, None)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    environment['PYTHONNOUSERSITE'] = '1'
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != expected:
        output = (result.stdout + result.stderr).strip()
        fail(f'{label}: expected exit {expected}, got {result.returncode}\n{output[-3000:]}')
    return result


def check_exercises() -> tuple[int, int, int]:
    verifier = ROOT / 'scripts/verify_submission.py'
    accepted = 0
    skeletons_rejected = 0
    known_bad_rejected = 0
    for name in STAGED_EXERCISES:
        exercise = ROOT / 'exercises' / name
        command = [sys.executable, str(verifier), str(exercise / 'contract.json')]
        run_checked(command + [str(exercise / 'reference/submission.json')], f'{name} reference', 0)
        run_checked(command + [str(exercise / 'skeleton/submission.json')], f'{name} skeleton', 1)
        run_checked(command + [str(exercise / 'known_bad/submission.json')], f'{name} known_bad', 1)
        accepted += 1
        skeletons_rejected += 1
        known_bad_rejected += 1
    return accepted, skeletons_rejected, known_bad_rejected


def check_meta_and_profile_tests() -> tuple[int, int]:
    tests = sorted((ROOT / 'scripts').glob('test_*.py'))
    if len(tests) < 3:
        fail(f'at least three verifier meta-test modules are required, found {len(tests)}')
    run_checked(
        [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_*.py', '-v'],
        'verifier meta-tests',
        timeout=180,
    )
    profile = ROOT / 'examples/optional-labs/check_profiles.py'
    require_files(['examples/optional-labs/check_profiles.py'])
    result = run_checked([sys.executable, '-B', str(profile)], 'optional local profiles')
    profile_cases = len(re.findall(r'^\[PASS\]\s', result.stdout, flags=re.MULTILINE))
    if profile_cases < 10:
        fail(f'optional local profile checker exercised too few cases: {profile_cases}')
    return len(tests), profile_cases


def check_contract_traceability() -> None:
    require_files([
        'reference/contract-evidence-map.md',
        'reference/manual-review-guide.md',
    ])
    evidence = (ROOT / 'reference/contract-evidence-map.md').read_text(encoding='utf-8')
    manual = (ROOT / 'reference/manual-review-guide.md').read_text(encoding='utf-8')
    for identifier in [*(f'OWN-{index}' for index in range(1, 6)), *(f'EXIT-{index}' for index in range(1, 4))]:
        if identifier not in evidence:
            fail(f'contract evidence map does not mention {identifier}')
    for identifier in (f'EXIT-{index}' for index in range(1, 4)):
        if identifier not in manual:
            fail(f'manual review guide does not mention {identifier}')


def check_optional_profiles() -> int:
    checker = ROOT / 'examples/optional-labs/check_profiles.py'
    result = subprocess.run(
        [sys.executable, str(checker)], cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        fail(f'선택 실습 결정적 검사가 실패했습니다.\n{result.stdout}{result.stderr}')
    match = re.search(r'PROFILE SUMMARY: PASS cases=(\d+)', result.stdout)
    if not match:
        fail(f'선택 실습 결정적 검사 summary를 찾을 수 없습니다.\n{result.stdout}')
    return int(match.group(1))


def check_prepared_fingerprint() -> None:
    marker_path = ROOT / '.guide/platform-engineering/prepared.json'
    if marker_path.is_symlink() or not marker_path.is_file():
        fail('preparation marker is missing or unsafe; run ./prepare.sh')
    marker = strict_json(marker_path)
    current = fingerprint(ROOT)
    if (
        not isinstance(marker, dict)
        or marker.get('schemaVersion') != 1
        or marker.get('guide') != 'platform-engineering'
        or marker.get('sourceSha256') != current[0]
        or marker.get('sourceFiles') != current[1]
    ):
        fail('prepared source fingerprint does not match current source')


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--quick', action='store_true', help='all mandatory checks except preparation marker')
    mode.add_argument('--full', action='store_true', help='mandatory checks plus preparation marker')
    args = parser.parse_args()

    check_required_structure()
    check_manifest()
    markdown_count, link_count = check_markdown()
    json_count = check_json()
    check_platform_api_schema()
    yaml_documents = check_yaml_subset()
    python_count, executable_count = check_shell_python_and_modes()
    check_ignore_and_secrets()
    accepted, skeletons, known_bad = check_exercises()
    test_modules, profile_cases = check_meta_and_profile_tests()
    check_contract_traceability()
    if args.full:
        check_prepared_fingerprint()

    selected_mode = 'full' if args.full else 'quick'
    print(
        f'OK mode={selected_mode} files={len(relative_files())} markdown={markdown_count} '
        f'links={link_count} json={json_count} yaml_documents={yaml_documents} '
        f'python={python_count} executables={executable_count} references={accepted} '
        f'skeletons_rejected={skeletons} known_bad_rejected={known_bad} '
        f'meta_modules={test_modules} profile_cases={profile_cases} mandatory_skips=0'
    )
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (VerificationError, UnsafeTreeError, OSError, subprocess.TimeoutExpired) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
