#!/usr/bin/env python3
import sys
body = sys.stdin.buffer.read()
sys.stdout.buffer.write(
    b"Status: 200\r\nContent-Type: text/plain\r\n\r\n" + body.upper()
)
