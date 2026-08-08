#!/usr/bin/env python3
"""Create and publish a prepare marker without following untrusted paths."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import re
import stat
import sys
from typing import Iterator


NAME_PATTERNS = {
    "prepared": re.compile(r"^\.prepared\.[A-Za-z0-9]{6}$"),
}


def directory_flags() -> int:
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("O_DIRECTORY와 O_NOFOLLOW를 모두 지원해야 합니다")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def validate_arguments(root: Path, guide_id: str) -> Path:
    if not root.is_absolute() or root != root.resolve(strict=True):
        raise RuntimeError("저장소 루트는 canonical absolute path여야 합니다")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", guide_id):
        raise RuntimeError("guide ID가 안전한 단일 path component가 아닙니다")
    return root / ".guide" / guide_id


def matching_metadata(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def verify_directory_entry(parent_fd: int, name: str, descriptor: int) -> None:
    path_state = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    descriptor_state = os.fstat(descriptor)
    if not stat.S_ISDIR(path_state.st_mode) or not matching_metadata(path_state, descriptor_state):
        raise RuntimeError(f"실제 directory identity가 바뀌었습니다: {name}")


@contextmanager
def open_state_directory(root: Path, guide_id: str, *, create: bool) -> Iterator[int]:
    expected = validate_arguments(root, guide_id)
    flags = directory_flags()
    descriptors: list[int] = []
    try:
        root_fd = os.open(root, flags)
        descriptors.append(root_fd)
        if create:
            try:
                os.mkdir(".guide", 0o700, dir_fd=root_fd)
                os.fsync(root_fd)
            except FileExistsError:
                pass
        state_fd = os.open(".guide", flags, dir_fd=root_fd)
        descriptors.append(state_fd)
        verify_directory_entry(root_fd, ".guide", state_fd)
        if create:
            try:
                os.mkdir(guide_id, 0o700, dir_fd=state_fd)
                os.fsync(state_fd)
            except FileExistsError:
                pass
        guide_fd = os.open(guide_id, flags, dir_fd=state_fd)
        descriptors.append(guide_fd)
        verify_directory_entry(state_fd, guide_id, guide_fd)
        if expected.parent.resolve(strict=True) != expected.parent:
            raise RuntimeError(".guide가 저장소 안의 실제 directory가 아닙니다")
        if expected.resolve(strict=True) != expected:
            raise RuntimeError("guide-id 상태 경로가 실제 directory가 아닙니다")
        yield guide_fd
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def parse_identity(value: str) -> tuple[int, int]:
    try:
        device, inode = value.split(":", 1)
        return int(device), int(inode)
    except (TypeError, ValueError) as error:
        raise RuntimeError("임시 파일 identity 형식이 올바르지 않습니다") from error


def candidate_name(root: Path, guide_id: str, candidate: Path, kind: str) -> str:
    expected_parent = validate_arguments(root, guide_id)
    if not candidate.is_absolute() or candidate.parent != expected_parent:
        raise RuntimeError("mktemp 반환 경로가 lexical marker sibling이 아닙니다")
    if expected_parent.resolve(strict=True) != expected_parent:
        raise RuntimeError("mktemp 반환 경로의 실제 parent가 상태 directory가 아닙니다")
    pattern = NAME_PATTERNS[kind]
    if pattern.fullmatch(candidate.name) is None:
        raise RuntimeError("mktemp 반환 파일 이름이 요청한 무작위 형식이 아닙니다")
    return candidate.name


def safe_file_state(
    guide_fd: int,
    name: str,
    *,
    identity: tuple[int, int] | None = None,
) -> os.stat_result:
    metadata = os.stat(name, dir_fd=guide_fd, follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise RuntimeError("임시 marker는 hard link가 없는 regular file이어야 합니다")
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise RuntimeError("임시 marker owner 또는 mode가 안전하지 않습니다")
    if identity is not None and (metadata.st_dev, metadata.st_ino) != identity:
        raise RuntimeError("임시 marker identity가 검증 이후 바뀌었습니다")
    return metadata


def ensure_directories(root: Path, guide_id: str) -> None:
    with open_state_directory(root, guide_id, create=True):
        pass


def check_final(root: Path, guide_id: str) -> None:
    with open_state_directory(root, guide_id, create=False) as guide_fd:
        try:
            metadata = os.stat("prepared.json", dir_fd=guide_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.geteuid()
        ):
            raise RuntimeError("기존 final marker는 소유한 regular file이어야 합니다")


def claim(root: Path, guide_id: str, candidate: Path, kind: str) -> None:
    name = candidate_name(root, guide_id, candidate, kind)
    path_state = candidate.lstat()
    with open_state_directory(root, guide_id, create=False) as guide_fd:
        metadata = safe_file_state(guide_fd, name)
        if not matching_metadata(path_state, metadata):
            raise RuntimeError("mktemp 반환 경로와 상태 directory entry가 다릅니다")
    print(f"{metadata.st_dev}:{metadata.st_ino}")


def write(root: Path, guide_id: str, candidate: Path, kind: str, identity: str) -> None:
    name = candidate_name(root, guide_id, candidate, kind)
    expected = parse_identity(identity)
    data = sys.stdin.buffer.read()
    with open_state_directory(root, guide_id, create=False) as guide_fd:
        path_state = safe_file_state(guide_fd, name, identity=expected)
        descriptor = os.open(name, os.O_WRONLY | os.O_NOFOLLOW, dir_fd=guide_fd)
        try:
            descriptor_state = os.fstat(descriptor)
            if (
                not matching_metadata(path_state, descriptor_state)
                or (descriptor_state.st_dev, descriptor_state.st_ino) != expected
                or not stat.S_ISREG(descriptor_state.st_mode)
                or descriptor_state.st_nlink != 1
            ):
                raise RuntimeError("쓰기 직전 임시 marker identity가 바뀌었습니다")
            os.ftruncate(descriptor, 0)
            os.fchmod(descriptor, 0o600)
            view = memoryview(data)
            while view:
                view = view[os.write(descriptor, view) :]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def publish(root: Path, guide_id: str, candidate: Path, kind: str, identity: str) -> None:
    name = candidate_name(root, guide_id, candidate, kind)
    expected = parse_identity(identity)
    with open_state_directory(root, guide_id, create=False) as guide_fd:
        safe_file_state(guide_fd, name, identity=expected)
        check_final_metadata: os.stat_result | None
        try:
            check_final_metadata = os.stat(
                "prepared.json", dir_fd=guide_fd, follow_symlinks=False
            )
        except FileNotFoundError:
            check_final_metadata = None
        if check_final_metadata is not None and (
            not stat.S_ISREG(check_final_metadata.st_mode)
            or check_final_metadata.st_nlink != 1
            or check_final_metadata.st_uid != os.geteuid()
        ):
            raise RuntimeError("final marker가 안전한 regular file이 아닙니다")
        os.replace(name, "prepared.json", src_dir_fd=guide_fd, dst_dir_fd=guide_fd)
        os.fsync(guide_fd)


def remove(root: Path, guide_id: str, candidate: Path, kind: str, identity: str) -> None:
    name = candidate_name(root, guide_id, candidate, kind)
    expected = parse_identity(identity)
    with open_state_directory(root, guide_id, create=False) as guide_fd:
        try:
            safe_file_state(guide_fd, name, identity=expected)
        except FileNotFoundError:
            return
        os.unlink(name, dir_fd=guide_fd)
        os.fsync(guide_fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("ensure", "check-final", "claim", "write", "publish", "remove"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--guide-id", required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--kind", choices=tuple(NAME_PATTERNS), default="prepared")
    parser.add_argument("--identity")
    arguments = parser.parse_args()
    try:
        if arguments.action == "ensure":
            ensure_directories(arguments.root, arguments.guide_id)
        elif arguments.action == "check-final":
            check_final(arguments.root, arguments.guide_id)
        else:
            if arguments.candidate is None:
                raise RuntimeError("candidate 경로가 필요합니다")
            if arguments.action == "claim":
                claim(arguments.root, arguments.guide_id, arguments.candidate, arguments.kind)
            else:
                if arguments.identity is None:
                    raise RuntimeError("검증한 device:inode identity가 필요합니다")
                function = {"write": write, "publish": publish, "remove": remove}[arguments.action]
                function(
                    arguments.root,
                    arguments.guide_id,
                    arguments.candidate,
                    arguments.kind,
                    arguments.identity,
                )
        return 0
    except (OSError, RuntimeError) as error:
        print(f"prepare marker 안전성 실패: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
