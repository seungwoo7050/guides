#!/usr/bin/env python3
import random
import subprocess
import sys

binary = sys.argv[1]
rng = random.Random(7050)
for size in range(1, 65):
    values = [rng.randrange(0, 100) for _ in range(size)]
    completed = subprocess.run(
        [binary, *map(str, values)], text=True, capture_output=True, check=True
    )
    after = next(line for line in completed.stdout.splitlines() if line.startswith("after:"))
    actual = [int(token) for token in after.split()[1:]]
    if actual != sorted(values):
        raise SystemExit(f"mismatch: {values} -> {actual}")
