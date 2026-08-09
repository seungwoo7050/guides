#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from source_fingerprint import ROOT, fingerprint


def main() -> int:
    if sys.version_info < (3, 12):
        raise SystemExit("Python 3.12 이상이 필요합니다.")
    result = fingerprint()
    marker = ROOT / ".guide" / "distributed-systems" / "prepared.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({
        "guide": "distributed-systems",
        "python": ".".join(map(str, sys.version_info[:3])),
        "source_sha256": result["source_sha256"],
        "file_count": result["file_count"],
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PREPARED {result['file_count']} files {result['source_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
