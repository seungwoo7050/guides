from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Span:
    source_id: str
    start: int
    end: int

    def validate(self, byte_length: int) -> None:
        if not (0 <= self.start <= self.end <= byte_length):
            raise ValueError(f"invalid span [{self.start}, {self.end}) for {byte_length} bytes")


@dataclass(frozen=True, slots=True)
class SourceText:
    source_id: str
    text: str
    data: bytes

    @classmethod
    def read(cls, path: Path) -> "SourceText":
        data = path.read_bytes()
        text = data.decode("utf-8")
        return cls(source_id=str(path), text=text, data=data)

    @property
    def byte_length(self) -> int:
        return len(self.data)
