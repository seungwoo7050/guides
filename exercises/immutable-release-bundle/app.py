from __future__ import annotations

import json


# [Implementation 1] Deterministic application payload
def main() -> int:
    print(json.dumps({"status": "ready"}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
