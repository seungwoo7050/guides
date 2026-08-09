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
from typing import Any, Iterable
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


def check_capstone_fixtures() -> None:
    base = ROOT / "projects/relay-arena-vertical-slice"
    inputs = base / "inputs"
    templates = base / "template"
    expected_templates = {
        "runtime-state-map.md",
        "time-and-input-contract.md",
        "state-ownership.csv",
        "world-and-asset-plan.md",
        "gameplay-rules.md",
        "movement-and-space.md",
        "presentation-contract.md",
        "save-and-replay.md",
        "ai-and-navigation.md",
        "authority-and-latency.md",
        "test-and-observability-plan.md",
        "performance-and-release.md",
        "traceability-matrix.csv",
        "change-plan.md",
    }
    actual_templates = {path.name for path in templates.iterdir() if path.is_file()}
    if actual_templates != expected_templates:
        fail(f"Capstone template set이 다릅니다: {sorted(expected_templates ^ actual_templates)}")

    reference_artifacts = base / "reference/artifacts"
    actual_artifacts = {path.name for path in reference_artifacts.iterdir() if path.is_file()}
    if actual_artifacts != CAPSTONE_REQUIRED_ARTIFACTS:
        fail(
            "Capstone 필수 reference artifact set이 다릅니다: "
            f"{sorted(CAPSTONE_REQUIRED_ARTIFACTS ^ actual_artifacts)}"
        )

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
        check_markdown_links()
        check_all_json_and_csv()
        check_exercise_fixtures()
        check_capstone_fixtures()
        check_example_and_meta(meta=not quick)
        if not quick:
            check_reference_starter_and_mutants()

    after = source_fingerprint()
    if before != after:
        fail("검증 중 source tree가 변경됐습니다")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the game-development guide")
    parser.add_argument("--quick", action="store_true", help="skip verifier meta-test")
    parser.add_argument("--fixtures-only", action="store_true")
    parser.add_argument("--require-marker", action="store_true")
    args = parser.parse_args()

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
