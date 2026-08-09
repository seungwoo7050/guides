#!/usr/bin/env python3
"""Verify repository contracts and reproducibility inputs.

These checks reject broken structure and shallow machine-readable contracts.
They deliberately do not claim that technical explanations are correct or that
the learning path is educationally complete; those remain human review tasks.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
H2_RE = re.compile(r"^##(?!#)[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
IDENTIFIER_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)+$")
ARTIFACT_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")
EXERCISE_ID_RE = re.compile(r"^[0-9]{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
RELATED_DOC_RE = re.compile(r"^docs/[a-z0-9][a-z0-9._/-]*\.md$")

EXPECTED_CORE_DOCS = [
    "docs/01-visual-model/01-rendering-contract-and-frame.md",
    "docs/01-visual-model/02-coordinate-spaces-and-transforms.md",
    "docs/01-visual-model/03-camera-projection-and-clipping.md",
    "docs/01-visual-model/04-images-color-and-alpha.md",
    "docs/01-visual-model/05-sampling-filtering-and-aliasing.md",
    "docs/02-software-rasterization/06-triangle-setup-coverage-and-fill-rules.md",
    "docs/02-software-rasterization/07-interpolation-perspective-and-derivatives.md",
    "docs/02-software-rasterization/08-depth-culling-blending-and-transparency.md",
    "docs/02-software-rasterization/09-software-rasterizer-capstone.md",
    "docs/03-lighting-assets-scene/10-normals-lighting-and-materials.md",
    "docs/03-lighting-assets-scene/11-textures-mipmaps-and-normal-mapping.md",
    "docs/03-lighting-assets-scene/12-meshes-scenes-and-asset-contracts.md",
    "docs/03-lighting-assets-scene/13-visibility-spatial-organization-and-lod.md",
    "docs/04-gpu-rendering/14-gpu-execution-and-command-model.md",
    "docs/04-gpu-rendering/15-resources-layouts-transfers-and-formats.md",
    "docs/04-gpu-rendering/16-shaders-pipelines-and-render-passes.md",
    "docs/04-gpu-rendering/17-frame-lifecycle-synchronization-and-resize.md",
    "docs/04-gpu-rendering/18-debugging-validation-and-frame-capture.md",
    "docs/04-gpu-rendering/19-performance-profiling-and-frame-budget.md",
    "docs/04-gpu-rendering/20-gpu-renderer-capstone.md",
]
EXPECTED_EXERCISES = [
    "01-transform-trace",
    "02-sampling-and-color",
    "03-triangle-coverage",
    "04-perspective-depth-blend",
    "05-textured-lit-scene",
    "06-gpu-first-frame",
    "07-frame-debugging",
    "08-renderer-capstone",
]
REQUIRED_CORE_SECTIONS = ["## 목표", "## 시작하기 전에", "## 연결 실습", "## 완료 기준"]
REQUIRED_CONTRACT_FIELDS = {
    "schema_version",
    "id",
    "title",
    "related_docs",
    "required_artifacts",
    "invariants",
    "known_bad_mutations",
    "completion_evidence",
}
ARRAY_MINIMUMS = {
    "related_docs": 1,
    "required_artifacts": 4,
    "invariants": 4,
    "known_bad_mutations": 4,
    "completion_evidence": 3,
}
README_ROLE_HEADINGS = {
    "목적": ("목적",),
    "입력·초기 상태": ("초기 상태", "입력 fixture", "결함 case", "필수 scene", "초기 단계"),
    "구현·조사 경계": ("구현할 경계", "초기 단계", "조사 절차", "필수 subsystem"),
    "artifact": ("필수 artifact", "report 필수 항목", "제출 구조"),
    "대표 실패": ("알려진 오답", "결함 case"),
    "완료 근거": ("완료 근거", "완료 판정"),
    "재현 절차": ("준비·workspace",),
}
PLACEHOLDER_TOKENS = {
    "todo",
    "tbd",
    "fixme",
    "placeholder",
    "dummy",
    "nonsense",
    "lorem",
    "foo",
    "bar",
    "baz",
    "stuff",
    "thing",
}
SEMANTIC_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "is",
    "are",
    "to",
    "of",
    "for",
    "with",
    "without",
    "in",
    "on",
    "by",
    "as",
    "if",
    "when",
    "only",
    "at",
    "least",
    "all",
    "each",
    "per",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
}
ARTIFACT_EVIDENCE_TOKENS = {
    "artifact",
    "attachment",
    "capture",
    "count",
    "diff",
    "image",
    "json",
    "log",
    "manifest",
    "map",
    "metadata",
    "pgm",
    "ppm",
    "report",
    "screenshot",
    "trace",
}
COMPLETION_EVIDENCE_TOKENS = ARTIFACT_EVIDENCE_TOKENS | {
    "assertion",
    "baseline",
    "comparison",
    "explanation",
    "failure",
    "note",
    "plan",
    "policy",
    "provenance",
    "result",
    "test",
    "tolerance",
    "validation",
}
SKIPPED_PATH_PREFIXES = (
    Path(".git"),
    Path(".guide"),
    Path("build"),
    Path("out"),
    Path("exercises/08-renderer-capstone/project/workspace"),
)


class DuplicateJsonKey(ValueError):
    pass


def fail(message: str) -> None:
    raise AssertionError(message)


def _is_skipped(relative: Path) -> bool:
    if "__pycache__" in relative.parts:
        return True
    return any(relative.parts[: len(prefix.parts)] == prefix.parts for prefix in SKIPPED_PATH_PREFIXES)


def _source_markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if not _is_skipped(path.relative_to(ROOT))
    )


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey(key)
        result[key] = value
    return result


def _load_json_strict(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except DuplicateJsonKey as error:
        fail(f"{path.relative_to(ROOT)}: 중복 JSON key {error}")
    except json.JSONDecodeError as error:
        fail(f"{path.relative_to(ROOT)}: JSON parse 실패 line={error.lineno} column={error.colno}: {error.msg}")
    if not isinstance(payload, dict):
        fail(f"{path.relative_to(ROOT)}: JSON root는 object여야 합니다.")
    return payload


def check_required_files() -> None:
    paths = [
        "README.md",
        "CONTRIBUTING.md",
        "LICENSE.md",
        "LICENSES/CC-BY-4.0.txt",
        "LICENSES/MIT.txt",
        "docs/00-roadmap.md",
        "exercises/README.md",
        "exercises/contract.schema.json",
        "reference/glossary.md",
        "reference/formulas-and-checklist.md",
        "reference/sources.md",
        "reference/version-baseline.md",
        "tools/ppm_diff.py",
        "scripts/source_fingerprint.py",
        "prepare.sh",
        "verify.sh",
        "Makefile",
        *EXPECTED_CORE_DOCS,
    ]
    for relative in paths:
        if not (ROOT / relative).is_file():
            fail(f"필수 파일이 없습니다: {relative}")


def check_core_documents() -> None:
    headings: set[str] = set()
    for relative in EXPECTED_CORE_DOCS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        if len(text.split()) < 350:
            fail(f"{relative}: 개념 문서가 지나치게 짧습니다.")
        first = text.splitlines()[0] if text.splitlines() else ""
        if not first.startswith("# "):
            fail(f"{relative}: H1 제목이 필요합니다.")
        if first in headings:
            fail(f"{relative}: 중복 H1 제목 {first}")
        headings.add(first)
        for section in REQUIRED_CORE_SECTIONS:
            if section not in text:
                fail(f"{relative}: 공통 절 누락 {section}")
        for marker in ("TBD", "FIXME", "lorem ipsum"):
            if marker.lower() in text.lower():
                fail(f"{relative}: 미완성 marker {marker}")
        prose = _without_fenced_code(text)
        prose_lines = [
            re.sub(r"\s+", " ", line.strip())
            for line in prose.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        prose_words = re.findall(r"[\w가-힣+-]+", " ".join(prose_lines).lower())
        if len(prose_words) < 450 or len(set(prose_words)) < 250:
            fail(f"{relative}: 설명 어휘가 지나치게 적거나 반복적입니다.")
        if len(set(prose_lines)) < 30 or len(set(prose_lines)) / len(prose_lines) < 0.75:
            fail(f"{relative}: 고유한 설명 문장이 지나치게 적습니다.")


def _without_fenced_code(text: str) -> str:
    lines: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if fence is None and (stripped.startswith("```") or stripped.startswith("~~~")):
            fence = stripped[:3]
            continue
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            continue
        lines.append(line)
    return "\n".join(lines)


def _heading_plain_text(markdown: str) -> str:
    value = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", markdown)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("`", "").replace("*", "").replace("~", "")
    return html.unescape(value).strip()


def _github_slug(markdown_heading: str) -> str:
    plain = _heading_plain_text(markdown_heading).lower()
    kept = "".join(character for character in plain if character.isalnum() or character in " _-")
    return re.sub(r"\s+", "-", kept.strip())


def _markdown_anchors(text: str) -> set[str]:
    counts: dict[str, int] = {}
    anchors: set[str] = set()
    for match in HEADING_RE.finditer(_without_fenced_code(text)):
        base = _github_slug(match.group(2))
        if not base:
            continue
        duplicate = counts.get(base, 0)
        counts[base] = duplicate + 1
        anchors.add(base if duplicate == 0 else f"{base}-{duplicate}")
    return anchors


def _raw_link_destination(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<"):
        closing = target.find(">")
        if closing == -1:
            return target
        target = target[1:closing]
    elif re.search(r"\s", target):
        target = target.split(None, 1)[0]
    return unquote(target)


def _resolve_internal_target(source: Path, raw: str) -> tuple[Path, str] | None:
    target = _raw_link_destination(raw)
    if not target:
        return None
    if target.startswith("//") or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
        return None
    path_text, separator, fragment = target.partition("#")
    if path_text.startswith("/"):
        fail(f"{source.relative_to(ROOT)}: 절대 경로 링크 {raw}")
    resolved = source if not path_text else (source.parent / path_text).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        fail(f"{source.relative_to(ROOT)}: 저장소 밖 상대 링크 {raw}")
    return resolved, fragment if separator else ""


def _internal_markdown_targets(path: Path, text: str) -> set[Path]:
    result: set[Path] = set()
    for raw in MARKDOWN_LINK_RE.findall(_without_fenced_code(text)):
        resolved = _resolve_internal_target(path, raw)
        if resolved is None:
            continue
        target, _ = resolved
        if target.suffix.lower() == ".md":
            result.add(target.resolve())
    return result


def check_markdown_links() -> None:
    files = _source_markdown_files()
    if len(files) < 40:
        fail(f"Markdown 문서 수가 예상보다 적습니다: {len(files)}")
    anchor_cache: dict[Path, set[str]] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        for raw in MARKDOWN_LINK_RE.findall(_without_fenced_code(text)):
            resolved = _resolve_internal_target(path, raw)
            if resolved is None:
                continue
            target, fragment = resolved
            if not target.exists():
                fail(f"{path.relative_to(ROOT)}: 깨진 링크 {raw}")
            if not fragment:
                continue
            if not target.is_file() or target.suffix.lower() != ".md":
                fail(f"{path.relative_to(ROOT)}: Markdown가 아닌 대상의 anchor 링크 {raw}")
            anchors = anchor_cache.setdefault(
                target.resolve(), _markdown_anchors(target.read_text(encoding="utf-8"))
            )
            requested = fragment.lower()
            if requested not in anchors:
                fail(f"{path.relative_to(ROOT)}: 존재하지 않는 anchor #{fragment} -> {target.relative_to(ROOT)}")


def check_contract_schema() -> dict[str, object]:
    schema_path = ROOT / "exercises/contract.schema.json"
    schema = _load_json_strict(schema_path)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail("contract schema는 JSON Schema draft 2020-12를 사용해야 합니다.")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        fail("contract schema root는 additionalProperties=false인 object여야 합니다.")
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or set(required) != REQUIRED_CONTRACT_FIELDS:
        fail("contract schema required field가 정본과 다릅니다.")
    if not isinstance(properties, dict) or set(properties) != REQUIRED_CONTRACT_FIELDS:
        fail("contract schema properties가 정본과 다릅니다.")
    schema_version = properties.get("schema_version")
    if not isinstance(schema_version, dict) or schema_version.get("const") != 1:
        fail("contract schema_version은 const 1이어야 합니다.")
    for field, minimum in ARRAY_MINIMUMS.items():
        definition = properties.get(field)
        if not isinstance(definition, dict):
            fail(f"contract schema {field} 정의가 object가 아닙니다.")
        if definition.get("type") != "array" or definition.get("uniqueItems") is not True:
            fail(f"contract schema {field}는 unique array여야 합니다.")
        if definition.get("minItems") != minimum:
            fail(f"contract schema {field}.minItems는 {minimum}이어야 합니다.")
        items = definition.get("items")
        if not isinstance(items, dict) or items.get("type") != "string" or not items.get("pattern"):
            fail(f"contract schema {field} item에는 string pattern이 필요합니다.")
    return schema


def _identifier_tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", value.lower()) if token not in SEMANTIC_STOPWORDS]


def _word_forms(token: str) -> set[str]:
    forms = {token}
    if token.endswith("ies") and len(token) > 4:
        forms.add(token[:-3] + "y")
    if token.endswith("ices") and len(token) > 5:
        forms.add(token[:-4] + "ex")
    if token.endswith("s") and len(token) > 3:
        forms.add(token[:-1])
    if token.endswith("es") and len(token) > 4:
        forms.add(token[:-2])
    if token.endswith("ing") and len(token) > 5:
        forms.add(token[:-3])
    if token.endswith("ed") and len(token) > 4:
        forms.add(token[:-2])
        forms.add(token[:-1])
    return forms


def _document_terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return set().union(*(_word_forms(word) for word in words)) if words else set()


def _validate_identifier_list(
    exercise_id: str,
    field: str,
    values: list[str],
    readme_text: str,
) -> None:
    minimum = ARRAY_MINIMUMS[field]
    if len(values) < minimum:
        fail(f"{exercise_id}.{field}: 최소 {minimum}개 항목이 필요합니다.")
    pattern = ARTIFACT_RE if field == "required_artifacts" else IDENTIFIER_RE
    document_terms = _document_terms(readme_text)
    total_terms = 0
    grounded_terms = 0
    semantic_signatures: set[tuple[str, ...]] = set()
    for value in values:
        if not pattern.fullmatch(value):
            fail(f"{exercise_id}.{field}: 형식이 잘못된 identifier {value}")
        if field == "required_artifacts":
            artifact_path = Path(value)
            if artifact_path.is_absolute() or ".." in artifact_path.parts:
                fail(f"{exercise_id}.{field}: 안전하지 않은 artifact 경로 {value}")
        raw_tokens = re.findall(r"[a-z0-9]+", value.lower())
        if PLACEHOLDER_TOKENS.intersection(raw_tokens):
            fail(f"{exercise_id}.{field}: placeholder identifier {value}")
        terms = _identifier_tokens(value)
        required_distinct = 1 if field == "required_artifacts" else 2
        if len(set(terms)) < required_distinct:
            fail(f"{exercise_id}.{field}: 의미 단어가 부족한 identifier {value}")
        signature = tuple(sorted(set(terms)))
        if signature in semantic_signatures:
            fail(f"{exercise_id}.{field}: 의미상 중복 identifier {value}")
        semantic_signatures.add(signature)
        expanded = set().union(*(_word_forms(term) for term in terms)) if terms else set()
        hits = sum(bool(_word_forms(term) & document_terms) for term in terms)
        total_terms += len(terms)
        grounded_terms += hits
        if not expanded.intersection(document_terms):
            fail(f"{exercise_id}.{field}: README에서 근거 단어를 찾을 수 없습니다: {value}")
    grounding_floor = {
        "required_artifacts": 0.80,
        "invariants": 0.45,
        "known_bad_mutations": 0.45,
        "completion_evidence": 0.40,
    }[field]
    if total_terms == 0 or grounded_terms / total_terms < grounding_floor:
        fail(
            f"{exercise_id}.{field}: README 의미 근거 비율이 낮습니다 "
            f"({grounded_terms}/{total_terms}, required={grounding_floor:.0%})"
        )


def _h2_sections(text: str) -> list[tuple[str, str]]:
    matches = list(H2_RE.finditer(text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((_heading_plain_text(match.group(1)), text[match.end() : end]))
    return sections


def _check_readme_roles(exercise_id: str, readme_text: str) -> None:
    lines = readme_text.splitlines()
    first = lines[0] if lines else ""
    stage_number = exercise_id[:2]
    if not re.match(rf"^# 실습 {re.escape(stage_number)}\b", first):
        fail(f"{exercise_id}: README H1이 stage 번호와 대응하지 않습니다: {first}")
    sections = _h2_sections(readme_text)
    if len(sections) < 7:
        fail(f"{exercise_id}: README의 학습 역할 절이 부족합니다: {len(sections)}")
    for title, body in sections:
        if len(body.split()) < 10:
            fail(f"{exercise_id}: 내용이 지나치게 짧은 절 ## {title}")
    titles = [title.lower() for title, _ in sections]
    for role, alternatives in README_ROLE_HEADINGS.items():
        if not any(any(fragment.lower() in title for fragment in alternatives) for title in titles):
            fail(f"{exercise_id}: README 역할 절 누락: {role} ({', '.join(alternatives)})")


def _validate_related_docs(exercise_id: str, values: list[str], readme: Path, readme_text: str) -> None:
    readme_targets = _internal_markdown_targets(readme, readme_text)
    for relative in values:
        if not RELATED_DOC_RE.fullmatch(relative):
            fail(f"{exercise_id}.related_docs: docs 아래 Markdown 경로여야 합니다: {relative}")
        doc = (ROOT / relative).resolve()
        if not doc.is_file():
            fail(f"{exercise_id}: related_docs가 존재하지 않습니다: {relative}")
        if doc not in readme_targets:
            fail(f"{exercise_id}: README가 related_doc에 링크하지 않습니다: {relative}")
        doc_targets = _internal_markdown_targets(doc, doc.read_text(encoding="utf-8"))
        if readme.resolve() not in doc_targets:
            fail(f"{exercise_id}: related_doc의 연결 실습이 README로 돌아오지 않습니다: {relative}")


def check_contracts() -> None:
    check_contract_schema()
    contract_paths = sorted((ROOT / "exercises").glob("*/contract.json"))
    found = sorted(path.parent.name for path in contract_paths)
    if found != EXPECTED_EXERCISES:
        fail(f"실습 contract 목록 불일치: {found}")
    exercise_index = ROOT / "exercises/README.md"
    index_targets = _internal_markdown_targets(
        exercise_index, exercise_index.read_text(encoding="utf-8")
    )
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    for contract_path in contract_paths:
        exercise_id = contract_path.parent.name
        readme = contract_path.parent / "README.md"
        if not readme.is_file():
            fail(f"{exercise_id}: README.md가 없습니다.")
        payload = _load_json_strict(contract_path)
        if set(payload) != REQUIRED_CONTRACT_FIELDS:
            fail(f"{exercise_id}: contract field 불일치 {sorted(set(payload) ^ REQUIRED_CONTRACT_FIELDS)}")
        if type(payload.get("schema_version")) is not int or payload.get("schema_version") != 1:
            fail(f"{exercise_id}: schema_version은 1이어야 합니다.")
        contract_id = payload.get("id")
        if not isinstance(contract_id, str) or not EXERCISE_ID_RE.fullmatch(contract_id):
            fail(f"{exercise_id}: contract id 형식이 잘못됐습니다: {contract_id!r}")
        if contract_id != exercise_id:
            fail(f"{exercise_id}: 디렉터리와 contract id가 다릅니다: {contract_id}")
        if contract_id in seen_ids:
            fail(f"중복 exercise id: {contract_id}")
        seen_ids.add(contract_id)
        title = payload.get("title")
        if (
            not isinstance(title, str)
            or len(title.strip()) < 4
            or "\n" in title
            or "\r" in title
        ):
            fail(f"{exercise_id}: title이 지나치게 짧거나 잘못됐습니다.")
        folded_title = title.casefold()
        if folded_title in seen_titles:
            fail(f"{exercise_id}: 중복 contract title {title}")
        seen_titles.add(folded_title)
        readme_text = readme.read_text(encoding="utf-8")
        if len(readme_text.split()) < 180:
            fail(f"{exercise_id}: README가 지나치게 짧습니다.")
        _check_readme_roles(exercise_id, readme_text)
        if readme.resolve() not in index_targets:
            fail(f"{exercise_id}: exercises/README.md 목록에서 README 링크를 찾을 수 없습니다.")

        arrays: dict[str, list[str]] = {}
        for field in ARRAY_MINIMUMS:
            value = payload.get(field)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                fail(f"{exercise_id}.{field}: 문자열 배열이어야 합니다.")
            if len(value) < ARRAY_MINIMUMS[field]:
                fail(f"{exercise_id}.{field}: 최소 {ARRAY_MINIMUMS[field]}개 항목이 필요합니다.")
            if len(value) != len(set(value)):
                fail(f"{exercise_id}.{field}: 중복 항목이 있습니다.")
            arrays[field] = value
        _validate_related_docs(exercise_id, arrays["related_docs"], readme, readme_text)
        for field in ("required_artifacts", "invariants", "known_bad_mutations", "completion_evidence"):
            _validate_identifier_list(exercise_id, field, arrays[field], readme_text)
        named_fields = ("required_artifacts", "invariants", "known_bad_mutations", "completion_evidence")
        for index, left in enumerate(named_fields):
            for right in named_fields[index + 1 :]:
                overlap = set(arrays[left]).intersection(arrays[right])
                if overlap:
                    fail(f"{exercise_id}: {left}/{right} 역할이 중복됩니다: {sorted(overlap)}")
        artifact_tokens = set().union(*(_identifier_tokens(value) for value in arrays["required_artifacts"]))
        if not artifact_tokens.intersection(ARTIFACT_EVIDENCE_TOKENS):
            fail(f"{exercise_id}.required_artifacts: 관측 가능한 artifact 종류가 없습니다.")
        evidence_tokens = set().union(*(_identifier_tokens(value) for value in arrays["completion_evidence"]))
        if not evidence_tokens.intersection(COMPLETION_EVIDENCE_TOKENS):
            fail(f"{exercise_id}.completion_evidence: 판단 가능한 evidence 종류가 없습니다.")


def check_convention_contract() -> None:
    roadmap = (ROOT / "docs/00-roadmap.md").read_text(encoding="utf-8")
    formula = (ROOT / "docs/90-appendix/01-math-conventions-and-formulas.md").read_text(encoding="utf-8")
    required_fragments = [
        "column vector",
        "P * V * M",
        "left-handed",
        "`+Z`",
        "`[0, 1]`",
        "왼쪽 위",
        "`+Y`는 아래",
        "pixel center",
        "linear RGB",
        "sRGB",
    ]
    for fragment in required_fragments:
        if fragment not in roadmap:
            fail(f"roadmap 좌표/색 정본 누락: {fragment}")
    for fragment in ("column vector", "P * V * M", "left-handed", "linear RGB", "sRGB"):
        if fragment not in formula:
            fail(f"formula 참조에 정본 누락: {fragment}")


def check_no_large_untracked_binaries() -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if _is_skipped(relative):
            continue
        if path.stat().st_size > 2_000_000:
            fail(f"2MB를 넘는 파일은 provenance 검토가 필요합니다: {relative}")


def run_ppm_self_test() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/ppm_diff.py"), "--self-test"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0 or "PPM_DIFF_SELF_TEST_OK" not in result.stdout:
        fail(
            "ppm_diff self-test 실패\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "저장소의 구조·링크·계약 최소 품질을 검사합니다. "
            "기술 정확성과 교육적 완성은 사람 검토 대상입니다."
        )
    )
    parser.add_argument("--quick", action="store_true", help="구조·문서·contract 검사만 실행")
    args = parser.parse_args()

    check_required_files()
    check_core_documents()
    check_markdown_links()
    check_contracts()
    check_convention_contract()
    check_no_large_untracked_binaries()
    if not args.quick:
        run_ppm_self_test()
    markdown_count = len(_source_markdown_files())
    print(
        "VERIFY_REPOSITORY_OK "
        f"docs={len(EXPECTED_CORE_DOCS)} markdown={markdown_count} "
        f"exercises={len(EXPECTED_EXERCISES)} quick={args.quick}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
