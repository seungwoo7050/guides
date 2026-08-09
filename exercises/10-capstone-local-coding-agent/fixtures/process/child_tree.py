from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


pid_file = Path(sys.argv[2])
if sys.argv[1] == "child":
    pid_file.write_text(str(os.getpid()), encoding="utf-8")

    def stop(_signum: int, _frame: object) -> None:
        pid_file.unlink(missing_ok=True)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    while True:
        time.sleep(1)

subprocess.Popen(
    (sys.executable, __file__, "child", str(pid_file)),
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
deadline = time.monotonic() + 5
while not pid_file.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
while True:
    time.sleep(1)
