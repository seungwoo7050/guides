#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/fixed-step-replay"
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")

COMMON_DOC_HEADINGS = [
    "## 문제",
    "## 핵심 상태",
    "## 설계 계약",
    "## 대표 실패",
    "## 관찰과 검증",
    "## 실습 연결",
    "## 기존 브랜치와 경계",
    "## 완료 기준",
]

CONCEPT_DOCS = [
    "docs/01-game-product-and-runtime-contract.md",
    "docs/02-game-loop-time-and-frames.md",
    "docs/03-input-command-camera-and-ui.md",
    "docs/04-world-scene-entity-component-lifecycles.md",
    "docs/05-gameplay-rules-progression-and-data.md",
    "docs/06-assets-import-cooking-loading-and-memory.md",
    "docs/07-collision-physics-movement-and-space.md",
    "docs/08-animation-audio-vfx-and-presentation.md",
    "docs/09-save-migration-replay-and-determinism.md",
    "docs/10-game-ai-navigation-and-behavior.md",
    "docs/11-network-authority-replication-and-latency.md",
    "docs/12-tools-editor-builds-and-content-validation.md",
    "docs/13-testing-debugging-telemetry-and-reproduction.md",
    "docs/14-performance-budgets-profiling-and-scalability.md",
    "docs/15-platform-accessibility-lifecycle-and-release.md",
    "docs/16-game-team-interfaces-and-change-management.md",
]

EXERCISES = [
    "01-time-step-analysis",
    "02-input-command-contract",
    "03-world-lifecycle-review",
    "04-asset-loading-plan",
    "05-save-and-replay-migration",
    "06-authority-and-latency",
    "07-performance-budget-review",
    "08-release-readiness",
]

CAPSTONE_REQUIRED_ARTIFACTS = {
    "runtime-state-map.md",
    "time-and-input-contract.md",
    "state-ownership.csv",
    "world-and-asset-plan.md",
    "gameplay-rules.md",
    "movement-and-space.md",
    "presentation-contract.md",
    "save-and-replay.md",
    "authority-and-latency.md",
    "test-and-observability-plan.md",
    "performance-and-release.md",
    "traceability-matrix.csv",
    "change-plan.md",
}

CAPSTONE_OPTIONAL_ARTIFACTS = {"ai-and-navigation.md"}

LEARNING_MAP_DOCS = [
    "docs/00-roadmap.md",
    *CONCEPT_DOCS,
    "docs/17-capstone.md",
    "docs/90-engine-and-source-map.md",
]

LEARNING_MAP_EXERCISES = [f"exercises/{slug}/README.md" for slug in EXERCISES]

IMPLEMENTATION_MARKER_RE = re.compile(r"\[Implementation ([^\]\n]+)\]")
VALID_IMPLEMENTATION_LABEL_RE = re.compile(r"(?:0|[1-9]\d*)(?:-[1-9]\d*)?\Z")

IMPLEMENTATION_SCOPES = {
    "fixed-step-replay": {
        "index": "examples/fixed-step-replay/README.md",
        "heading": "## 권장 구현 순서",
        "files": {
            "examples/fixed-step-replay/README.md",
            "examples/fixed-step-replay/sim.py",
        },
    },
    "relay-arena-reference": {
        "index": "projects/relay-arena-vertical-slice/README.md",
        "heading": "### Reference 권장 구현 순서",
        "files": {
            "projects/relay-arena-vertical-slice/README.md",
            "projects/relay-arena-vertical-slice/reference/relay_arena.py",
        },
    },
}

REQUIRED_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "LICENSES/CC-BY-4.0.txt",
    "LICENSES/MIT.txt",
    "Makefile",
    "prepare.sh",
    "verify.sh",
    "docs/00-roadmap.md",
    *CONCEPT_DOCS,
    "docs/17-capstone.md",
    "docs/90-engine-and-source-map.md",
    "exercises/README.md",
    "examples/fixed-step-replay/README.md",
    "examples/fixed-step-replay/config.json",
    "examples/fixed-step-replay/input-trace.json",
    "examples/fixed-step-replay/expected-state.json",
    "examples/fixed-step-replay/sim.py",
    "scripts/check_submission.py",
    "scripts/new-workspace.sh",
    "scripts/new_workspace.py",
    "scripts/cleanup.py",
    "projects/relay-arena-vertical-slice/README.md",
    "projects/relay-arena-vertical-slice/starter/relay_arena.py",
    "projects/relay-arena-vertical-slice/reference/relay_arena.py",
    "projects/relay-arena-vertical-slice/reference/expected-contract.json",
    "projects/relay-arena-vertical-slice/reference/boundary-recovery.md",
    "projects/relay-arena-vertical-slice/tests/check_contract.py",
    "projects/relay-arena-vertical-slice/tests/check_mutants.py",
    "projects/relay-arena-vertical-slice/tests/known_bad.py",
    "reference/glossary.md",
    "reference/artifact-checklists.md",
    "reference/completion-evidence.md",
    "reference/engine-crosswalk.md",
    "reference/fixture-schemas.md",
    "reference/role-entry-map.md",
    "reference/safety-and-environment.md",
]

IGNORED_PARTS = {".git", ".guide", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".log"}


class VerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerificationError(message)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{rel(path)}: JSON을 읽을 수 없습니다: {exc}")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            rows = list(reader)
    except (OSError, csv.Error) as exc:
        fail(f"{rel(path)}: CSV를 읽을 수 없습니다: {exc}")
    if not headers or any(not header.strip() for header in headers):
        fail(f"{rel(path)}: 비어 있지 않은 header가 필요합니다")
    if len(headers) != len(set(headers)):
        fail(f"{rel(path)}: 중복 CSV header가 있습니다")
    return headers, rows


def unique(items: Iterable[Any], context: str) -> None:
    values = list(items)
    if len(values) != len(set(values)):
        fail(f"{context}: 중복 값이 있습니다")


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        fail(f"Markdown table row 형식이 아닙니다: {line!r}")
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def markdown_table_after_heading(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    lines = text.splitlines()
    try:
        heading_index = next(index for index, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        fail(f"필수 heading이 없습니다: {heading}")

    table_index: int | None = None
    for index in range(heading_index + 1, len(lines) - 1):
        stripped = lines[index].strip()
        if stripped.startswith("##"):
            break
        if stripped.startswith("|") and lines[index + 1].strip().startswith("|"):
            table_index = index
            break
    if table_index is None:
        fail(f"{heading}: Markdown table이 없습니다")

    headers = split_markdown_row(lines[table_index])
    separators = split_markdown_row(lines[table_index + 1])
    if len(headers) != len(separators) or any(
        not re.fullmatch(r":?-{3,}:?", separator) for separator in separators
    ):
        fail(f"{heading}: Markdown table separator가 잘못됐습니다")

    rows: list[list[str]] = []
    for line in lines[table_index + 2 :]:
        if not line.strip().startswith("|"):
            break
        cells = split_markdown_row(line)
        if len(cells) != len(headers):
            fail(f"{heading}: table column 수가 다릅니다")
        rows.append(cells)
    if not rows:
        fail(f"{heading}: table row가 없습니다")
    return headers, rows


def positive_int(value: Any, context: str, *, allow_zero: bool = False) -> int:
    if not isinstance(value, int) or (value < 0 if allow_zero else value <= 0):
        rule = "0 이상의 정수" if allow_zero else "양의 정수"
        fail(f"{context}: {rule}여야 합니다")
    return value


def source_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        result.append(path)
    return sorted(result, key=lambda p: rel(p))


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in source_files():
        digest.update(rel(path).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def check_required_structure() -> None:
    for item in REQUIRED_FILES:
        if not (ROOT / item).is_file():
            fail(f"필수 파일이 없습니다: {item}")
    for exercise in EXERCISES:
        base = ROOT / "exercises" / exercise
        for name in ("README.md", "inputs", "template", "reference"):
            if not (base / name).exists():
                fail(f"실습 구조가 없습니다: exercises/{exercise}/{name}")
    project = ROOT / "projects/relay-arena-vertical-slice"
    if not (project / "inputs").is_dir() or not (project / "template").is_dir():
        fail("Capstone inputs/template 디렉터리가 필요합니다")

    unexpected = []
    for name in ("build", "dist", "out", ".venv", "node_modules"):
        path = ROOT / name
        if path.exists():
            unexpected.append(name)
    if unexpected:
        fail(f"저장소 루트에 생성 부산물이 있습니다: {unexpected}")


def check_doc_sections() -> None:
    for item in CONCEPT_DOCS:
        path = ROOT / item
        text = path.read_text(encoding="utf-8")
        positions: list[int] = []
        for heading in COMMON_DOC_HEADINGS:
            count = sum(1 for line in text.splitlines() if line.strip() == heading)
            if count != 1:
                fail(f"{item}: 공통 절 {heading!r}가 정확히 한 번 필요합니다")
            positions.append(text.index(heading))
        if positions != sorted(positions):
            fail(f"{item}: 공통 절 순서가 잘못됐습니다")
        if len(text.split()) < 700:
            fail(f"{item}: 개념 문서가 지나치게 짧습니다")


def parse_markdown_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif " \"" in target:
        target = target.split(" \"", 1)[0]
    elif " '" in target:
        target = target.split(" '", 1)[0]
    return target


def markdown_targets(cell: str) -> list[str]:
    targets: list[str] = []
    for raw in MARKDOWN_LINK_RE.findall(cell):
        target = parse_markdown_target(raw)
        file_part = unquote(target.split("#", 1)[0])
        if file_part:
            targets.append(file_part)
    return targets


def validate_readme_learning_map_text(text: str) -> None:
    headers, rows = markdown_table_after_heading(text, "## 정본 진행 순서")
    expected_headers = ["순서", "문서", "관찰 예제", "직접 수행", "수정 위치", "검증", "완료 뒤 비교·다음"]
    if headers != expected_headers:
        fail(f"README 정본 진행 순서 column이 다릅니다: {headers}")

    expected_steps = [str(index) for index in range(18)] + ["참고"]
    actual_steps = [row[0] for row in rows]
    if actual_steps != expected_steps:
        fail(f"README 학습 순서가 다릅니다: {actual_steps}")

    document_targets = [target for row in rows for target in markdown_targets(row[1])]
    if document_targets != LEARNING_MAP_DOCS:
        fail(f"README 문서 순서가 다릅니다: {document_targets}")

    all_targets = [target for row in rows for cell in row for target in markdown_targets(cell)]
    for exercise in LEARNING_MAP_EXERCISES:
        if all_targets.count(exercise) != 1:
            fail(f"README 학습 지도에 실습 링크가 정확히 한 번 필요합니다: {exercise}")
    for target in (
        "examples/fixed-step-replay/README.md",
        "projects/relay-arena-vertical-slice/README.md",
    ):
        if target not in all_targets:
            fail(f"README 학습 지도에 연결이 없습니다: {target}")

    for row in rows:
        direct = row[3].strip()
        if direct and direct != "—":
            for index, name in ((4, "수정 위치"), (5, "검증"), (6, "완료 뒤 비교·다음")):
                if not row[index].strip() or row[index].strip() == "—":
                    fail(f"README {row[0]}단계의 {name}이 비어 있습니다")


def check_readme_learning_map() -> None:
    validate_readme_learning_map_text((ROOT / "README.md").read_text(encoding="utf-8"))


def implementation_label_parts(label: str) -> tuple[int, int | None]:
    parts = label.split("-", 1)
    return int(parts[0]), int(parts[1]) if len(parts) == 2 else None


def readable_source_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    for path in source_files():
        try:
            texts[rel(path)] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return texts


def implementation_index_labels(text: str, heading: str) -> list[str]:
    headers, rows = markdown_table_after_heading(text, heading)
    expected_headers = ["순서", "파일·symbol", "먼저 고정할 책임", "다음 단계가 의존하는 결과"]
    if headers != expected_headers:
        fail(f"{heading}: 구현 순서 column이 다릅니다: {headers}")

    labels: list[str] = []
    for row in rows:
        cell = row[0].strip().strip("`")
        marker = re.fullmatch(r"\[Implementation ([^\]]+)\]", cell)
        label = marker.group(1) if marker else cell
        if not VALID_IMPLEMENTATION_LABEL_RE.fullmatch(label):
            fail(f"{heading}: 잘못된 구현 순서 label {cell!r}")
        labels.append(label)
    return labels


def natural_implementation_order(labels: set[str]) -> list[str]:
    for label in labels:
        number, child = implementation_label_parts(label)
        if child is not None and str(number) not in labels:
            fail(f"Implementation {label}의 parent {number}가 없습니다")
    top_levels = sorted(
        number for number, child in map(implementation_label_parts, labels) if child is None and number > 0
    )
    if not top_levels or top_levels != list(range(1, max(top_levels) + 1)):
        fail(f"Implementation top-level 번호가 1부터 연속되지 않습니다: {top_levels}")

    order: list[str] = []
    if "0" in labels:
        order.append("0")
    for number in top_levels:
        parent = str(number)
        order.append(parent)
        children = sorted(
            child
            for top, child in map(implementation_label_parts, labels)
            if top == number and child is not None
        )
        if children and children != list(range(1, max(children) + 1)):
            fail(f"Implementation {number} child 번호가 1부터 연속되지 않습니다: {children}")
        order.extend(f"{number}-{child}" for child in children)
    return order


def validate_implementation_annotations(texts: dict[str, str]) -> None:
    labels_by_scope: dict[str, list[str]] = {name: [] for name in IMPLEMENTATION_SCOPES}

    for path, text in texts.items():
        for marker in IMPLEMENTATION_MARKER_RE.finditer(text):
            label = marker.group(1).strip()
            if not any(character.isdigit() for character in label):
                continue
            if not VALID_IMPLEMENTATION_LABEL_RE.fullmatch(label):
                fail(f"{path}: 잘못된 Implementation marker [{label}]")
            number, child = implementation_label_parts(label)
            if number == 0 and child is not None:
                fail(f"{path}: Implementation 0 child는 허용하지 않습니다")

            scope_name = next(
                (name for name, config in IMPLEMENTATION_SCOPES.items() if path in config["files"]),
                None,
            )
            if scope_name is None:
                fail(f"{path}: annotation 허용 scope 밖의 [Implementation {label}]")

            line_start = text.rfind("\n", 0, marker.start()) + 1
            line_end = text.find("\n", marker.end())
            line = text[line_start : line_end if line_end >= 0 else len(text)].strip()
            if path.endswith(".py"):
                if not line.startswith(f"# [Implementation {label}]"):
                    fail(f"{path}: Python marker는 독립 comment anchor여야 합니다: {label}")
            elif path == IMPLEMENTATION_SCOPES[scope_name]["index"]:
                if not line.startswith(f"| [Implementation {label}] |"):
                    fail(f"{path}: README sidecar marker는 구현 순서 표 첫 cell에 있어야 합니다: {label}")
            else:
                fail(f"{path}: 허용되지 않은 annotation anchor 형식입니다")
            labels_by_scope[scope_name].append(label)

    for scope_name, config in IMPLEMENTATION_SCOPES.items():
        labels = labels_by_scope[scope_name]
        if len(labels) != len(set(labels)):
            fail(f"{scope_name}: 중복 Implementation anchor가 있습니다")
        label_set = set(labels)
        order = natural_implementation_order(label_set)
        index_text = texts.get(config["index"])
        if index_text is None:
            fail(f"{scope_name}: implementation index README를 읽을 수 없습니다")
        index_labels = implementation_index_labels(index_text, config["heading"])
        if index_labels != order or set(index_labels) != label_set:
            fail(
                f"{scope_name}: README index와 authoritative anchor가 다릅니다: "
                f"index={index_labels}, anchors={order}"
            )


def check_implementation_annotations() -> None:
    validate_implementation_annotations(readable_source_texts())


def check_markdown_links() -> None:
    markdown = sorted(ROOT.rglob("*.md"), key=lambda p: rel(p))
    if len(markdown) < 40:
        fail("Markdown 문서 수가 예상보다 적습니다")
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        for raw in MARKDOWN_LINK_RE.findall(text):
            target = parse_markdown_target(raw)
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            file_part = unquote(target.split("#", 1)[0])
            if not file_part:
                continue
            resolved = (path.parent / file_part).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"{rel(path)}: 저장소 밖 상대 링크 {target}")
            if not resolved.exists():
                fail(f"{rel(path)}: 깨진 상대 링크 {target}")


def check_all_json_and_csv() -> None:
    files = source_files()
    json_files = [path for path in files if path.suffix == ".json"]
    csv_files = [path for path in files if path.suffix == ".csv"]
    if len(json_files) < 25 or len(csv_files) < 10:
        fail("fixture 파일 수가 예상보다 적습니다")
    for path in json_files:
        load_json(path)
    for path in csv_files:
        read_csv(path)


def check_dependency_graph(assets: list[dict[str, Any]], context: str) -> set[str]:
    ids = [asset.get("id") for asset in assets]
    if any(not isinstance(item, str) or not item for item in ids):
        fail(f"{context}: 모든 asset id가 필요합니다")
    unique(ids, f"{context} asset id")
    id_set = set(ids)
    graph: dict[str, list[str]] = {}
    for asset in assets:
        deps = asset.get("dependencies")
        if not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps):
            fail(f"{context}: {asset['id']} dependencies가 잘못됐습니다")
        unknown = sorted(set(deps) - id_set)
        if unknown:
            fail(f"{context}: {asset['id']}의 알 수 없는 dependency {unknown}")
        graph[asset["id"]] = deps

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in visiting:
            fail(f"{context}: asset dependency cycle {' -> '.join(stack + [node])}")
        if node in visited:
            return
        visiting.add(node)
        for dep in graph[node]:
            visit(dep, stack + [node])
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node, [])
    return id_set


def check_exercise_fixtures() -> None:
    # 01 time
    time_base = ROOT / "exercises/01-time-step-analysis/inputs"
    policy = load_json(time_base / "time-policy.json")
    positive_int(policy.get("fixed_step_us"), "time-policy.fixed_step_us")
    positive_int(policy.get("max_steps_per_render_frame"), "time-policy.max_steps_per_render_frame")
    clocks = policy.get("clocks")
    if not isinstance(clocks, list) or len(clocks) < 4:
        fail("time-policy에는 최소 네 clock이 필요합니다")
    unique((clock.get("id") for clock in clocks), "time-policy clock id")

    frames_data = load_json(time_base / "frame-trace.json")
    frames = frames_data.get("frames")
    if not isinstance(frames, list) or not frames:
        fail("frame-trace.frames가 필요합니다")
    frame_ids = [frame.get("frame") for frame in frames]
    unique(frame_ids, "frame-trace frame")
    frame_set = set(frame_ids)
    for frame in frames:
        positive_int(frame.get("real_delta_us"), "frame real_delta_us", allow_zero=True)
        if not isinstance(frame.get("pause_reasons"), list):
            fail("frame pause_reasons는 배열이어야 합니다")

    input_events = load_json(time_base / "input-events.json").get("events")
    if not isinstance(input_events, list):
        fail("input-events.events가 필요합니다")
    unique((event.get("sequence") for event in input_events), "time input sequence")
    for event in input_events:
        if event.get("arrival_frame") not in frame_set:
            fail("input event가 알 수 없는 frame을 참조합니다")

    # 02 input
    input_base = ROOT / "exercises/02-input-command-contract/inputs"
    action_map = load_json(input_base / "action-map.json")
    actions = action_map.get("actions")
    if not isinstance(actions, list):
        fail("action-map.actions가 필요합니다")
    action_ids = {item.get("id") for item in actions}
    if None in action_ids:
        fail("action id가 필요합니다")
    unique(action_ids, "action id")
    timeline = load_json(input_base / "context-timeline.json")
    users = timeline.get("local_users")
    if not isinstance(users, list):
        fail("context timeline local_users가 필요합니다")
    devices: dict[str, str] = {}
    for user in users:
        for device in user.get("devices", []):
            if device in devices:
                fail(f"device {device}가 여러 local user에 연결됐습니다")
            devices[device] = user.get("local_user")
    segments = timeline.get("segments")
    if not isinstance(segments, list) or not segments:
        fail("context timeline segments가 필요합니다")
    last_end = -1
    for segment in segments:
        start, end = segment.get("from_ms"), segment.get("to_ms")
        if not isinstance(start, int) or not isinstance(end, int) or start < last_end or end <= start:
            fail("context timeline interval이 겹치거나 잘못됐습니다")
        last_end = end
    device_events = load_json(input_base / "device-events.json").get("events")
    if not isinstance(device_events, list):
        fail("device-events.events가 필요합니다")
    unique((event.get("sequence") for event in device_events), "device event sequence")
    for event in device_events:
        if event.get("device") not in devices:
            fail(f"알 수 없는 device event: {event.get('device')}")

    # 03 lifecycle
    life_base = ROOT / "exercises/03-world-lifecycle-review/inputs"
    life_events = load_json(life_base / "lifecycle-events.json").get("events")
    if not isinstance(life_events, list):
        fail("lifecycle events가 필요합니다")
    unique((event.get("index") for event in life_events), "lifecycle event index")
    if [e.get("index") for e in life_events] != sorted(e.get("index") for e in life_events):
        fail("lifecycle event index가 정렬돼야 합니다")
    references = load_json(life_base / "references.json").get("edges")
    if not isinstance(references, list) or not references:
        fail("lifecycle reference edges가 필요합니다")
    for edge in references:
        if not all(isinstance(edge.get(key), str) and edge.get(key) for key in ("from", "to", "kind", "purpose")):
            fail("reference edge의 from/to/kind/purpose가 필요합니다")

    # 04 assets
    asset_base = ROOT / "exercises/04-asset-loading-plan/inputs"
    manifest = load_json(asset_base / "asset-manifest.json")
    asset_ids = check_dependency_graph(manifest.get("assets", []), "exercise asset manifest")
    scenarios = load_json(asset_base / "load-scenarios.json")
    for scenario in scenarios.get("scenarios", []):
        unknown = set(scenario.get("requested", [])) - asset_ids
        if unknown:
            fail(f"load scenario가 알 수 없는 asset을 참조합니다: {sorted(unknown)}")
        unknown_missing = set(scenario.get("missing", [])) - asset_ids
        if unknown_missing:
            fail(f"load scenario missing에 알 수 없는 asset이 있습니다: {sorted(unknown_missing)}")
    for gate_assets in scenarios.get("gates", {}).values():
        unknown = set(gate_assets) - asset_ids
        if unknown:
            fail(f"load gate가 알 수 없는 asset을 참조합니다: {sorted(unknown)}")
    budgets = load_json(asset_base / "memory-budgets.json")
    targets = budgets.get("targets")
    if not isinstance(targets, list) or len(targets) < 2:
        fail("두 개 이상의 asset target budget이 필요합니다")

    # 05 saves and replay
    save_base = ROOT / "exercises/05-save-and-replay-migration/inputs"
    save_v1 = load_json(save_base / "save-v1.json")
    save_v2 = load_json(save_base / "save-v2-schema.json")
    if save_v1.get("schema_version") != 1 or save_v2.get("schema_version") != 2:
        fail("save exercise schema version은 v1/v2여야 합니다")
    replay_a = load_json(save_base / "replay-a.json")
    replay_b = load_json(save_base / "replay-b.json")
    for name, replay in (("a", replay_a), ("b", replay_b)):
        commands = replay.get("commands")
        checkpoints = replay.get("checkpoints")
        if not isinstance(commands, list) or not isinstance(checkpoints, list):
            fail(f"replay-{name} command/checkpoint가 필요합니다")
        unique((item.get("sequence") for item in commands), f"replay-{name} command sequence")
        ticks = [item.get("tick") for item in checkpoints]
        if ticks != sorted(ticks) or len(ticks) != len(set(ticks)):
            fail(f"replay-{name} checkpoint tick이 정렬·유일해야 합니다")
    if replay_a["commands"] == replay_b["commands"]:
        fail("replay known-bad variant가 실제 command를 바꾸지 않았습니다")

    # 06 network authority
    network_base = ROOT / "exercises/06-authority-and-latency/inputs"
    authority = load_json(network_base / "authority-model.json")
    actor_ids = {actor.get("id") for actor in authority.get("actors", [])}
    if "server" not in actor_ids or len(actor_ids) < 3:
        fail("authority model에는 server와 두 client가 필요합니다")
    player_ids = {actor.get("owns_player") for actor in authority.get("actors", []) if actor.get("owns_player")}
    session = load_json(network_base / "session-trace.json")
    unique((event.get("index") for event in session.get("events", [])), "network event index")
    for event in session.get("events", []):
        if event.get("source") not in actor_ids:
            fail(f"network trace의 알 수 없는 source {event.get('source')}")
        if event.get("player") is not None and event.get("player") not in player_ids:
            fail(f"network trace의 알 수 없는 player {event.get('player')}")
    faults = load_json(network_base / "network-faults.json")
    if len(faults.get("required_cases", [])) < 5:
        fail("network required fault case가 부족합니다")

    # 07 performance
    perf_base = ROOT / "exercises/07-performance-budget-review/inputs"
    target_profile = load_json(perf_base / "target-profile.json")
    budgets = target_profile.get("budgets")
    if not isinstance(budgets, dict) or any(not isinstance(value, (int, float)) or value <= 0 for value in budgets.values()):
        fail("target profile budget이 잘못됐습니다")
    _, frame_rows = read_csv(perf_base / "frame-samples.csv")
    _, memory_rows = read_csv(perf_base / "memory-samples.csv")
    _, load_rows = read_csv(perf_base / "load-samples.csv")
    if len(frame_rows) < 10 or len(memory_rows) < 5 or len(load_rows) < 4:
        fail("performance sample이 너무 적습니다")
    for row in frame_rows:
        if float(row["frame_ms"]) <= 0:
            fail("frame sample이 양수가 아닙니다")

    # 08 release
    release_base = ROOT / "exercises/08-release-readiness/inputs"
    build = load_json(release_base / "build-manifest.json")
    evidence = load_json(release_base / "release-evidence.json")
    if build.get("candidate") != evidence.get("candidate"):
        fail("release candidate identity가 일치하지 않습니다")
    statuses = {item.get("status") for item in evidence.get("evidence", [])}
    if not {"pass", "fail", "unknown"}.issubset(statuses):
        fail("release fixture는 pass/fail/unknown을 모두 포함해야 합니다")
    _, platform_rows = read_csv(release_base / "platform-checks.csv")
    if not any(row.get("status") in {"unknown", "stale", "fail"} for row in platform_rows):
        fail("release platform fixture에 미해결 상태가 필요합니다")


def profile_a_artifacts(text: str, heading: str) -> set[str]:
    headers, rows = markdown_table_after_heading(text, heading)
    if headers[:2] not in (["번호", "제출 파일"], ["번호", "필수 제출 파일"]):
        fail(f"{heading}: Profile A table column이 다릅니다: {headers}")
    numbers = [row[0] for row in rows]
    if numbers != [str(index) for index in range(1, 14)]:
        fail(f"{heading}: 필수 제출 번호가 1~13이 아닙니다: {numbers}")

    artifacts: set[str] = set()
    for row in rows:
        targets = markdown_targets(row[1])
        if targets:
            artifacts.add(Path(targets[0]).name)
        else:
            artifacts.add(row[1].strip().strip("`"))
    return artifacts


def validate_capstone_artifact_sets(
    template_required: set[str],
    template_optional: set[str],
    reference_artifacts: set[str],
) -> None:
    if len(CAPSTONE_REQUIRED_ARTIFACTS) != 13:
        fail("Capstone required artifact 계약은 정확히 13개여야 합니다")
    if CAPSTONE_REQUIRED_ARTIFACTS & CAPSTONE_OPTIONAL_ARTIFACTS:
        fail("Capstone required와 optional artifact가 겹칩니다")
    if template_required != CAPSTONE_REQUIRED_ARTIFACTS:
        fail(
            "Capstone 필수 template set이 다릅니다: "
            f"{sorted(CAPSTONE_REQUIRED_ARTIFACTS ^ template_required)}"
        )
    if template_optional != CAPSTONE_OPTIONAL_ARTIFACTS:
        fail(
            "Capstone 선택 template set이 다릅니다: "
            f"{sorted(CAPSTONE_OPTIONAL_ARTIFACTS ^ template_optional)}"
        )
    if reference_artifacts != CAPSTONE_REQUIRED_ARTIFACTS:
        fail(
            "Capstone 필수 reference artifact set이 다릅니다: "
            f"{sorted(CAPSTONE_REQUIRED_ARTIFACTS ^ reference_artifacts)}"
        )


def check_capstone_fixtures() -> None:
    base = ROOT / "projects/relay-arena-vertical-slice"
    inputs = base / "inputs"
    templates = base / "template"
    optional_templates = templates / "optional"
    if not optional_templates.is_dir():
        fail("Capstone optional template 디렉터리가 필요합니다")
    if {path.name for path in templates.iterdir() if path.is_dir()} != {"optional"}:
        fail("Capstone template에는 optional 하위 디렉터리만 허용됩니다")
    actual_templates = {path.name for path in templates.iterdir() if path.is_file()}
    actual_optional = {path.name for path in optional_templates.iterdir() if path.is_file()}
    reference_artifacts = base / "reference/artifacts"
    actual_artifacts = {path.name for path in reference_artifacts.iterdir() if path.is_file()}
    validate_capstone_artifact_sets(actual_templates, actual_optional, actual_artifacts)

    optional_text = (optional_templates / "ai-and-navigation.md").read_text(encoding="utf-8")
    if "선택 산출물" not in optional_text or "필수 13개" not in optional_text:
        fail("AI template 자체에 선택 산출물 계약이 필요합니다")

    project_artifacts = profile_a_artifacts(
        (base / "README.md").read_text(encoding="utf-8"),
        "## 필수 Profile A — 정확히 13개 제출 파일",
    )
    document_artifacts = profile_a_artifacts(
        (ROOT / "docs/17-capstone.md").read_text(encoding="utf-8"),
        "## 필수 Profile A — 정확히 13개 설계·검토 산출물",
    )
    if project_artifacts != CAPSTONE_REQUIRED_ARTIFACTS or document_artifacts != CAPSTONE_REQUIRED_ARTIFACTS:
        fail("Capstone README와 docs/17의 필수 13개 표가 artifact contract와 다릅니다")

    _, req_rows = read_csv(inputs / "requirements.csv")
    req_ids = [row.get("requirement_id") for row in req_rows]
    unique(req_ids, "Capstone requirement id")
    if len(req_ids) < 10:
        fail("Capstone requirement가 너무 적습니다")
    req_set = set(req_ids)

    runtime = load_json(inputs / "runtime-events.json")
    events = runtime.get("events")
    if not isinstance(events, list) or len(events) < 15:
        fail("Capstone runtime event가 부족합니다")
    unique((event.get("index") for event in events), "Capstone runtime index")
    generations = {event.get("generation") for event in events}
    if len(generations) < 3:
        fail("Capstone runtime fixture가 여러 generation을 포함해야 합니다")

    rules = load_json(inputs / "gameplay-rules.json")
    command_kinds = {item.get("kind") for item in rules.get("commands", [])}
    if command_kinds != {"move", "dash", "interact"}:
        fail("Capstone gameplay command set이 잘못됐습니다")
    if len(rules.get("invariants", [])) < 4:
        fail("Capstone gameplay invariant가 부족합니다")

    content = load_json(inputs / "content-manifest.json")
    asset_ids = check_dependency_graph(content.get("assets", []), "Capstone content manifest")
    for gate, ids in content.get("gates", {}).items():
        unknown = set(ids) - asset_ids
        if unknown:
            fail(f"Capstone gate {gate}의 알 수 없는 asset {sorted(unknown)}")
    if len(content.get("target_budgets", {})) < 2:
        fail("Capstone target budget이 부족합니다")

    save1 = load_json(inputs / "save-v1.json")
    save2 = load_json(inputs / "save-v2-contract.json")
    if save1.get("schema_version") != 1 or save2.get("schema_version") != 2:
        fail("Capstone save version은 1→2여야 합니다")

    replay = load_json(inputs / "replay-trace.json")
    commands = replay.get("commands")
    checkpoints = replay.get("checkpoints")
    if not isinstance(commands, list) or not isinstance(checkpoints, list):
        fail("Capstone replay command/checkpoint가 필요합니다")
    unique((item.get("sequence") for item in commands), "Capstone replay command sequence")
    checkpoint_ticks = [item.get("tick") for item in checkpoints]
    if checkpoint_ticks != sorted(checkpoint_ticks):
        fail("Capstone replay checkpoint가 정렬돼야 합니다")

    network = load_json(inputs / "network-session.json")
    unique((event.get("index") for event in network.get("events", [])), "Capstone network event index")
    if not all(key in network.get("fault_profile", {}) for key in ("latency_ms", "loss_percent", "reorder_percent")):
        fail("Capstone network fault profile이 불완전합니다")

    profile = load_json(inputs / "target-profile.json")
    if profile.get("target") not in content.get("target_budgets", {}):
        fail("Capstone profile target이 content budget에 없습니다")
    if profile.get("content") != content.get("content_version"):
        fail("Capstone profile content identity가 manifest와 다릅니다")

    release = load_json(inputs / "release-evidence.json")
    for item in release.get("evidence", []):
        unknown = set(item.get("requirements", [])) - req_set
        if unknown:
            fail(f"release evidence {item.get('id')}의 알 수 없는 requirement {sorted(unknown)}")
    covered = {req for item in release.get("evidence", []) for req in item.get("requirements", [])}
    if len(covered) < 8:
        fail("Capstone release evidence의 requirement coverage가 부족합니다")


def check_workspace_generator() -> None:
    copied_roots = []
    for exercise in EXERCISES:
        base = ROOT / "exercises" / exercise
        copied_roots.extend((base / "inputs", base / "template"))
    project = ROOT / "projects/relay-arena-vertical-slice"
    copied_roots.extend((project / "inputs", project / "template", project / "starter"))
    for copied_root in copied_roots:
        for path in (copied_root, *copied_root.rglob("*")):
            if path.is_symlink():
                fail(f"workspace 복사 source에 symlink가 있습니다: {rel(path)}")

    with tempfile.TemporaryDirectory(prefix="game-guide-workspace-") as raw:
        parent = Path(raw)
        destination = parent / "learner"
        command = [sys.executable, str(ROOT / "scripts/new_workspace.py"), str(destination)]
        created = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        if created.returncode != 0 or "WORKSPACE_CREATED" not in created.stdout:
            fail(f"learner workspace 생성 실패:\n{created.stdout}\n{created.stderr}")

        workspace_readme = (destination / "README.md").read_text(encoding="utf-8")
        if "exactly 13 required top-level submission files" not in workspace_readme:
            fail("생성된 workspace README에 필수 13개 계약이 없습니다")

        exercise_root = destination / "exercises"
        actual_exercises = {path.name for path in exercise_root.iterdir() if path.is_dir()}
        if actual_exercises != set(EXERCISES):
            fail("생성된 workspace의 exercise set이 다릅니다")
        if any(not (exercise_root / exercise / "submission").is_dir() for exercise in EXERCISES):
            fail("생성된 workspace에 exercise submission이 없습니다")

        capstone = destination / "relay-arena-vertical-slice"
        submission = capstone / "submission"
        required = {path.name for path in submission.iterdir() if path.is_file()}
        optional = {path.name for path in (submission / "optional").iterdir() if path.is_file()}
        validate_capstone_artifact_sets(required, optional, CAPSTONE_REQUIRED_ARTIFACTS)
        if not (capstone / "starter/relay_arena.py").is_file():
            fail("생성된 workspace에 Capstone starter가 없습니다")
        if any(path.is_symlink() for path in destination.rglob("*")):
            fail("생성된 workspace에 symlink가 있습니다")

        repeated = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        if repeated.returncode == 0:
            fail("workspace 생성기가 기존 destination을 거부하지 못했습니다")
        relative = subprocess.run(
            [sys.executable, str(ROOT / "scripts/new_workspace.py"), "relative-workspace"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if relative.returncode == 0:
            fail("workspace 생성기가 상대 경로를 거부하지 못했습니다")

        link_target = parent / "link-target"
        link_target.mkdir()
        link = parent / "workspace-link"
        link.symlink_to(link_target, target_is_directory=True)
        linked = subprocess.run(
            [sys.executable, str(ROOT / "scripts/new_workspace.py"), str(link)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if linked.returncode == 0:
            fail("workspace 생성기가 symlink destination을 거부하지 못했습니다")


def run_example(*, expected: Path | None = None, should_succeed: bool = True) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(EXAMPLE / "sim.py"), "--verify"]
    if expected is not None:
        command += ["--expected", str(expected)]
    result = subprocess.run(command, cwd=EXAMPLE, text=True, capture_output=True, check=False)
    if should_succeed and result.returncode != 0:
        fail(f"fixed-step example 실패:\n{result.stdout}\n{result.stderr}")
    if not should_succeed and result.returncode == 0:
        fail("fixed-step meta-check가 잘못된 expected hash를 거부하지 못했습니다")
    return result


def check_example_and_meta(*, meta: bool) -> None:
    run_example()
    if not meta:
        return
    expected = load_json(EXAMPLE / "expected-state.json")
    current_hash = expected.get("canonical_state_hash")
    if not isinstance(current_hash, str) or len(current_hash) != 64:
        fail("example expected hash 형식이 잘못됐습니다")
    expected["canonical_state_hash"] = ("0" if current_hash[0] != "0" else "1") + current_hash[1:]
    with tempfile.TemporaryDirectory(prefix="game-guide-meta-") as temp_dir:
        mutated = Path(temp_dir) / "expected-state.json"
        mutated.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run_example(expected=mutated, should_succeed=False)


def check_prepare_marker() -> None:
    marker_path = ROOT / ".guide/game-development/prepared.json"
    if not marker_path.is_file():
        fail("먼저 ./prepare.sh를 실행하십시오")
    marker = load_json(marker_path)
    current = source_fingerprint()
    if marker.get("source_sha256") != current:
        fail("prepare 이후 source가 변경됐습니다. ./prepare.sh를 다시 실행하십시오")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if head.returncode == 0 and marker.get("git_head") != head.stdout.strip():
        fail("prepare marker의 git HEAD가 현재 HEAD와 다릅니다. ./prepare.sh를 다시 실행하십시오")


def run_required_check(command: list[str], context: str) -> None:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        fail(f"{context} 실패:\n{result.stdout}\n{result.stderr}")
    if result.stdout.strip():
        print(result.stdout.strip())


def check_reference_starter_and_mutants() -> None:
    run_required_check(
        [sys.executable, str(ROOT / "scripts/check_submission.py"), "--self-test"],
        "단계 실습 reference/template/mutant matrix",
    )
    run_required_check(
        [
            sys.executable,
            str(ROOT / "projects/relay-arena-vertical-slice/tests/check_mutants.py"),
        ],
        "Capstone reference/starter/mutant matrix",
    )


def expect_policy_failure(callback: Callable[[], None], context: str) -> None:
    try:
        callback()
    except VerificationError:
        return
    fail(f"repository policy mutant를 거부하지 못했습니다: {context}")


def implementation_marker(label: str) -> str:
    return f"[Implementation {label}]"


def check_repository_policy_mutants() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    validate_readme_learning_map_text(readme)
    prefix, learning_section = readme.split("## 정본 진행 순서", 1)

    missing_doc = prefix + "## 정본 진행 순서" + learning_section.replace(
        "(docs/03-input-command-camera-and-ui.md)",
        "(docs/99-missing.md)",
        1,
    )
    expect_policy_failure(lambda: validate_readme_learning_map_text(missing_doc), "README document missing")

    swapped_section = learning_section.replace(
        "(docs/02-game-loop-time-and-frames.md)", "(__DOC_TWO__)", 1
    ).replace(
        "(docs/03-input-command-camera-and-ui.md)",
        "(docs/02-game-loop-time-and-frames.md)",
        1,
    ).replace("(__DOC_TWO__)", "(docs/03-input-command-camera-and-ui.md)", 1)
    expect_policy_failure(
        lambda: validate_readme_learning_map_text(prefix + "## 정본 진행 순서" + swapped_section),
        "README document order swapped",
    )

    missing_exercise = prefix + "## 정본 진행 순서" + learning_section.replace(
        "(exercises/04-asset-loading-plan/README.md)",
        "(exercises/99-missing/README.md)",
        1,
    )
    expect_policy_failure(
        lambda: validate_readme_learning_map_text(missing_exercise),
        "README exercise connection missing",
    )

    missing_location = prefix + "## 정본 진행 순서" + learning_section.replace(
        "| 실습 01 `submission/*`; `$CAP/submission/time-and-input-contract.md` |",
        "| — |",
        1,
    )
    expect_policy_failure(
        lambda: validate_readme_learning_map_text(missing_location),
        "README learner location missing",
    )

    missing_required = set(CAPSTONE_REQUIRED_ARTIFACTS)
    missing_required.remove("change-plan.md")
    expect_policy_failure(
        lambda: validate_capstone_artifact_sets(
            missing_required,
            set(CAPSTONE_OPTIONAL_ARTIFACTS),
            set(CAPSTONE_REQUIRED_ARTIFACTS),
        ),
        "Capstone required template missing",
    )
    expect_policy_failure(
        lambda: validate_capstone_artifact_sets(
            set(CAPSTONE_REQUIRED_ARTIFACTS),
            set(),
            set(CAPSTONE_REQUIRED_ARTIFACTS),
        ),
        "Capstone optional template missing",
    )
    expect_policy_failure(
        lambda: validate_capstone_artifact_sets(
            set(CAPSTONE_REQUIRED_ARTIFACTS),
            set(CAPSTONE_OPTIONAL_ARTIFACTS),
            set(CAPSTONE_REQUIRED_ARTIFACTS | CAPSTONE_OPTIONAL_ARTIFACTS),
        ),
        "Capstone optional artifact treated as required reference",
    )

    texts = readable_source_texts()
    validate_implementation_annotations(texts)
    example_source = "examples/fixed-step-replay/sim.py"
    duplicate = dict(texts)
    duplicate[example_source] += f"\n# {implementation_marker('1')} duplicate\n"
    expect_policy_failure(
        lambda: validate_implementation_annotations(duplicate),
        "duplicate annotation",
    )

    top_gap = dict(texts)
    top_gap[example_source] = top_gap[example_source].replace(
        implementation_marker("4"), implementation_marker("8"), 1
    )
    expect_policy_failure(
        lambda: validate_implementation_annotations(top_gap),
        "top-level annotation gap",
    )

    orphan = dict(texts)
    orphan[example_source] = orphan[example_source].replace(
        implementation_marker("3-1"), implementation_marker("8-1"), 1
    )
    expect_policy_failure(
        lambda: validate_implementation_annotations(orphan),
        "annotation child without parent",
    )

    invalid_zero_child = dict(texts)
    invalid_zero_child[example_source] += f"\n# {implementation_marker('0-1')} invalid\n"
    expect_policy_failure(
        lambda: validate_implementation_annotations(invalid_zero_child),
        "Implementation 0 child",
    )

    starter_path = "projects/relay-arena-vertical-slice/starter/relay_arena.py"
    forbidden = dict(texts)
    forbidden[starter_path] = (
        forbidden[starter_path] + f"\n# {implementation_marker('1')} leaked answer order\n"
    )
    expect_policy_failure(
        lambda: validate_implementation_annotations(forbidden),
        "starter annotation leakage",
    )

    index_path = "examples/fixed-step-replay/README.md"
    mismatched_index = dict(texts)
    mismatched_index[index_path] = mismatched_index[index_path].replace(
        "| 7 | `main()` |", "| 8 | `main()` |", 1
    )
    expect_policy_failure(
        lambda: validate_implementation_annotations(mismatched_index),
        "README implementation index mismatch",
    )


def run_checks(*, quick: bool, fixtures_only: bool, require_marker: bool) -> None:
    if require_marker:
        check_prepare_marker()
    before = source_fingerprint()

    if fixtures_only:
        check_all_json_and_csv()
        check_exercise_fixtures()
        check_capstone_fixtures()
    else:
        check_required_structure()
        check_doc_sections()
        check_readme_learning_map()
        check_markdown_links()
        check_implementation_annotations()
        check_all_json_and_csv()
        check_exercise_fixtures()
        check_capstone_fixtures()
        check_workspace_generator()
        check_example_and_meta(meta=not quick)
        if not quick:
            check_reference_starter_and_mutants()
            check_repository_policy_mutants()

    after = source_fingerprint()
    if before != after:
        fail("검증 중 source tree가 변경됐습니다")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the game-development guide")
    parser.add_argument("--quick", action="store_true", help="skip verifier meta-test")
    parser.add_argument("--fixtures-only", action="store_true")
    parser.add_argument("--require-marker", action="store_true")
    parser.add_argument("--policy-meta", action="store_true")
    args = parser.parse_args()

    if args.policy_meta:
        if args.quick or args.fixtures_only or args.require_marker:
            parser.error("--policy-meta cannot be combined with other modes")
        try:
            check_readme_learning_map()
            check_implementation_annotations()
            check_capstone_fixtures()
            check_repository_policy_mutants()
        except VerificationError as exc:
            print(f"VERIFY_ERROR: {exc}", file=sys.stderr)
            return 1
        print("POLICY_META_OK mutants=13")
        return 0

    try:
        run_checks(quick=args.quick, fixtures_only=args.fixtures_only, require_marker=args.require_marker)
    except VerificationError as exc:
        print(f"VERIFY_ERROR: {exc}", file=sys.stderr)
        return 1

    files = source_files()
    markdown_count = sum(path.suffix == ".md" for path in files)
    json_count = sum(path.suffix == ".json" for path in files)
    csv_count = sum(path.suffix == ".csv" for path in files)
    mode = "fixtures" if args.fixtures_only else ("quick" if args.quick else "full")
    print(f"VERIFY_OK mode={mode} markdown={markdown_count} json={json_count} csv={csv_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
