#!/usr/bin/env python3
from urllib.request import urlopen

# [Implementation 3] app process 내부에서만 사용하는 bounded readiness probe입니다.
with urlopen("http://127.0.0.1:8080/healthz", timeout=1) as response:
    if response.status != 200 or response.read().strip() != b"ok":
        raise SystemExit(1)
