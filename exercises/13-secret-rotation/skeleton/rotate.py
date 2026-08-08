from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


class SecretStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def install(self, name: str, version: str, value: str, validator: Callable[[Path], bool]) -> bool:
        directory = self.root / name
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / version
        path.write_text(value, encoding="utf-8")
        (directory / "current.json").write_text(json.dumps({"version": version}), encoding="utf-8")
        with (self.root / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": "installed", "value": value}) + "\n")
        return validator(path)

    def current(self, name: str) -> dict:
        return json.loads((self.root / name / "current.json").read_text(encoding="utf-8"))

    def retire(self, name: str, version: str) -> None:
        (self.root / name / version).unlink()
