from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


marker = Path(sys.argv[2])
if sys.argv[1] == "child":
    marker.write_text(str(os.getpid()), encoding="utf-8")

    def stop(_signum: int, _frame: object) -> None:
        marker.unlink(missing_ok=True)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    while True:
        time.sleep(1)

subprocess.Popen(
    (sys.executable, __file__, "child", str(marker)),
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
deadline = time.monotonic() + 2
while not marker.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
