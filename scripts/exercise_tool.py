#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "exercises/manifest.json"
CHECK_TIMEOUT_SECONDS = 10


class ExerciseError(RuntimeError):
    pass


class WorkspaceInterrupted(ExerciseError):
    pass


_WORKSPACE_HOLD_HOOK = None
_SIGNAL_INTERRUPTED = False


def reject_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise ExerciseError(f"symlink는 허용하지 않습니다: {root}")
    if not root.exists():
        return
    if not root.is_dir() and not root.is_file():
        raise ExerciseError(f"regular file/directory가 아닌 항목은 허용하지 않습니다: {root}")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ExerciseError(f"symlink는 허용하지 않습니다: {path}")
        if not path.is_dir() and not path.is_file():
            raise ExerciseError(f"regular file/directory가 아닌 항목은 허용하지 않습니다: {path}")


def contained_path(
    base: Path,
    raw: object,
    *,
    label: str,
    expect: str | None = None,
) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ExerciseError(f"{label} 경로가 비어 있습니다.")
    if raw != raw.strip() or "\\" in raw or "\x00" in raw:
        raise ExerciseError(f"{label} 경로 spelling이 잘못됐습니다: {raw!r}")
    raw_parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise ExerciseError(f"{label} 경로에 빈/. /.. component를 사용할 수 없습니다: {raw!r}")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or relative.as_posix() != raw:
        raise ExerciseError(f"{label} 경로는 안전한 상대 경로여야 합니다: {raw!r}")
    candidate = base.joinpath(*relative.parts)
    reject_symlinks(candidate)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise ExerciseError(f"{label} 경로가 허용 범위를 벗어납니다: {raw!r}") from exc
    if expect == "dir" and not candidate.is_dir():
        raise ExerciseError(f"{label} directory가 없습니다: {raw}")
    if expect == "file" and not candidate.is_file():
        raise ExerciseError(f"{label} file이 없습니다: {raw}")
    return candidate


def load_items() -> dict[str, dict]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ExerciseError("exercise manifest version은 1이어야 합니다.")
    raw_items = data.get("exercises")
    if not isinstance(raw_items, list) or not raw_items:
        raise ExerciseError("manifest exercises는 비어 있지 않은 배열이어야 합니다.")
    items: dict[str, dict] = {}
    success_markers: set[str] = set()
    for item in raw_items:
        if not isinstance(item, dict):
            raise ExerciseError("manifest exercise 항목은 object여야 합니다.")
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or not raw_path.startswith("exercises/"):
            raise ExerciseError(f"잘못된 exercise path: {raw_path!r}")
        if raw_path in items:
            raise ExerciseError(f"중복 exercise path: {raw_path}")
        kind = item.get("kind")
        if kind not in {"code", "design", "capstone"}:
            raise ExerciseError(f"알 수 없는 exercise kind: {kind!r}")
        path = contained_path(ROOT, raw_path, label="exercise", expect="dir")
        if kind in {"code", "design"}:
            contained_path(path, item.get("checker"), label="checker", expect="file")
            semantic = item.get("semantic_failure")
            if not isinstance(semantic, str) or not semantic.startswith("GUIDE_SEMANTIC:"):
                raise ExerciseError(f"semantic_failure가 잘못됐습니다: {raw_path}")
            success = item.get("success_marker")
            if not isinstance(success, str) or not success.startswith("OK ") or "\n" in success:
                raise ExerciseError(f"success_marker가 잘못됐습니다: {raw_path}")
            if success in success_markers:
                raise ExerciseError(f"success_marker가 중복됩니다: {success}")
            success_markers.add(success)
            known_bad = item.get("known_bad")
            if not isinstance(known_bad, list) or not known_bad:
                raise ExerciseError(f"known_bad fixture가 없습니다: {raw_path}")
            if not all(isinstance(fixture, str) for fixture in known_bad):
                raise ExerciseError(f"known_bad path는 string이어야 합니다: {raw_path}")
            if len(known_bad) != len(set(known_bad)):
                raise ExerciseError(f"known_bad fixture가 중복됩니다: {raw_path}")
            for fixture in known_bad:
                if not isinstance(fixture, str) or not fixture.startswith("known_bad/"):
                    raise ExerciseError(f"known_bad path는 known_bad/ 아래여야 합니다: {fixture!r}")
                contained_path(path, fixture, label="known_bad", expect="dir")
        items[raw_path] = item
    return items


def resolve_registered(raw: str, items: dict[str, dict]) -> tuple[str, Path, dict]:
    candidate = raw.strip()
    if any(part in {"", ".", ".."} for part in candidate.split("/")):
        raise ExerciseError(f"exercise path에 빈/. /.. component를 사용할 수 없습니다: {raw!r}")
    if candidate not in items:
        raise ExerciseError(f"manifest에 등록되지 않은 exercise입니다: {raw}")
    path = contained_path(ROOT, candidate, label="exercise", expect="dir")
    return candidate, path, items[candidate]


PLACEHOLDER_TOKENS = ("TODO", "TBD", "PLACEHOLDER")
MIN_MARKDOWN_SECTION_CHARS = 20
MIN_MARKDOWN_BODY_CHARS = 80
MIN_EVIDENCE_CHARS = 20
HTML_COMMENT_RE = re.compile(r"<!--.*?(?:-->|$)", re.DOTALL)


def _contains_placeholder(value: object) -> bool:
    if isinstance(value, str):
        upper = value.upper()
        return any(token in upper for token in PLACEHOLDER_TOKENS)
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_placeholder(item) for item in value.values())
    return False


def _require_text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or "\n" in value:
        raise ExerciseError(f"{label}는 앞뒤 공백이나 줄바꿈 없는 비어 있지 않은 문자열이어야 합니다.")
    if _contains_placeholder(value):
        raise ExerciseError(f"{label}에 TODO/TBD/PLACEHOLDER를 사용할 수 없습니다.")
    return value


def _meaningful_chars(lines: list[str]) -> int:
    body: list[str] = []
    visible_content = HTML_COMMENT_RE.sub("", "\n".join(lines))
    for line in visible_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("|") and not stripped.replace("|", "").replace(":", "").replace("-", "").strip():
            continue
        body.append(stripped)
    return sum(1 for character in "\n".join(body) if character.isalnum())


def _markdown_sections(content: str, *, artifact: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in content.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            if not heading or heading in sections:
                raise ExerciseError(f"capstone Markdown의 section heading이 비었거나 중복됩니다: {artifact}")
            sections[heading] = []
            current = heading
        elif current is not None:
            sections[current].append(line)
    return sections


def _validate_completed_markdown(path: Path, artifact: str, content: str) -> None:
    template_file = contained_path(path / "skeleton", artifact, label="capstone template artifact", expect="file")
    template_content = template_file.read_text(encoding="utf-8")
    required_sections = _markdown_sections(template_content, artifact=artifact)
    actual_sections = _markdown_sections(content, artifact=artifact)
    missing = sorted(set(required_sections) - set(actual_sections))
    if missing:
        raise ExerciseError(f"capstone Markdown 필수 section이 없습니다: {artifact}: {missing}")
    for heading in required_sections:
        if _meaningful_chars(actual_sections[heading]) < MIN_MARKDOWN_SECTION_CHARS:
            raise ExerciseError(
                f"capstone Markdown section에 구체적인 근거가 부족합니다: {artifact} ## {heading}"
            )
    if _meaningful_chars(content.splitlines()) < MIN_MARKDOWN_BODY_CHARS:
        raise ExerciseError(f"capstone Markdown 본문 근거가 부족합니다: {artifact}")


def _validate_json_shape(template: object, actual: object, *, label: str, location: str = "$") -> None:
    if isinstance(template, dict):
        if not isinstance(actual, dict):
            raise ExerciseError(f"{label}의 JSON object 구조가 template과 다릅니다: {location}")
        missing = sorted(set(template) - set(actual))
        if missing:
            raise ExerciseError(f"{label}의 JSON key가 누락됐습니다: {location}: {missing}")
        for key, value in template.items():
            _validate_json_shape(value, actual[key], label=label, location=f"{location}.{key}")
    elif isinstance(template, list):
        if not isinstance(actual, list):
            raise ExerciseError(f"{label}의 JSON array 구조가 template과 다릅니다: {location}")
        if template:
            for index, value in enumerate(actual):
                _validate_json_shape(template[0], value, label=label, location=f"{location}[{index}]")
    elif type(actual) is not type(template):
        raise ExerciseError(f"{label}의 JSON scalar type이 template과 다릅니다: {location}")


def _json_path(value: object, raw: str, *, label: str) -> object:
    if (
        not isinstance(raw, str)
        or not raw
        or raw != raw.strip()
        or any(part in {"", ".", ".."} for part in raw.split("."))
    ):
        raise ExerciseError(f"{label}의 JSON path가 잘못됐습니다: {raw!r}")
    current = value
    for part in raw.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ExerciseError(f"{label}의 JSON path가 없습니다: {raw}")
        current = current[part]
    return current


def _meaningful_json_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not _contains_placeholder(value)
    if isinstance(value, list):
        return bool(value) and all(_meaningful_json_value(item) for item in value)
    if isinstance(value, dict):
        return bool(value) and all(
            isinstance(key, str) and bool(key.strip()) and _meaningful_json_value(item)
            for key, item in value.items()
        )
    return True


def _validate_capstone_evidence(
    target: Path,
    *,
    capstone_id: str,
    required_scenarios: list[str],
    submission: dict,
) -> int:
    evidence_path = contained_path(target, "evidence.json", label="capstone evidence manifest", expect="file")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if (
        not isinstance(evidence, dict)
        or type(evidence.get("schema_version")) is not int
        or evidence.get("schema_version") != 1
    ):
        raise ExerciseError("capstone evidence.json schema_version은 1이어야 합니다.")
    if evidence.get("capstone_id") != capstone_id:
        raise ExerciseError("capstone evidence.json의 capstone_id가 rubric과 다릅니다.")
    for field in ("run_id", "input_fixture", "input_identity", "code_identity", "output_location", "output_identity"):
        _require_text(evidence.get(field), label=f"evidence.{field}")
    for field in (
        "run_id",
        "input_fixture",
        "input_identity",
        "code_identity",
        "output_location",
        "output_identity",
    ):
        if evidence[field] != submission[field]:
            raise ExerciseError(f"submission과 evidence의 {field}가 다릅니다.")

    scenarios = evidence.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ExerciseError("capstone evidence.scenarios는 비어 있지 않은 배열이어야 합니다.")
    by_id: dict[str, dict] = {}
    evidence_files: set[str] = set()
    evidence_file_identities: set[tuple[int, int]] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ExerciseError("capstone evidence scenario는 object여야 합니다.")
        scenario_id = _require_text(scenario.get("id"), label="evidence.scenario.id")
        if scenario_id in by_id:
            raise ExerciseError(f"capstone evidence scenario가 중복됩니다: {scenario_id}")
        by_id[scenario_id] = scenario
        if scenario.get("status") != "pass":
            raise ExerciseError(f"capstone evidence scenario status는 pass여야 합니다: {scenario_id}")
        for field in ("fixture", "expected", "observed", "evidence"):
            _require_text(scenario.get(field), label=f"evidence.scenario[{scenario_id}].{field}")
        relative_evidence = scenario["evidence"]
        if not relative_evidence.startswith("evidence/"):
            raise ExerciseError(f"scenario evidence는 evidence/ 아래여야 합니다: {scenario_id}")
        if relative_evidence in evidence_files:
            raise ExerciseError(f"scenario별 evidence file은 고유해야 합니다: {relative_evidence}")
        evidence_files.add(relative_evidence)
        evidence_file = contained_path(target, relative_evidence, label="scenario evidence", expect="file")
        file_stat = evidence_file.stat()
        file_identity = (file_stat.st_dev, file_stat.st_ino)
        if file_identity in evidence_file_identities:
            raise ExerciseError(f"scenario별 evidence file은 물리적으로 고유해야 합니다: {relative_evidence}")
        evidence_file_identities.add(file_identity)
        evidence_content = evidence_file.read_text(encoding="utf-8")
        if _contains_placeholder(evidence_content) or _meaningful_chars(evidence_content.splitlines()) < MIN_EVIDENCE_CHARS:
            raise ExerciseError(f"scenario evidence file의 관측 근거가 부족합니다: {relative_evidence}")

    missing = sorted(set(required_scenarios) - set(by_id))
    unexpected = sorted(set(by_id) - set(required_scenarios))
    if missing or unexpected:
        raise ExerciseError(
            f"capstone evidence scenario 집합이 rubric과 다릅니다: missing={missing} unexpected={unexpected}"
        )
    return len(scenarios)


def capstone_check(path: Path, target: Path, *, template: bool) -> None:
    reject_symlinks(target)
    rubric_path = contained_path(path, "rubric.json", label="capstone rubric", expect="file")
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    if not isinstance(rubric, dict):
        raise ExerciseError("capstone rubric root는 object여야 합니다.")
    required = rubric.get("required_artifacts")
    criteria = rubric.get("criteria")
    capstone_id = rubric.get("capstone_id")
    required_scenarios = rubric.get("required_scenarios")
    required_nonempty_json = rubric.get("required_nonempty_json")
    if rubric.get("version") != 2:
        raise ExerciseError("capstone rubric version은 2여야 합니다.")
    if not isinstance(required, list) or not required or not all(isinstance(x, str) for x in required):
        raise ExerciseError("capstone required_artifacts가 없습니다.")
    if len(required) != len(set(required)) or "submission.json" not in required or "evidence.json" not in required:
        raise ExerciseError("capstone required_artifacts는 고유해야 하며 submission.json과 evidence.json을 포함해야 합니다.")
    if (
        not isinstance(criteria, list)
        or not criteria
        or not all(isinstance(x, str) and x.strip() == x and x for x in criteria)
    ):
        raise ExerciseError("capstone human-review criteria가 없습니다.")
    if not isinstance(capstone_id, str) or not capstone_id or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in capstone_id
    ):
        raise ExerciseError("capstone_id는 소문자 영숫자와 하이픈으로 구성해야 합니다.")
    if (
        not isinstance(required_scenarios, list)
        or not required_scenarios
        or not all(isinstance(x, str) and x.strip() == x and x for x in required_scenarios)
        or len(required_scenarios) != len(set(required_scenarios))
    ):
        raise ExerciseError("capstone required_scenarios는 고유한 비어 있지 않은 문자열 배열이어야 합니다.")
    if not isinstance(required_nonempty_json, dict):
        raise ExerciseError("capstone required_nonempty_json은 object여야 합니다.")
    for artifact, json_paths in required_nonempty_json.items():
        if not isinstance(artifact, str) or artifact not in required or not artifact.endswith(".json"):
            raise ExerciseError(f"required_nonempty_json artifact가 required_artifacts의 JSON이 아닙니다: {artifact!r}")
        if (
            not isinstance(json_paths, list)
            or not json_paths
            or not all(isinstance(value, str) for value in json_paths)
            or len(json_paths) != len(set(json_paths))
        ):
            raise ExerciseError(f"required_nonempty_json path 목록이 잘못됐습니다: {artifact}")
        template_json = json.loads(
            contained_path(
                path / "skeleton", artifact, label="required_nonempty_json template", expect="file"
            ).read_text(encoding="utf-8")
        )
        for json_path in json_paths:
            _json_path(template_json, json_path, label=artifact)
    if rubric.get("reference_implementation") is not False:
        raise ExerciseError("capstone은 자동 완성 판정용 reference를 제공하지 않습니다.")
    placeholder_artifacts: set[str] = set()
    for artifact in required:
        file = contained_path(target, artifact, label="capstone artifact", expect="file")
        content = file.read_text(encoding="utf-8")
        if not content.strip():
            raise ExerciseError(f"capstone artifact가 비어 있습니다: {artifact}")
        if file.suffix == ".json":
            value = json.loads(content)
            if _contains_placeholder(value):
                placeholder_artifacts.add(artifact)
            if not template and _contains_placeholder(value):
                raise ExerciseError(f"capstone artifact에 TODO/TBD/PLACEHOLDER가 남아 있습니다: {artifact}")
            if not template and value in ({}, []):
                raise ExerciseError(f"capstone JSON artifact가 비어 있습니다: {artifact}")
            if not template:
                template_file = contained_path(
                    path / "skeleton", artifact, label="capstone JSON template artifact", expect="file"
                )
                template_value = json.loads(template_file.read_text(encoding="utf-8"))
                _validate_json_shape(template_value, value, label=artifact)
                for json_path in required_nonempty_json.get(artifact, []):
                    required_value = _json_path(value, json_path, label=artifact)
                    if not _meaningful_json_value(required_value):
                        raise ExerciseError(f"capstone JSON 필수 값이 비었습니다: {artifact}: {json_path}")
        else:
            if _contains_placeholder(content):
                placeholder_artifacts.add(artifact)
            if not template and _contains_placeholder(content):
                raise ExerciseError(f"capstone artifact에 TODO/TBD/PLACEHOLDER가 남아 있습니다: {artifact}")
            if not template:
                _validate_completed_markdown(path, artifact, content)
    if template and "submission.json" not in placeholder_artifacts:
        raise ExerciseError("capstone template submission.json은 의도적인 TODO placeholder를 포함해야 합니다.")
    if template and "evidence.json" not in placeholder_artifacts:
        raise ExerciseError("capstone template evidence.json은 의도적인 TODO placeholder를 포함해야 합니다.")
    if template:
        submission = json.loads(
            contained_path(target, "submission.json", label="capstone submission template", expect="file").read_text(
                encoding="utf-8"
            )
        )
        evidence = json.loads(
            contained_path(target, "evidence.json", label="capstone evidence template", expect="file").read_text(
                encoding="utf-8"
            )
        )
        if (
            not isinstance(submission, dict)
            or submission.get("capstone_id") != capstone_id
            or submission.get("evidence_manifest") != "evidence.json"
        ):
            raise ExerciseError("capstone submission template identity가 rubric과 다릅니다.")
        for field in (
            "run_id",
            "implementation_profile",
            "run_command",
            "verify_command",
            "input_fixture",
            "input_identity",
            "code_identity",
            "output_location",
            "output_identity",
        ):
            value = submission.get(field)
            if not isinstance(value, str) or not _contains_placeholder(value):
                raise ExerciseError(f"capstone submission template field는 의도적으로 미완성이어야 합니다: {field}")
        known_limits = submission.get("known_limits")
        if (
            not isinstance(known_limits, list)
            or not known_limits
            or not all(isinstance(value, str) and _contains_placeholder(value) for value in known_limits)
        ):
            raise ExerciseError("capstone submission template known_limits는 의도적으로 미완성이어야 합니다.")
        if (
            not isinstance(evidence, dict)
            or type(evidence.get("schema_version")) is not int
            or evidence.get("schema_version") != 1
            or evidence.get("capstone_id") != capstone_id
        ):
            raise ExerciseError("capstone evidence template identity가 rubric과 다릅니다.")
        template_scenarios = evidence.get("scenarios")
        if (
            not isinstance(template_scenarios, list)
            or not all(isinstance(item, dict) for item in template_scenarios)
            or [item.get("id") for item in template_scenarios] != required_scenarios
        ):
            raise ExerciseError("capstone evidence template scenario 순서가 rubric과 다릅니다.")
        for field in ("run_id", "input_fixture", "input_identity", "code_identity", "output_location", "output_identity"):
            value = evidence.get(field)
            if not isinstance(value, str) or not _contains_placeholder(value):
                raise ExerciseError(f"capstone evidence template field는 의도적으로 미완성이어야 합니다: {field}")
        for scenario in template_scenarios:
            for field in ("status", "fixture", "expected", "observed", "evidence"):
                value = scenario.get(field)
                if not isinstance(value, str) or not _contains_placeholder(value):
                    raise ExerciseError(
                        f"capstone evidence template scenario field는 의도적으로 미완성이어야 합니다: "
                        f"{scenario.get('id')}.{field}"
                    )
    if not template:
        submission_path = contained_path(target, "submission.json", label="submission", expect="file")
        submission = json.loads(submission_path.read_text(encoding="utf-8"))
        if not isinstance(submission, dict) or submission.get("capstone_id") != capstone_id:
            raise ExerciseError("submission.capstone_id가 rubric과 다릅니다.")
        if submission.get("evidence_manifest") != "evidence.json":
            raise ExerciseError("submission.evidence_manifest는 evidence.json이어야 합니다.")
        for field in (
            "run_id",
            "implementation_profile",
            "run_command",
            "verify_command",
            "input_fixture",
            "input_identity",
            "code_identity",
            "output_location",
            "output_identity",
        ):
            _require_text(submission.get(field), label=f"submission.{field}")
        known_limits = submission.get("known_limits")
        if not isinstance(known_limits, list) or not known_limits:
            raise ExerciseError("submission.known_limits는 하나 이상의 알려진 한계를 포함해야 합니다.")
        for index, value in enumerate(known_limits):
            _require_text(value, label=f"submission.known_limits[{index}]")
        scenario_count = _validate_capstone_evidence(
            target,
            capstone_id=capstone_id,
            required_scenarios=required_scenarios,
            submission=submission,
        )
        print(
            f"OK capstone evidence structure scenarios={scenario_count}; "
            f"human review required for {len(criteria)} rubric criteria and runtime evidence."
        )
    else:
        print(
            "OK capstone template structure only; "
            f"human review required for {len(criteria)} rubric criteria after learner completion."
        )


def run_checker(path: Path, item: dict, target: Path) -> subprocess.CompletedProcess[str]:
    checker = contained_path(path, item["checker"], label="checker", expect="file")
    reject_symlinks(target)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        return subprocess.run(
            [sys.executable, "-B", str(checker), str(target)],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExerciseError(
            f"checker timeout ({CHECK_TIMEOUT_SECONDS}s): {path.relative_to(ROOT)} target={target.name}"
        ) from exc


def require_pass(result: subprocess.CompletedProcess[str], *, label: str, success_marker: str) -> None:
    if result.returncode != 0:
        raise ExerciseError(f"{label} 실패\n{result.stdout}")
    lines = [line.strip() for line in result.stdout.splitlines()]
    if lines.count(success_marker) != 1:
        raise ExerciseError(
            f"{label}이 exact success marker를 한 번 출력하지 않았습니다.\n"
            f"expected={success_marker}\nactual={result.stdout}"
        )
    if any("GUIDE_SEMANTIC:" in line or "GUIDE_CONTRACT:" in line for line in lines):
        raise ExerciseError(f"{label} 성공 output에 오류 marker가 섞였습니다.\n{result.stdout}")


def tree_fingerprint(root: Path) -> str:
    reject_symlinks(root)
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        mode = stat.S_IMODE(path.stat().st_mode).to_bytes(2, "big")
        if path.is_dir():
            digest.update(b"D\0" + relative + b"\0" + mode)
        else:
            digest.update(b"F\0" + relative + b"\0" + mode + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def inode_identity(path: Path) -> tuple[int, int]:
    metadata = os.lstat(path)
    return metadata.st_dev, metadata.st_ino


def remove_owned_tree(path: Path, expected: tuple[int, int]) -> None:
    if not path.exists() and not path.is_symlink():
        return
    metadata = os.lstat(path)
    if (metadata.st_dev, metadata.st_ino) != expected or not stat.S_ISDIR(metadata.st_mode):
        raise ExerciseError(f"소유권을 확인할 수 없는 staging은 정리하지 않습니다: {path}")
    reject_symlinks(path)
    shutil.rmtree(path)


def unlink_owned_file(path: Path, expected: tuple[int, int]) -> None:
    metadata = os.lstat(path)
    if (metadata.st_dev, metadata.st_ino) != expected or not stat.S_ISREG(metadata.st_mode):
        raise ExerciseError(f"소유권을 확인할 수 없는 lock은 제거하지 않습니다: {path}")
    path.unlink()


def rename_noreplace(source: Path, target: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    target_bytes = os.fsencode(target)
    if sys.platform == "darwin":
        try:
            rename = libc.renamex_np
        except AttributeError as exc:
            raise ExerciseError("renamex_np(RENAME_EXCL)를 사용할 수 없어 workspace publish를 중단합니다.") from exc
        rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        rename.restype = ctypes.c_int
        result = rename(source_bytes, target_bytes, 0x00000004)
    elif sys.platform.startswith("linux"):
        try:
            rename = libc.renameat2
        except AttributeError as exc:
            raise ExerciseError("renameat2(RENAME_NOREPLACE)를 사용할 수 없어 workspace publish를 중단합니다.") from exc
        rename.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        rename.restype = ctypes.c_int
        result = rename(-100, source_bytes, -100, target_bytes, 0x00000001)
    else:
        raise ExerciseError(f"exclusive workspace publish를 지원하지 않는 platform입니다: {sys.platform}")
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(error, os.strerror(error), target)
    raise OSError(error, os.strerror(error), source, target)


def _raise_workspace_interrupted(signum: int, _frame: object) -> None:
    global _SIGNAL_INTERRUPTED
    if _SIGNAL_INTERRUPTED:
        return
    _SIGNAL_INTERRUPTED = True
    raise WorkspaceInterrupted(f"workspace 생성이 signal {signum}으로 중단됐습니다.")


def install_workspace_signal_handlers() -> dict[int, object]:
    global _SIGNAL_INTERRUPTED
    if threading.current_thread() is not threading.main_thread():
        return {}
    _SIGNAL_INTERRUPTED = False
    previous: dict[int, object] = {}
    for name in ("SIGHUP", "SIGTERM"):
        signum = getattr(signal, name, None)
        if signum is None:
            continue
        previous[signum] = signal.getsignal(signum)
        signal.signal(signum, _raise_workspace_interrupted)
    return previous


def restore_workspace_signal_handlers(previous: dict[int, object]) -> None:
    global _SIGNAL_INTERRUPTED
    for signum, handler in previous.items():
        signal.signal(signum, handler)
    _SIGNAL_INTERRUPTED = False


def require_semantic_failure(
    result: subprocess.CompletedProcess[str],
    *,
    expected: str,
    label: str,
) -> None:
    if result.returncode == 0:
        raise ExerciseError(f"{label}이 의도와 달리 통과했습니다.")
    prefix = f"{expected}:"
    semantic_lines = [line for line in result.stdout.splitlines() if line.startswith(prefix)]
    if len(semantic_lines) != 1 or not semantic_lines[0][len(prefix) :].strip():
        raise ExerciseError(
            f"{label}이 비어 있지 않은 진단을 포함한 정확한 의미 오류 행으로 실패하지 않았습니다.\n"
            f"expected={expected}: <diagnostic>\nactual={result.stdout}"
        )
    if "GUIDE_CONTRACT:" in result.stdout:
        raise ExerciseError(f"{label}에 contract/infra 오류가 섞였습니다.\n{result.stdout}")


def command_list(items: dict[str, dict]) -> int:
    for path, item in items.items():
        print(f"{item['kind']:<8} {path}")
    return 0


def _create_workspace(raw: str, items: dict[str, dict]) -> int:
    _, path, _ = resolve_registered(raw, items)
    skeleton = contained_path(path, "skeleton", label="skeleton", expect="dir")
    workspace = path / "workspace"
    lock = path / ".workspace-create.lock"
    staging: Path | None = None
    descriptor: int | None = None
    lock_identity: tuple[int, int] | None = None
    staging_identity: tuple[int, int] | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(lock, flags, 0o600)
        lock_metadata = os.fstat(descriptor)
        if not stat.S_ISREG(lock_metadata.st_mode):
            raise ExerciseError("workspace lock이 regular file이 아닙니다.")
        lock_identity = (lock_metadata.st_dev, lock_metadata.st_ino)
    except FileExistsError as exc:
        raise ExerciseError(f"workspace 생성이 이미 진행 중입니다: {path.relative_to(ROOT)}") from exc
    try:
        if workspace.exists() or workspace.is_symlink():
            raise ExerciseError(f"workspace가 이미 있습니다: {workspace.relative_to(ROOT)}")
        staging = Path(tempfile.mkdtemp(prefix=".workspace-staging-", dir=path))
        staging_identity = inode_identity(staging)
        shutil.copytree(skeleton, staging, symlinks=False, dirs_exist_ok=True)
        if tree_fingerprint(staging) != tree_fingerprint(skeleton):
            raise ExerciseError("workspace staging copy 검증에 실패했습니다.")
        if _WORKSPACE_HOLD_HOOK is not None:
            _WORKSPACE_HOLD_HOOK(path, staging)
        rename_noreplace(staging, workspace)
        if inode_identity(workspace) != staging_identity:
            raise ExerciseError("published workspace inode가 staging과 다릅니다.")
        staging = None
        staging_identity = None
    except FileExistsError as exc:
        raise ExerciseError(f"workspace를 덮어쓰지 않습니다: {workspace.relative_to(ROOT)}") from exc
    finally:
        cleanup_errors: list[Exception] = []
        if descriptor is not None:
            os.close(descriptor)
        if staging is not None and staging_identity is not None:
            try:
                remove_owned_tree(staging, staging_identity)
            except Exception as exc:
                cleanup_errors.append(exc)
        if lock_identity is not None:
            try:
                unlink_owned_file(lock, lock_identity)
            except Exception as exc:
                cleanup_errors.append(exc)
        if cleanup_errors:
            raise cleanup_errors[0]
    print(workspace.relative_to(ROOT))
    return 0


def command_new(raw: str, items: dict[str, dict]) -> int:
    previous_handlers = install_workspace_signal_handlers()
    try:
        return _create_workspace(raw, items)
    finally:
        restore_workspace_signal_handlers(previous_handlers)


def target_for(path: Path, source: str) -> Path:
    return contained_path(path, source, label=source, expect="dir")


def command_check(raw: str, source: str, items: dict[str, dict]) -> int:
    _, path, item = resolve_registered(raw, items)
    target = target_for(path, source)
    if item["kind"] == "capstone":
        capstone_check(path, target, template=source == "skeleton")
        return 0
    result = run_checker(path, item, target)
    print(result.stdout, end="")
    return result.returncode


def command_verify_all(items: dict[str, dict]) -> int:
    for raw in items:
        _, path, item = resolve_registered(raw, items)
        reject_symlinks(path)
        if item["kind"] == "capstone":
            capstone_check(path, target_for(path, "skeleton"), template=True)
            print(f"OK capstone template {raw}")
            continue
        reference_target = target_for(path, "reference")
        reference = run_checker(path, item, reference_target)
        require_pass(reference, label=f"reference {raw}", success_marker=item["success_marker"])
        expected = item["semantic_failure"]
        skeleton = run_checker(path, item, target_for(path, "skeleton"))
        require_semantic_failure(skeleton, expected=expected, label=f"skeleton {raw}")
        fixture_count = 0
        for fixture in item["known_bad"]:
            fixture_target = contained_path(path, fixture, label="known_bad", expect="dir")
            result = run_checker(path, item, fixture_target)
            require_semantic_failure(
                result,
                expected=expected,
                label=f"known_bad {raw}/{fixture}",
            )
            fixture_count += 1
        print(f"OK contract {raw} known_bad={fixture_count}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    new = sub.add_parser("new")
    new.add_argument("exercise")
    check = sub.add_parser("check")
    check.add_argument("exercise")
    check.add_argument("--source", choices=("skeleton", "reference", "workspace"), default="workspace")
    sub.add_parser("verify-all")
    args = parser.parse_args()
    items = load_items()
    if args.command == "list":
        return command_list(items)
    if args.command == "new":
        return command_new(args.exercise, items)
    if args.command == "check":
        return command_check(args.exercise, args.source, items)
    if args.command == "verify-all":
        return command_verify_all(items)
    raise ExerciseError("unknown command")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ExerciseError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
