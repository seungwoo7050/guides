#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


# [Implementation 1] ManifestError 하나로 입력 계약과 Git 상태 검증 실패를 호출자에게 전달합니다.
class ManifestError(RuntimeError):
    pass


# [Implementation 2] Git subprocess 경계를 모아 exit code와 stderr를 명세 오류로 변환합니다.
def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        raise ManifestError(f"git {' '.join(args)} failed for {repo}: {detail}")
    return process

# [Implementation 3] 원격 URL 표기 차이만 정규화하고 저장소 identity 자체는 보존합니다.
def normalize_remote(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized


# [Implementation 3-1] 모든 필수 문자열 필드가 비어 있지 않다는 공통 입력 invariant를 둡니다.
def require_string(entry: dict[str, Any], field: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{field} must be a non-empty string")
    return value


# [Implementation 4] 저장소 하나의 remote, clean detached HEAD, annotated tag 연결을 검증합니다.
def verify_repository(entry: dict[str, Any]) -> None:
    name = require_string(entry, "name")
    repo = Path(require_string(entry, "path")).expanduser()
    remote = require_string(entry, "remote")
    tag = require_string(entry, "tag")
    commit = require_string(entry, "commit").lower()

    if not SHA_PATTERN.fullmatch(commit):
        raise ManifestError(f"{name}: commit must be a full 40-character SHA")
    if not repo.is_absolute():
        raise ManifestError(f"{name}: path must be absolute")
    if not repo.is_dir():
        raise ManifestError(f"{name}: repository path does not exist: {repo}")

    inside = git(repo, "rev-parse", "--is-inside-work-tree").stdout.strip()
    if inside != "true":
        raise ManifestError(f"{name}: path is not a Git worktree")

    actual_remote = git(repo, "remote", "get-url", "origin", check=False)
    if actual_remote.returncode != 0:
        raise ManifestError(f"{name}: origin remote is missing")
    if normalize_remote(actual_remote.stdout) != normalize_remote(remote):
        raise ManifestError(f"{name}: origin remote does not match manifest")

    status = git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout
    if status.strip():
        raise ManifestError(f"{name}: worktree is not clean")

    symbolic = git(repo, "symbolic-ref", "-q", "HEAD", check=False)
    if symbolic.returncode == 0:
        raise ManifestError(f"{name}: HEAD must be detached")

    head = git(repo, "rev-parse", "HEAD").stdout.strip().lower()
    if head != commit:
        raise ManifestError(f"{name}: HEAD does not match manifest commit")

    tag_ref = f"refs/tags/{tag}"
    tag_type = git(repo, "cat-file", "-t", tag_ref, check=False)
    if tag_type.returncode != 0:
        raise ManifestError(f"{name}: tag does not exist: {tag}")
    if tag_type.stdout.strip() != "tag":
        raise ManifestError(f"{name}: tag must be annotated: {tag}")

    peeled = git(repo, "rev-parse", f"{tag_ref}^{{}}").stdout.strip().lower()
    if peeled != commit:
        raise ManifestError(f"{name}: annotated tag does not peel to manifest commit")


# [Implementation 5] manifest 전체에서 이름·경로 uniqueness를 소유하고 각 저장소 검증을 위임합니다.
def verify_manifest(path: Path) -> None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestError(f"cannot read manifest: {error}") from error

    if not isinstance(document, dict):
        raise ManifestError("manifest root must be an object")
    repositories = document.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise ManifestError("repositories must be a non-empty array")

    names: set[str] = set()
    paths: set[Path] = set()
    for raw_entry in repositories:
        if not isinstance(raw_entry, dict):
            raise ManifestError("every repository entry must be an object")
        name = require_string(raw_entry, "name")
        if name in names:
            raise ManifestError(f"duplicate repository name: {name}")
        names.add(name)
        repository_path = Path(require_string(raw_entry, "path")).expanduser().resolve()
        if repository_path in paths:
            raise ManifestError(f"duplicate repository path: {repository_path}")
        paths.add(repository_path)
        verify_repository(raw_entry)


# [Implementation 6] CLI 경계가 사용법, 안정적인 exit code, 사람이 읽는 증거를 제공합니다.
def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: manifest_check.py MANIFEST.json", file=sys.stderr)
        return 2
    try:
        verify_manifest(Path(argv[1]))
    except ManifestError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("release manifest verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
