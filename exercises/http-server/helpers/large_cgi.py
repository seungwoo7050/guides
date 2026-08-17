#!/usr/bin/env python3
import sys
sys.stdout.buffer.write(b"Status: 200\r\nContent-Type: text/plain\r\n\r\n")
sys.stdout.buffer.write(b"x" * (1024 * 1024 + 1))
