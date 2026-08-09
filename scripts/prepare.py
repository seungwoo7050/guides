#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from path_safety import UnsafePathError, atomic_write_text, require_no_symlink_components
from source_fingerprint import ROOT, fingerprint


def main() -> int:
    if sys.version_info < (3, 12):
        raise SystemExit("Python 3.12 이상이 필요합니다.")
    result = fingerprint()
    generated_root = ROOT / ".guide"
    marker_directory = generated_root / "distributed-systems"
    marker = marker_directory / "prepared.json"
    try:
        require_no_symlink_components(marker, boundary=ROOT)
        marker_directory.mkdir(parents=True, exist_ok=True)
        require_no_symlink_components(marker, boundary=ROOT)
    except UnsafePathError as exc:
        raise SystemExit(f"unsafe prepare path: {exc}") from exc
    payload = json.dumps({
        "guide": "distributed-systems",
        "python": ".".join(map(str, sys.version_info[:3])),
        "source_sha256": result["source_sha256"],
        "file_count": result["file_count"],
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        atomic_write_text(marker, payload, boundary=ROOT)
    except UnsafePathError as exc:
        raise SystemExit(f"unsafe prepare path: {exc}") from exc
    print(f"PREPARED {result['file_count']} files {result['source_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
