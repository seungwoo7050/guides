#!/usr/bin/env python3
"""Capture and copy the learner-owned source tree without following symlinks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

GUIDE_ID = "java"
GENERATED_DIRECTORIES = {
    ".git",
    ".guide",
    "target",
    "examples/runtime-model/target",
    "exercises/01-language-and-domain/01-first-program/reference/target",
    "exercises/01-language-and-domain/01-first-program/skeleton/target",
    "exercises/01-language-and-domain/02-value-object-contract/reference/target",
    "exercises/01-language-and-domain/02-value-object-contract/skeleton/target",
    "exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference/target",
    "exercises/02-runtime-and-concurrency/01-concurrent-state-update/skeleton/target",
    "exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference/target",
    "exercises/02-runtime-and-concurrency/02-executor-lifecycle/skeleton/target",
    "exercises/03-build-test-and-evidence/01-multi-repository-maven/.workspace",
    "exercises/03-build-test-and-evidence/01-multi-repository-maven/consumer-service/target",
    "exercises/03-build-test-and-evidence/01-multi-repository-maven/contract-library/target",
    "exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference/target",
    "exercises/03-build-test-and-evidence/02-state-and-effect-testing/skeleton/target",
    "exercises/04-capstone/01-concurrent-job-ledger/reference/target",
    "exercises/04-capstone/01-concurrent-job-ledger/skeleton/target",
    "scripts/__pycache__",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def learner_workspace(relative: str) -> bool:
    return relative == ".workspace" or relative.startswith(".workspace/")


def generated(relative: str, *, include_learner_workspace: bool = True) -> bool:
    if not include_learner_workspace and learner_workspace(relative):
        return True
    return any(
        relative == directory or relative.startswith(f"{directory}/")
        for directory in GENERATED_DIRECTORIES
    )


def source_entries(
    root: Path, *, include_learner_workspace: bool = True
) -> Iterator[tuple[str, int, str, str]]:
    def visit(directory: Path) -> Iterator[tuple[str, int, str, str]]:
        with os.scandir(directory) as iterator:
            children = sorted(iterator, key=lambda item: item.name)
        for child in children:
            child_path = Path(child.path)
            relative = child_path.relative_to(root).as_posix()
            if generated(
                relative, include_learner_workspace=include_learner_workspace
            ):
                continue
            metadata = child.stat(follow_symlinks=False)
            mode = stat.S_IMODE(metadata.st_mode)
            if child.is_symlink():
                yield ("L", mode, relative, os.readlink(child.path))
            elif child.is_dir(follow_symlinks=False):
                yield ("D", mode, relative, "")
                yield from visit(child_path)
            elif child.is_file(follow_symlinks=False):
                yield ("F", mode, relative, file_digest(child_path))
            else:
                fail(f"지원하지 않는 파일 형식입니다: {relative}")

    yield from visit(root)


def capture(root: Path, *, include_learner_workspace: bool = True) -> str:
    digest = hashlib.sha256()
    for entry in source_entries(
        root, include_learner_workspace=include_learner_workspace
    ):
        encoded = json.dumps(entry, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def copy_source(root: Path, destination: Path) -> None:
    if destination.exists() and any(destination.iterdir()):
        fail(f"복사 목적지가 비어 있지 않습니다: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    for kind, mode, relative, payload in source_entries(root):
        source = root / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if kind == "D":
            target.mkdir(exist_ok=True)
            target.chmod(mode)
        elif kind == "L":
            target.symlink_to(payload)
        elif kind == "F":
            shutil.copy2(source, target, follow_symlinks=False)
            target.chmod(mode)


def git_index_state(root: Path) -> dict[str, str]:
    """Hash the linked-worktree index bytes and its semantic staged entries."""

    probe = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        fail(f"Git working tree가 아닙니다: {root}")

    index_path_result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-path", "index"],
        check=True,
        capture_output=True,
        text=True,
    )
    index_path = Path(index_path_result.stdout.strip())
    if not index_path.is_absolute():
        index_path = root / index_path
    index_path = index_path.resolve(strict=True)
    if not index_path.is_file():
        fail(f"Git index 파일이 없습니다: {index_path}")

    staged_entries = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--stage", "-z"],
        check=True,
        capture_output=True,
    ).stdout
    return {
        "raw_bytes_sha256": file_digest(index_path),
        "staged_entries_sha256": hashlib.sha256(staged_entries).hexdigest(),
    }


def load_marker(path: Path) -> dict[str, object]:
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"준비 상태 파일을 읽을 수 없습니다: {error}")
    if not isinstance(marker, dict):
        fail("준비 상태 파일의 최상위 값은 객체여야 합니다.")
    return marker


def validate_marker(path: Path, fingerprint: str) -> dict[str, object]:
    marker = load_marker(path)
    expected = {
        "schema": 1,
        "guide_id": GUIDE_ID,
        "input_fingerprint": fingerprint,
        "maven_version": "3.9.16",
    }
    for key, value in expected.items():
        if marker.get(key) != value:
            fail(f"준비 상태가 현재 저장소와 일치하지 않습니다: {key}")
    expected_locations = {
        "maven_user_home": path.absolute().parent / "maven-home",
        "maven_repository": path.absolute().parent / "maven-repository",
    }
    for key, expected_location in expected_locations.items():
        raw = marker.get(key)
        if (
            not isinstance(raw, str)
            or not Path(raw).is_absolute()
            or Path(raw) != expected_location
            or not Path(raw).is_dir()
        ):
            fail(f"준비 상태의 경로가 올바르지 않습니다: {key}")
    version_fields = {
        "java_version": r'^(?:openjdk|java) version "21(?:[.]|\")',
        "javac_version": r"^javac 21(?:[.]|$)",
        "maven_version_text": r"^Apache Maven 3[.]9[.]16(?:\s|$)",
    }
    for key, pattern in version_fields.items():
        raw = marker.get(key)
        if not isinstance(raw, str) or re.search(pattern, raw) is None:
            fail(f"준비 상태의 도구 버전이 올바르지 않습니다: {key}")
    if marker.get("docker_image_id") is not None:
        fail("Java 가이드의 docker_image_id는 null이어야 합니다.")
    return marker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("root", type=Path)

    preparation_parser = subparsers.add_parser("preparation-capture")
    preparation_parser.add_argument("root", type=Path)

    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser.add_argument("root", type=Path)

    copy_parser = subparsers.add_parser("copy")
    copy_parser.add_argument("root", type=Path)
    copy_parser.add_argument("destination", type=Path)

    index_parser = subparsers.add_parser("index-state")
    index_parser.add_argument("root", type=Path)

    marker_parser = subparsers.add_parser("validate-marker")
    marker_parser.add_argument("path", type=Path)
    marker_parser.add_argument("fingerprint")

    field_parser = subparsers.add_parser("marker-field")
    field_parser.add_argument("path", type=Path)
    field_parser.add_argument("fingerprint")
    field_parser.add_argument("field", choices=("maven_user_home", "maven_repository"))
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if arguments.command == "capture":
        print(capture(arguments.root.resolve()))
    elif arguments.command == "preparation-capture":
        print(capture(arguments.root.resolve(), include_learner_workspace=False))
    elif arguments.command == "manifest":
        for entry in source_entries(arguments.root.resolve()):
            print(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
    elif arguments.command == "copy":
        copy_source(arguments.root.resolve(), arguments.destination.resolve())
    elif arguments.command == "index-state":
        print(
            json.dumps(
                git_index_state(arguments.root.resolve()),
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    elif arguments.command == "validate-marker":
        validate_marker(arguments.path, arguments.fingerprint)
    elif arguments.command == "marker-field":
        marker = validate_marker(arguments.path, arguments.fingerprint)
        print(marker[arguments.field])
    else:
        fail(f"지원하지 않는 명령입니다: {arguments.command}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.stderr.close()
        raise SystemExit(1)
