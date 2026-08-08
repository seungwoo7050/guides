#!/usr/bin/env python3
"""Create and validate a learner-owned Spring exercise workspace."""

from __future__ import annotations

import os
import shutil
import stat
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUGS = {
    "application-boundaries",
    "security-boundaries",
    "transaction-locking",
    "idempotency-outbox",
    "kafka-avro-contract",
    "resilient-http-client",
    "single-service-capstone",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def require_slug(raw: str) -> str:
    if raw not in SLUGS:
        fail(f"알 수 없는 실습 slug입니다: {raw}")
    return raw


def workspace_root(*, create: bool) -> Path:
    path = ROOT / ".workspace"
    if path.is_symlink():
        fail(".workspace는 symlink일 수 없습니다.")
    if path.exists() and not path.is_dir():
        fail(".workspace는 directory여야 합니다.")
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    if path.exists() and path.resolve(strict=True) != path.absolute():
        fail(".workspace 실제 경로가 저장소 내부 고정 경로와 다릅니다.")
    return path


def test_map(root: Path) -> dict[str, bytes]:
    source = root / "src/test/java"
    if not source.is_dir():
        return {}
    return {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in sorted(source.rglob("*.java"))
        if path.is_file() and not path.is_symlink()
    }


def replace_parent_path(pom: Path) -> None:
    old = b"<relativePath>../../../pom.xml</relativePath>"
    new = b"<relativePath>../../pom.xml</relativePath>"
    content = pom.read_bytes()
    if content.count(old) != 1:
        fail("workspace POM의 parent relativePath 계약이 다릅니다.")
    temporary = pom.with_name(f".{pom.name}.tmp-{os.getpid()}")
    temporary.write_bytes(content.replace(old, new, 1))
    temporary.chmod(stat.S_IMODE(pom.stat().st_mode))
    os.replace(temporary, pom)


def create_workspace(slug: str) -> Path:
    root = workspace_root(create=True)
    source = ROOT / "exercises" / slug / "skeleton"
    destination = root / slug
    if destination.exists() or destination.is_symlink():
        fail(f"workspace가 이미 존재합니다: {destination}")
    if not source.is_dir() or source.is_symlink():
        fail(f"canonical skeleton이 안전한 directory가 아닙니다: {source}")
    try:
        shutil.copytree(
            source,
            destination,
            symlinks=True,
            copy_function=shutil.copy2,
            ignore=shutil.ignore_patterns("target", "*.class", "*.jar", "*.log"),
        )
        replace_parent_path(destination / "pom.xml")
        validate_workspace(slug)
    except BaseException:
        if destination.exists() and destination.parent == root:
            shutil.rmtree(destination)
        raise
    return destination


def validate_workspace(slug: str) -> Path:
    root = workspace_root(create=False)
    destination = root / slug
    if destination.is_symlink() or not destination.is_dir():
        fail(f"workspace directory가 없습니다: {destination}")
    if destination.resolve(strict=True).parent != root.resolve(strict=True):
        fail("workspace 경로가 .workspace 밖으로 벗어났습니다.")
    for path in destination.rglob("*"):
        if path.is_symlink():
            fail(f"workspace 내부 symlink는 허용하지 않습니다: {path}")

    pom = destination / "pom.xml"
    try:
        project = ET.parse(pom).getroot()
    except (OSError, ET.ParseError) as error:
        fail(f"workspace POM을 읽을 수 없습니다: {error}")
    namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
    relative = project.findtext("./m:parent/m:relativePath", namespaces=namespace)
    artifact = project.findtext("./m:artifactId", namespaces=namespace)
    if relative != "../../pom.xml":
        fail("workspace POM parent가 repository root를 가리키지 않습니다.")
    if artifact != f"{slug}-skeleton":
        fail("workspace artifactId가 canonical skeleton과 다릅니다.")

    canonical_tests = test_map(ROOT / "exercises" / slug / "skeleton")
    workspace_tests = test_map(destination)
    if not canonical_tests or workspace_tests != canonical_tests:
        fail("workspace는 canonical skeleton과 byte-identical 공개 tests를 사용해야 합니다.")
    return destination


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"create", "validate"}:
        fail("사용법: workspace.py create|validate EXERCISE_SLUG")
    command = sys.argv[1]
    slug = require_slug(sys.argv[2])
    path = create_workspace(slug) if command == "create" else validate_workspace(slug)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
