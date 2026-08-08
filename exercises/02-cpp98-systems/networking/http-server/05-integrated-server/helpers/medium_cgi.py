#!/usr/bin/env python3
import sys

sys.stdout.buffer.write(b"Status: 200\r\nContent-Type: text/plain\r\n\r\n")
sys.stdout.buffer.write(b"m" * (128 * 1024))
