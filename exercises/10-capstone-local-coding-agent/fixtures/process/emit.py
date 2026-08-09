from __future__ import annotations

import sys


sys.stdout.buffer.write("stdout: 안녕\n".encode("utf-8") + b"bad:\xff\n")
sys.stdout.flush()
sys.stderr.write("stderr: fixture\n")
raise SystemExit(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
