#!/usr/bin/env python3
"""Reject tracked secrets, dependency/cache output, and unsafe repository entries."""

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
MAX_TRACKED_BYTES = 5 * 1024 * 1024
TEXT_SCAN_BYTES = 2 * 1024 * 1024

FORBIDDEN_PARTS = {
    ".guide",
    ".workspace",
    ".agent-state",
    ".verifier",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".venv",
    "venv",
    "node_modules",
    "htmlcov",
    "build",
    "dist",
    "target",
}
FORBIDDEN_NAMES = {".DS_Store", ".coverage", "coverage.xml", ".env"}
FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".keystore",
    ".jks",
}
REQUIRED_EXECUTABLES = {
    "prepare.sh",
    "verify.sh",
    "scripts/check_docs.py",
    "scripts/check_contracts.py",
    "scripts/check_repository.py",
    "scripts/source_fingerprint.py",
}

SECRET_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{12,}\b")),
)
GENERIC_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)\b"
    r"\s*[:=]\s*[\"']?([^\s\"'`,;]{16,})"
)
SAFE_ASSIGNMENT_MARKERS = {"example", "fixture", "fake", "dummy", "placeholder", "replace", "redacted", "test-only"}


def fail(messages: list[str]) -> None:
    for message in messages:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _git(*arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        fail([f"Git 검사를 실행할 수 없습니다: {detail}"])
    return completed.stdout


def tracked_entries() -> list[tuple[str, str, str]]:
    raw = _git("ls-files", "-s", "-z")
    result: list[tuple[str, str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, separator, path_raw = record.partition(b"\t")
        if not separator:
            fail(["git ls-files가 잘못된 record를 반환했습니다."])
        fields = metadata.decode("ascii").split()
        if len(fields) != 3:
            fail(["git index metadata를 해석할 수 없습니다."])
        result.append((path_raw.decode("utf-8", "surrogateescape"), fields[0], fields[1]))
    return result


def _looks_binary(value: bytes) -> bool:
    return b"\0" in value[:8192]


def _secret_findings(path: str, value: bytes) -> list[str]:
    if _looks_binary(value):
        return []
    text = value.decode("utf-8", "replace")
    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"{path}: 추적된 {label} 형태의 secret")
    for match in GENERIC_ASSIGNMENT.finditer(text):
        candidate = match.group(1).lower()
        if not any(marker in candidate for marker in SAFE_ASSIGNMENT_MARKERS):
            findings.append(f"{path}: 실제 값처럼 보이는 credential assignment")
            break
    return findings


def main() -> None:
    top = Path(_git("rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != ROOT.resolve():
        fail([f"검사는 저장소 root에서 실행해야 합니다: expected={ROOT} actual={top}"])

    problems: list[str] = []
    total_bytes = 0
    entries = tracked_entries()
    for relative, index_mode, object_id in entries:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            problems.append(f"안전하지 않은 추적 경로: {relative}")
            continue
        if FORBIDDEN_PARTS.intersection(pure.parts):
            problems.append(f"cache/dependency/learner output이 추적됨: {relative}")
        if pure.name in FORBIDDEN_NAMES or pure.name.startswith(".coverage."):
            problems.append(f"generated/secret 파일이 추적됨: {relative}")
        if pure.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(f"generated/credential 확장자가 추적됨: {relative}")
        if pure.name.startswith(".env.") and pure.name not in {".env.example", ".env.sample"}:
            problems.append(f"환경 credential 파일이 추적됨: {relative}")

        path = ROOT / relative
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            problems.append(f"index의 파일이 worktree에 없음: {relative}")
            continue

        if index_mode == "160000":
            problems.append(f"검증할 수 없는 submodule이 추적됨: {relative}")
            continue
        if stat.S_ISLNK(metadata.st_mode):
            if index_mode != "120000":
                problems.append(f"symlink mode가 index와 다름: {relative}")
            try:
                target = _git("cat-file", "blob", object_id).decode("utf-8", "surrogateescape")
            except UnicodeDecodeError:
                problems.append(f"symlink target을 해석할 수 없음: {relative}")
                continue
            if PurePosixPath(target).is_absolute():
                problems.append(f"절대 symlink는 격리 복사에서 허용되지 않음: {relative} -> {target}")
                continue
            resolved = (path.parent / target).resolve(strict=False)
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                problems.append(f"저장소 밖을 가리키는 symlink: {relative} -> {target}")
            continue
        if not stat.S_ISREG(metadata.st_mode):
            problems.append(f"regular file이 아닌 항목이 추적됨: {relative}")
            continue
        if index_mode == "120000":
            problems.append(f"index symlink가 worktree regular file과 다름: {relative}")

        try:
            size = int(_git("cat-file", "-s", object_id).decode("ascii").strip())
        except ValueError:
            problems.append(f"Git blob 크기를 해석할 수 없음: {relative}")
            continue
        total_bytes += size
        if size > MAX_TRACKED_BYTES:
            problems.append(f"대용량 파일이 추적됨: {relative} ({size} bytes > {MAX_TRACKED_BYTES})")
        if size <= TEXT_SCAN_BYTES:
            try:
                problems.extend(_secret_findings(relative, _git("cat-file", "blob", object_id)))
            except OSError as exc:
                problems.append(f"secret scan 실패: {relative}: {exc}")

        if relative in REQUIRED_EXECUTABLES and index_mode != "100755":
            problems.append(f"필수 실행 파일의 Git mode가 100755가 아님: {relative} ({index_mode})")

    for relative in REQUIRED_EXECUTABLES:
        if relative not in {path for path, _mode, _object_id in entries}:
            problems.append(f"필수 검증 스크립트가 추적되지 않음: {relative}")

    if problems:
        fail(sorted(set(problems)))
    print(f"REPOSITORY OK tracked={len(entries)} bytes={total_bytes} secrets=0 generated=0")


if __name__ == "__main__":
    main()
