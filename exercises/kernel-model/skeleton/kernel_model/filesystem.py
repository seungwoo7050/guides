"""파일 이름, inode와 durable 상태의 학습자 구현 골격입니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class FileSystemError(ValueError):
    pass


@dataclass
class Inode:
    inode_id: int
    cached_data: str
    durable_data: str = ""
    dirty: bool = True
    links: int = 0


@dataclass
class FileSystemModel:
    directory: dict[str, int] = field(default_factory=dict)
    durable_directory: dict[str, int] = field(default_factory=dict)
    inodes: dict[int, Inode] = field(default_factory=dict)
    directory_dirty: bool = False
    _next_inode: int = 1

    def create(self, name: str, data: str = "") -> int:
        raise NotImplementedError("이름과 inode를 만들고 directory를 dirty로 표시하세요.")

    def write(self, name: str, data: str) -> None:
        raise NotImplementedError("cached data만 바꾸고 inode를 dirty로 표시하세요.")

    def read(self, name: str) -> str:
        raise NotImplementedError("현재 directory가 가리키는 cached data를 반환하세요.")

    def rename(self, old: str, new: str) -> None:
        raise NotImplementedError("inode는 유지하고 이름 매핑만 바꾸세요.")

    def link(self, existing: str, new: str) -> None:
        raise NotImplementedError("같은 inode를 가리키는 새 이름과 link count를 만드세요.")

    def unlink(self, name: str) -> None:
        raise NotImplementedError("이름을 제거하고 안전할 때 inode를 회수하세요.")

    def fsync_file(self, name: str) -> None:
        raise NotImplementedError("cached data를 durable data로 반영하세요.")

    def fsync_directory(self) -> None:
        raise NotImplementedError("현재 이름 매핑을 durable directory로 반영하세요.")

    def crash_recover(self) -> None:
        raise NotImplementedError("durable 상태만 남긴 장애 뒤 상태를 만드세요.")

    def apply_operation(self, operation: Mapping[str, Any]) -> None:
        raise NotImplementedError("저널이 재생할 수 있는 멱등 연산을 구현하세요.")

    def snapshot(self) -> dict[str, Any]:
        raise NotImplementedError("파일시스템 상태를 직렬화하세요.")

    def assert_invariants(self) -> None:
        raise NotImplementedError("directory 참조와 inode link count를 비교하세요.")

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        raise NotImplementedError("snapshot을 복원하고 불변식을 검사하세요.")
