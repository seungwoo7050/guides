"""이름, inode, 페이지 캐시와 durable 상태를 분리한 파일시스템 모델입니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class FileSystemError(ValueError):
    """파일시스템 계약이나 불변식이 깨질 때 발생합니다."""


# [Implementation 6] Inode와 FileSystemModel은 현재 namespace/cache와 durable namespace/data를 서로 다른 상태 owner로 둡니다.
@dataclass
class Inode:
    inode_id: int
    cached_data: str
    durable_data: str = ""
    dirty: bool = True
    links: int = 0


@dataclass
class FileSystemModel:
    """메모리에 보이는 상태와 장애 뒤 남는 상태를 따로 관리합니다."""

    directory: dict[str, int] = field(default_factory=dict)
    durable_directory: dict[str, int] = field(default_factory=dict)
    inodes: dict[int, Inode] = field(default_factory=dict)
    directory_dirty: bool = False
    _next_inode: int = 1

    # [Implementation 6-1] create/write/rename/link/unlink는 live namespace와 inode link count를 한 operation 경계에서 갱신합니다.
    def create(self, name: str, data: str = "") -> int:
        self._validate_name(name)
        if name in self.directory:
            raise FileSystemError(f"이미 존재하는 이름입니다: {name}")
        inode_id = self._next_inode
        self._next_inode += 1
        inode = Inode(inode_id=inode_id, cached_data=data, dirty=True, links=1)
        self.inodes[inode_id] = inode
        self.directory[name] = inode_id
        self.directory_dirty = True
        self.assert_invariants()
        return inode_id

    def write(self, name: str, data: str) -> None:
        inode = self._inode_for_name(name)
        inode.cached_data = data
        inode.dirty = inode.cached_data != inode.durable_data
        self.assert_invariants()

    def read(self, name: str) -> str:
        return self._inode_for_name(name).cached_data

    def rename(self, old: str, new: str) -> None:
        self._validate_name(new)
        if old not in self.directory:
            raise FileSystemError(f"이름을 찾을 수 없습니다: {old}")
        if new in self.directory:
            raise FileSystemError(f"대상 이름이 이미 존재합니다: {new}")
        inode_id = self.directory.pop(old)
        self.directory[new] = inode_id
        self.directory_dirty = True
        self.assert_invariants()

    def link(self, existing: str, new: str) -> None:
        self._validate_name(new)
        if new in self.directory:
            raise FileSystemError(f"대상 이름이 이미 존재합니다: {new}")
        inode = self._inode_for_name(existing)
        self.directory[new] = inode.inode_id
        inode.links += 1
        self.directory_dirty = True
        self.assert_invariants()

    def unlink(self, name: str) -> None:
        if name not in self.directory:
            raise FileSystemError(f"이름을 찾을 수 없습니다: {name}")
        inode_id = self.directory.pop(name)
        inode = self.inodes[inode_id]
        inode.links -= 1
        self.directory_dirty = True
        if inode.links == 0 and inode_id not in self.durable_directory.values():
            self.inodes.pop(inode_id)
        self.assert_invariants()

    # [Implementation 6-2] file fsync와 directory fsync를 분리해 data durability, name durability와 crash recovery 가능 상태를 구분합니다.
    def fsync_file(self, name: str) -> None:
        inode = self._inode_for_name(name)
        inode.durable_data = inode.cached_data
        inode.dirty = False
        self.assert_invariants()

    def fsync_directory(self) -> None:
        self.durable_directory = dict(self.directory)
        self.directory_dirty = False
        self._recompute_links()
        self._collect_unreferenced()
        self.assert_invariants()

    def crash_recover(self) -> None:
        """durable directory와 durable data만 남긴 장애 뒤 상태를 만듭니다."""

        self.directory = dict(self.durable_directory)
        durable_ids = set(self.directory.values())
        for inode_id in list(self.inodes):
            if inode_id not in durable_ids:
                self.inodes.pop(inode_id)
                continue
            inode = self.inodes[inode_id]
            inode.cached_data = inode.durable_data
            inode.dirty = False
        self.directory_dirty = False
        self._recompute_links()
        self.assert_invariants()

    # [Implementation 6-3] journal replay가 호출하는 작은 operation 경계는 retry와 중복 적용 정책을 각 mutation에 명시합니다.
    def apply_operation(self, operation: Mapping[str, Any]) -> None:
        """저널 복구가 재생할 수 있는 작은 메타데이터 연산 집합입니다."""

        kind = operation.get("op")
        if kind == "create":
            name = str(operation["name"])
            if name not in self.directory:
                self.create(name, str(operation.get("data", "")))
        elif kind == "write":
            name = str(operation["name"])
            data = str(operation.get("data", ""))
            if name not in self.directory:
                raise FileSystemError(f"write 대상이 없습니다: {name}")
            self.write(name, data)
        elif kind == "rename":
            old = str(operation["old"])
            new = str(operation["new"])
            if old in self.directory and new not in self.directory:
                self.rename(old, new)
            elif new not in self.directory:
                raise FileSystemError(f"rename 복구 상태가 모호합니다: {old} -> {new}")
        elif kind == "unlink":
            name = str(operation["name"])
            if name in self.directory:
                self.unlink(name)
        elif kind == "fsync-file":
            self.fsync_file(str(operation["name"]))
        elif kind == "fsync-directory":
            self.fsync_directory()
        else:
            raise FileSystemError(f"지원하지 않는 파일시스템 연산입니다: {kind}")

    # [Implementation 6-4] snapshot은 live/durable 관찰을 함께 노출하되 내부 object identity를 public expected 결과로 만들지 않습니다.
    def snapshot(self) -> dict[str, Any]:
        return {
            "directory": dict(sorted(self.directory.items())),
            "durable_directory": dict(sorted(self.durable_directory.items())),
            "directory_dirty": self.directory_dirty,
            "inodes": {
                str(inode_id): {
                    "cached_data": inode.cached_data,
                    "durable_data": inode.durable_data,
                    "dirty": inode.dirty,
                    "links": inode.links,
                }
                for inode_id, inode in sorted(self.inodes.items())
            },
        }

    # [Implementation 6-5] namespace reachability, link count와 clean data의 durable 일치를 검사하고 외부 snapshot에도 같은 규칙을 적용합니다.
    def assert_invariants(self) -> None:
        for name, inode_id in self.directory.items():
            self._validate_name(name)
            if inode_id not in self.inodes:
                raise FileSystemError(f"디렉터리가 없는 inode를 가리킵니다: {name}")
        for name, inode_id in self.durable_directory.items():
            self._validate_name(name)
            if inode_id not in self.inodes:
                raise FileSystemError(f"durable directory가 없는 inode를 가리킵니다: {name}")
        live_counts: dict[int, int] = {inode_id: 0 for inode_id in self.inodes}
        for inode_id in self.directory.values():
            live_counts[inode_id] = live_counts.get(inode_id, 0) + 1
        for inode_id, inode in self.inodes.items():
            if inode.links != live_counts.get(inode_id, 0):
                raise FileSystemError(
                    f"inode link 수가 현재 디렉터리와 다릅니다: inode={inode_id} stored={inode.links} actual={live_counts.get(inode_id, 0)}"
                )
            if inode.links == 0 and inode_id not in self.durable_directory.values():
                raise FileSystemError(f"어디에서도 참조하지 않는 inode가 남아 있습니다: {inode_id}")
            if not inode.dirty and inode.cached_data != inode.durable_data:
                raise FileSystemError(f"clean inode의 cache와 durable data가 다릅니다: {inode_id}")

    @classmethod
    def validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        raw_directory = snapshot.get("directory")
        raw_durable = snapshot.get("durable_directory")
        raw_inodes = snapshot.get("inodes")
        if not isinstance(raw_directory, Mapping) or not isinstance(raw_durable, Mapping) or not isinstance(raw_inodes, Mapping):
            raise FileSystemError("filesystem snapshot 형식이 잘못되었습니다.")
        model = cls()
        model.directory = {str(name): int(inode_id) for name, inode_id in raw_directory.items()}
        model.durable_directory = {str(name): int(inode_id) for name, inode_id in raw_durable.items()}
        model.directory_dirty = bool(snapshot.get("directory_dirty", False))
        model.inodes = {}
        for raw_id, raw in raw_inodes.items():
            if not isinstance(raw, Mapping):
                raise FileSystemError("inode 항목 형식이 잘못되었습니다.")
            inode_id = int(raw_id)
            model.inodes[inode_id] = Inode(
                inode_id=inode_id,
                cached_data=str(raw.get("cached_data", "")),
                durable_data=str(raw.get("durable_data", "")),
                dirty=bool(raw.get("dirty", False)),
                links=int(raw.get("links", 0)),
            )
        model._next_inode = max(model.inodes, default=0) + 1
        model.assert_invariants()

    def _inode_for_name(self, name: str) -> Inode:
        try:
            return self.inodes[self.directory[name]]
        except KeyError as exc:
            raise FileSystemError(f"이름을 찾을 수 없습니다: {name}") from exc

    def _recompute_links(self) -> None:
        for inode in self.inodes.values():
            inode.links = 0
        for inode_id in self.directory.values():
            self.inodes[inode_id].links += 1

    def _collect_unreferenced(self) -> None:
        protected = set(self.durable_directory.values())
        for inode_id in list(self.inodes):
            if self.inodes[inode_id].links == 0 and inode_id not in protected:
                self.inodes.pop(inode_id)

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or "/" in name or name in {".", ".."}:
            raise FileSystemError(f"단일 디렉터리 이름이 유효하지 않습니다: {name!r}")
