#!/usr/bin/env python3
"""Capture, copy, and validate the Spring guide preparation state."""

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
from collections.abc import Iterator, Mapping
from pathlib import Path

GUIDE_ID = "backend-spring-boot"
MAVEN_VERSION = "3.9.16"
IMAGE_REFS = (
    "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15",
    "redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005",
    "testcontainers/ryuk:0.14.0@sha256:7c1a8a9a47c780ed0f983770a662f80deb115d95cce3e2daa3d12115b8cd28f0",
    "apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837",
)
EXERCISES = (
    "application-boundaries",
    "security-boundaries",
    "transaction-locking",
    "idempotency-outbox",
    "kafka-avro-contract",
    "resilient-http-client",
    "single-service-capstone",
)

# Only build locations owned by this guide are generated. A learner directory
# named target or .workspace elsewhere remains part of the source state.
GENERATED_DIRECTORIES = {
    ".git",
    ".guide",
    ".workspace",
    "target",
    "scripts/__pycache__",
    *(f"exercises/{exercise}/{variant}/target"
      for exercise in EXERCISES for variant in ("reference", "skeleton")),
}


def fail(message: str) -> None:
    raise SystemExit(message)


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generated(relative: str) -> bool:
    return any(
        relative == directory or relative.startswith(f"{directory}/")
        for directory in GENERATED_DIRECTORIES
    )


def source_entries(root: Path) -> Iterator[tuple[str, int, str, str]]:
    """Yield source entries without following symlinks."""

    def visit(directory: Path) -> Iterator[tuple[str, int, str, str]]:
        try:
            with os.scandir(directory) as iterator:
                children = sorted(iterator, key=lambda item: item.name)
        except OSError as error:
            fail(f"source directory를 읽을 수 없습니다: {directory}: {error}")
        for child in children:
            child_path = Path(child.path)
            relative = child_path.relative_to(root).as_posix()
            if generated(relative):
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


def capture(root: Path) -> str:
    digest = hashlib.sha256()
    for entry in source_entries(root):
        encoded = json.dumps(
            entry, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
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
    """Hash actual linked-worktree index bytes and semantic staged entries."""

    probe = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        fail(f"Git working tree가 아닙니다: {root}")
    index_result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-path", "index"],
        check=True,
        capture_output=True,
        text=True,
    )
    index_path = Path(index_result.stdout.strip())
    if not index_path.is_absolute():
        index_path = root / index_path
    index_path = index_path.resolve(strict=True)
    if not index_path.is_file():
        fail(f"Git index 파일이 없습니다: {index_path}")
    staged = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--stage", "-z"],
        check=True,
        capture_output=True,
    ).stdout
    return {
        "raw_bytes_sha256": file_digest(index_path),
        "staged_entries_sha256": hashlib.sha256(staged).hexdigest(),
    }


def command_output(arguments: list[str], environment: Mapping[str, str] | None = None) -> str:
    result = subprocess.run(
        arguments,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode != 0:
        fail(f"도구 정보를 읽지 못했습니다: {' '.join(arguments)}")
    return result.stdout.strip() or result.stderr.strip()


def current_tools(root: Path, maven_home: Path, repository: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["MAVEN_USER_HOME"] = str(maven_home)
    maven = command_output(
        [
            str(root / "mvnw"),
            "-o",
            "-B",
            "-ntp",
            f"-Dmaven.repo.local={repository}",
            "--version",
        ],
        environment,
    ).splitlines()[0]
    return {
        "java": command_output(["java", "-version"]).splitlines()[0],
        "javac": command_output(["javac", "-version"]).splitlines()[0],
        "maven": maven,
        "python": command_output(["python3", "--version"]).splitlines()[0],
        "git": command_output(["git", "--version"]).splitlines()[0],
        "docker": command_output(
            ["docker", "version", "--format", "{{.Server.Version}}"]
        ).splitlines()[0],
    }


def current_images() -> dict[str, str]:
    return {
        reference: command_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}", reference]
        ).splitlines()[0]
        for reference in IMAGE_REFS
    }


def load_marker(path: Path) -> dict[str, object]:
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"준비 상태 파일을 읽을 수 없습니다: {error}")
    if not isinstance(marker, dict):
        fail("준비 상태 파일의 최상위 값은 객체여야 합니다.")
    return marker


def validate_marker_payload(
    marker: Mapping[str, object],
    *,
    fingerprint: str,
    expected_maven_home: Path,
    expected_repository: Path,
    tools: Mapping[str, str],
    images: Mapping[str, str],
    require_cache: bool = True,
) -> None:
    expected_keys = {
        "schema",
        "guide_id",
        "preparation_input_fingerprint",
        "cache",
        "tools",
        "images",
    }
    if set(marker) != expected_keys:
        fail("준비 상태 schema key가 정확하지 않습니다.")
    if marker.get("schema") != 1 or marker.get("guide_id") != GUIDE_ID:
        fail("준비 상태 schema 또는 guide ID가 다릅니다.")
    if marker.get("preparation_input_fingerprint") != fingerprint:
        fail("준비 입력 fingerprint가 현재 working tree와 다릅니다.")

    cache = marker.get("cache")
    if not isinstance(cache, dict) or set(cache) != {"maven_home", "maven_repository"}:
        fail("준비 상태 cache schema가 정확하지 않습니다.")
    expected_cache = {
        "maven_home": str(expected_maven_home),
        "maven_repository": str(expected_repository),
    }
    if cache != expected_cache:
        fail("준비 상태 cache 경로가 정확하지 않습니다.")
    if require_cache:
        for path in (expected_maven_home, expected_repository):
            if path.is_symlink() or not path.is_dir():
                fail(f"준비된 Maven cache가 없습니다: {path}")

    marker_tools = marker.get("tools")
    expected_tool_keys = {"java", "javac", "maven", "python", "git", "docker"}
    if not isinstance(marker_tools, dict) or set(marker_tools) != expected_tool_keys:
        fail("준비 상태 tool schema가 정확하지 않습니다.")
    if dict(marker_tools) != dict(tools):
        fail("준비 상태 tool version이 현재 실행 환경과 다릅니다.")
    if re.match(r"^Apache Maven 3[.]9[.]16(?:\s|$)", tools["maven"]) is None:
        fail("Apache Maven 3.9.16 준비 상태가 아닙니다.")
    if re.match(r'^(?:openjdk|java) version "21(?:[.]|\")', tools["java"]) is None:
        fail("JDK 21 준비 상태가 아닙니다.")
    if re.match(r"^javac 21(?:[.]|$)", tools["javac"]) is None:
        fail("javac 21 준비 상태가 아닙니다.")

    marker_images = marker.get("images")
    if not isinstance(marker_images, dict) or set(marker_images) != set(IMAGE_REFS):
        fail("준비 상태 Docker image reference schema가 정확하지 않습니다.")
    if dict(marker_images) != dict(images):
        fail("준비 상태 Docker image ID가 현재 daemon과 다릅니다.")
    for image_id in marker_images.values():
        if not isinstance(image_id, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
            fail("준비 상태 Docker image ID 형식이 올바르지 않습니다.")


def validate_marker(path: Path, root: Path, fingerprint: str) -> dict[str, object]:
    state_dir = root / ".guide" / GUIDE_ID
    expected_marker = state_dir / "prepared.json"
    if path.absolute() != expected_marker.absolute():
        fail("준비 상태 파일 경로가 guide namespace와 다릅니다.")
    maven_home = state_dir / "maven-home"
    repository = state_dir / "m2"
    marker = load_marker(path)
    tools = current_tools(root, maven_home, repository)
    images = current_images()
    validate_marker_payload(
        marker,
        fingerprint=fingerprint,
        expected_maven_home=maven_home,
        expected_repository=repository,
        tools=tools,
        images=images,
    )
    return marker


def write_marker(path: Path, root: Path, fingerprint: str) -> None:
    state_dir = root / ".guide" / GUIDE_ID
    expected_marker = state_dir / "prepared.json"
    if path.absolute() != expected_marker.absolute():
        fail("준비 상태 파일 경로가 guide namespace와 다릅니다.")
    maven_home = state_dir / "maven-home"
    repository = state_dir / "m2"
    if maven_home.is_symlink() or repository.is_symlink():
        fail("Maven cache 경로는 symlink일 수 없습니다.")
    maven_home.mkdir(parents=True, exist_ok=True)
    repository.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "guide_id": GUIDE_ID,
        "preparation_input_fingerprint": fingerprint,
        "cache": {
            "maven_home": str(maven_home),
            "maven_repository": str(repository),
        },
        "tools": current_tools(root, maven_home, repository),
        "images": current_images(),
    }
    validate_marker_payload(
        payload,
        fingerprint=fingerprint,
        expected_maven_home=maven_home,
        expected_repository=repository,
        tools=payload["tools"],
        images=payload["images"],
    )
    state_dir.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.chmod(0o600)
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("capture", "manifest"):
        command = commands.add_parser(name)
        command.add_argument("root", type=Path)
    copy = commands.add_parser("copy")
    copy.add_argument("root", type=Path)
    copy.add_argument("destination", type=Path)
    index = commands.add_parser("index-state")
    index.add_argument("root", type=Path)
    marker = commands.add_parser("validate-marker")
    marker.add_argument("path", type=Path)
    marker.add_argument("root", type=Path)
    marker.add_argument("fingerprint")
    write = commands.add_parser("write-marker")
    write.add_argument("path", type=Path)
    write.add_argument("root", type=Path)
    write.add_argument("fingerprint")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if arguments.command == "capture":
        print(capture(arguments.root.resolve()))
    elif arguments.command == "manifest":
        for entry in source_entries(arguments.root.resolve()):
            print(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
    elif arguments.command == "copy":
        copy_source(arguments.root.resolve(), arguments.destination.resolve())
    elif arguments.command == "index-state":
        print(json.dumps(git_index_state(arguments.root.resolve()), sort_keys=True))
    elif arguments.command == "validate-marker":
        marker = validate_marker(
            arguments.path.absolute(), arguments.root.resolve(), arguments.fingerprint
        )
        cache = marker["cache"]
        print(f"{cache['maven_home']}\t{cache['maven_repository']}")
    elif arguments.command == "write-marker":
        write_marker(
            arguments.path.absolute(), arguments.root.resolve(), arguments.fingerprint
        )
    else:
        fail(f"지원하지 않는 명령입니다: {arguments.command}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.stderr.close()
        raise SystemExit(1)
