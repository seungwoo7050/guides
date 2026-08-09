"""Completed support helpers; these are not learner TODOs."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def value_digest(value: Any) -> str:
    return sha256_text(canonical_json(value))
