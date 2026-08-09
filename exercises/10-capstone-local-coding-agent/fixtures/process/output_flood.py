from __future__ import annotations

import os


block = b"x" * 16_384
for _ in range(256):
    os.write(1, block)
    os.write(2, block)
