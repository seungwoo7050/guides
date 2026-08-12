from __future__ import annotations

import json

# [Implementation 1] image가 실행할 deterministic payload를 가장 작은 runtime 계약으로 둡니다.
print(json.dumps({"status": "ready"}, separators=(",", ":")))
