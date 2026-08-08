from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def deploy(state_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """의도적으로 잘못된 시작 구현입니다. 계약에 맞게 수정합니다."""
    state_dir.mkdir(parents=True, exist_ok=True)
    current_path = state_dir / "current.json"
    previous = json.loads(current_path.read_text(encoding="utf-8")) if current_path.exists() else {}
    current_path.write_text(
        json.dumps({"current": manifest.get("release_id"), "previous": previous.get("current")}),
        encoding="utf-8",
    )
    return {"status": "success", "phase": "committed"}
