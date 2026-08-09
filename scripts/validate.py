#!/usr/bin/env python3
"""Validate repository structure and executable contracts without writing artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

from repository_state import entries

ROOT = Path(os.environ.get("GUIDE_ROOT", Path(__file__).resolve().parents[1])).resolve()
LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
H1_RE = re.compile(r"^#\s+\S", re.MULTILINE)
FENCED_RE = re.compile(r"(?ms)^```.*?^```\s*$|^~~~.*?^~~~\s*$")
CONCEPT_HEADINGS = (
    "## 학습 목표",
    "## 핵심 모델",
    "## 실패 모드",
    "## 검증 질문",
    "## 연결 연습",
    "## 완료 기준",
)
REQUIRED_FILES = {
    ".gitignore",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "LICENSES/CC-BY-4.0.txt",
    "LICENSES/MIT.txt",
    "Makefile",
    "README.md",
    "exercises/manifest.json",
    "prepare.sh",
    "scripts/check-workspace.sh",
    "scripts/clean_generated.py",
    "scripts/exercise_tool.py",
    "scripts/fingerprint.py",
    "scripts/new-workspace.sh",
    "scripts/repository_state.py",
    "scripts/test_clean_safety.py",
    "scripts/test_prepare_safety.py",
    "scripts/test_repository_state.py",
    "scripts/test_validator.py",
    "scripts/test_verify_preflight.py",
    "scripts/test_workspace_tools.py",
    "scripts/validate.py",
    "verify.sh",
}
REQUIRED_DIRECTORIES = {
    "LICENSES",
    "docs",
    "examples",
    "exercises",
    "reference",
    "scripts",
    "tests",
}
REQUIRED_IGNORE_RULES = {
    ".DS_Store",
    ".env",
    ".env.*",
    ".guide/",
    ".pytest_cache/",
    ".venv/",
    "*.log",
    "*.pid",
    "*.py[cod]",
    "*.tmp",
    "__pycache__/",
    "exercises/**/workspace/",
    "exercises/**/workspace.tmp.*/",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def lstat_regular(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISREG(metadata.st_mode)


def lstat_directory(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISDIR(metadata.st_mode)


def markdown_target(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1 : raw.index(">")]
    return raw.split(maxsplit=1)[0]


def anchor(value: str) -> str:
    value = re.sub(r"[`*_~]", "", value.strip().lower())
    value = re.sub(r"[^\w\-가-힣 ]", "", value)
    return re.sub(r"\s+", "-", value.strip())


def managed_files(suffix: str | None = None) -> list[Path]:
    paths: list[Path] = []
    for item in entries(ROOT, "source"):
        if item["kind"] != "file":
            continue
        path = ROOT / str(item["path"])
        if suffix is None or path.suffix == suffix:
            paths.append(path)
    return sorted(paths)


def check_structure() -> None:
    missing = sorted(path for path in REQUIRED_FILES if not lstat_regular(ROOT / path))
    if missing:
        fail(f"필수 일반 파일 누락: {missing}")
    missing_directories = sorted(
        path for path in REQUIRED_DIRECTORIES if not lstat_directory(ROOT / path)
    )
    if missing_directories:
        fail(f"필수 실제 디렉터리 누락: {missing_directories}")
    unsafe = [
        f"{item['path']} ({item['kind']})"
        for item in entries(ROOT, "source")
        if item["kind"] in {"symlink", "other"}
    ]
    if unsafe:
        fail(f"managed source의 symlink/특수 파일은 허용하지 않습니다: {unsafe}")
    for path in (ROOT / "prepare.sh", ROOT / "verify.sh"):
        if not path.stat().st_mode & stat.S_IXUSR:
            fail(f"실행 권한 누락: {path.relative_to(ROOT)}")
    for path in sorted(
        candidate
        for candidate in (ROOT / "scripts").iterdir()
        if candidate.suffix in {".py", ".sh"} and lstat_regular(candidate)
    ):
        if not path.stat().st_mode & stat.S_IXUSR:
            fail(f"실행 권한 누락: {path.relative_to(ROOT)}")


def check_markdown() -> None:
    files = managed_files(".md")
    if not files:
        fail("Markdown 문서가 없습니다.")
    root = ROOT.resolve()
    for path in files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        prose = FENCED_RE.sub("", text)
        if len(H1_RE.findall(prose)) != 1:
            fail(f"{relative}: H1 제목은 정확히 하나여야 합니다.")
        if text.count("```") % 2 or text.count("~~~") % 2:
            fail(f"{relative}: 닫히지 않은 fenced code block이 있습니다.")
        for raw in LINK_RE.findall(prose):
            target_text = markdown_target(raw)
            if not target_text or target_text.startswith(
                ("http://", "https://", "mailto:", "data:")
            ):
                continue
            raw_path, _, fragment = target_text.partition("#")
            decoded = unquote(raw_path)
            resolved = (path if not decoded else path.parent / decoded).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                fail(f"{relative}: 저장소 밖 링크 {raw}")
            if not resolved.exists():
                fail(f"{relative}: 깨진 링크 {raw}")
            if fragment and resolved.is_file() and resolved.suffix == ".md":
                linked = resolved.read_text(encoding="utf-8")
                anchors = {anchor(heading) for heading in HEADING_RE.findall(linked)}
                if anchor(unquote(fragment)) not in anchors:
                    fail(f"{relative}: 깨진 anchor {raw}")


def check_concept_docs() -> None:
    for section in range(1, 6):
        directories = sorted((ROOT / "docs").glob(f"{section:02d}-*"))
        if len(directories) != 1 or not lstat_directory(directories[0]):
            fail(f"docs/{section:02d}-* 개념 디렉터리는 정확히 하나여야 합니다.")
        concept_files = sorted(directories[0].glob("*.md"))
        if not concept_files:
            fail(f"{directories[0].relative_to(ROOT)}: 개념 문서가 없습니다.")
        for path in concept_files:
            text = path.read_text(encoding="utf-8")
            offsets: list[int] = []
            for heading in CONCEPT_HEADINGS:
                if text.count(heading + "\n") != 1:
                    fail(f"{path.relative_to(ROOT)}: {heading} section은 정확히 하나여야 합니다.")
                offsets.append(text.index(heading + "\n"))
            if offsets != sorted(offsets):
                fail(f"{path.relative_to(ROOT)}: 개념 section 순서가 올바르지 않습니다.")


def safe_relative(value: object, *, prefix: str | None = None) -> PurePosixPath:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\\" in value
        or "\x00" in value
    ):
        fail(f"잘못된 상대 경로: {value!r}")
    raw_parts = value.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        fail(f"정규화되지 않은 상대 경로: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        fail(f"정규화되지 않은 상대 경로: {value!r}")
    if prefix is not None and (not path.parts or path.parts[0] != prefix):
        fail(f"{prefix}/ 아래가 아닌 경로: {value!r}")
    return path


def load_manifest() -> dict[str, object]:
    path = ROOT / "exercises/manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"exercise manifest를 읽을 수 없습니다: {exc}")
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        fail("exercise manifest version은 1이어야 합니다.")
    exercises = manifest.get("exercises")
    if not isinstance(exercises, list) or not exercises:
        fail("manifest exercises는 비어 있지 않은 배열이어야 합니다.")
    return manifest


def check_exercises(manifest: dict[str, object]) -> None:
    items = manifest["exercises"]
    assert isinstance(items, list)
    seen: set[str] = set()
    seen_semantic_failures: set[str] = set()
    seen_success_markers: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            fail(f"exercise 항목은 object여야 합니다: {item!r}")
        path_value = item.get("path")
        exercise_path = safe_relative(path_value, prefix="exercises")
        path_text = exercise_path.as_posix()
        if path_text in seen:
            fail(f"중복 exercise: {path_text}")
        seen.add(path_text)
        path = ROOT.joinpath(*exercise_path.parts)
        if not lstat_directory(path) or not lstat_regular(path / "README.md") or not lstat_directory(path / "skeleton"):
            fail(f"{path_text}: README 또는 skeleton 누락")
        kind = item.get("kind")
        if kind in {"code", "design"}:
            checker_path = safe_relative(item.get("checker"))
            semantic = item.get("semantic_failure")
            if not isinstance(semantic, str) or not semantic.startswith("GUIDE_SEMANTIC:"):
                fail(f"{path_text}: semantic_failure 형식이 올바르지 않습니다.")
            if semantic in seen_semantic_failures:
                fail(f"{path_text}: semantic_failure가 중복됩니다: {semantic}")
            seen_semantic_failures.add(semantic)
            success_marker = item.get("success_marker")
            if (
                not isinstance(success_marker, str)
                or not success_marker.startswith("OK ")
                or success_marker != success_marker.strip()
            ):
                fail(f"{path_text}: success_marker는 'OK '로 시작하는 문자열이어야 합니다.")
            if success_marker in seen_success_markers:
                fail(f"{path_text}: success_marker가 중복됩니다: {success_marker}")
            seen_success_markers.add(success_marker)
            if not lstat_regular(path.joinpath(*checker_path.parts)) or not lstat_directory(path / "reference"):
                fail(f"{path_text}: checker 또는 reference 누락")
            known_bad = item.get("known_bad")
            if (
                not isinstance(known_bad, list)
                or not known_bad
                or any(not isinstance(value, str) for value in known_bad)
            ):
                fail(f"{path_text}: known_bad는 비어 있지 않은 상대 경로 문자열 배열이어야 합니다.")
            if len(set(known_bad)) != len(known_bad):
                fail(f"{path_text}: known_bad 경로가 중복됩니다.")
            for value in known_bad:
                bad_path = safe_relative(value)
                if bad_path.parts[0] != "known_bad":
                    fail(f"{path_text}: known_bad fixture는 known_bad/ 아래여야 합니다: {value}")
                candidate = path.joinpath(*bad_path.parts)
                if not lstat_directory(candidate):
                    fail(f"{path_text}: known_bad fixture 누락 {value}")
        elif kind == "capstone":
            rubric_path = path / "rubric.json"
            if not lstat_regular(rubric_path):
                fail(f"{path_text}: rubric.json 누락")
            rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
            required = rubric.get("required_artifacts")
            criteria = rubric.get("criteria")
            if not isinstance(required, list) or not required:
                fail(f"{path_text}: required_artifacts 누락")
            if not isinstance(criteria, list) or not criteria:
                fail(f"{path_text}: criteria 누락")
            for artifact in required:
                artifact_path = safe_relative(artifact)
                if not lstat_regular(path / "skeleton" / Path(*artifact_path.parts)):
                    fail(f"{path_text}: capstone template 누락 {artifact}")
            if rubric.get("reference_implementation") is not False:
                fail(f"{path_text}: capstone은 reference 구현을 제공하지 않아야 합니다.")
        else:
            fail(f"{path_text}: 알 수 없는 kind {kind!r}")

    actual = {
        path.parent.relative_to(ROOT).as_posix()
        for path in (ROOT / "exercises").rglob("README.md")
        if lstat_directory(path.parent / "skeleton")
    }
    if seen != actual:
        fail(
            "manifest와 exercise tree가 다릅니다: "
            f"missing={sorted(actual - seen)} unexpected={sorted(seen - actual)}"
        )


def check_json_and_python() -> None:
    for path in managed_files():
        relative = path.relative_to(ROOT)
        if path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                fail(f"{relative}: JSON 오류 {exc}")
        elif path.suffix == ".py":
            try:
                source = path.read_text(encoding="utf-8")
                compile(source, str(path), "exec")
            except (UnicodeError, SyntaxError) as exc:
                fail(f"{relative}: Python syntax 오류 {exc}")


def check_repository_contracts() -> None:
    ignore_rules = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    missing_rules = sorted(REQUIRED_IGNORE_RULES - ignore_rules)
    if missing_rules:
        fail(f".gitignore 필수 규칙 누락: {missing_rules}")
    license_document = (ROOT / "LICENSE.md").read_text(encoding="utf-8")
    for token in ("Creative Commons Attribution 4.0", "LICENSES/CC-BY-4.0.txt", "MIT License", "LICENSES/MIT.txt"):
        if token not in license_document:
            fail(f"LICENSE.md 고지 누락: {token}")
    for path in (ROOT / "README.md", ROOT / "CONTRIBUTING.md"):
        text = path.read_text(encoding="utf-8")
        for command in ("make prepare", "make check", "make verify", "make clean"):
            if command not in text:
                fail(f"{path.relative_to(ROOT)} 공개 명령 누락: {command}")
    forbidden_names = {".env", "id_dsa", "id_ed25519", "id_rsa"}
    private_key_markers = (
        b"-----BEGIN " + b"PRIVATE KEY-----",
        b"-----BEGIN RSA " + b"PRIVATE KEY-----",
    )
    for path in managed_files():
        if path.name in forbidden_names or path.suffix.lower() in {".p12", ".pem"}:
            fail(f"비밀정보 가능성이 있는 파일: {path.relative_to(ROOT)}")
        if path.stat().st_size <= 2_000_000:
            data = path.read_bytes()
            if any(marker in data for marker in private_key_markers):
                fail(f"private key 내용이 발견됐습니다: {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="호환성을 위한 alias; 모든 구조 검사를 실행합니다.")
    parser.parse_args()
    check_structure()
    check_markdown()
    check_concept_docs()
    manifest = load_manifest()
    check_exercises(manifest)
    check_json_and_python()
    check_repository_contracts()
    print(
        f"OK structural-contracts markdown={len(managed_files('.md'))} "
        f"exercises={len(manifest['exercises'])}; 자동 검사는 교육적 완성을 판정하지 않습니다."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
