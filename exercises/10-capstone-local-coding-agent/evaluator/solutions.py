"""Evaluator-owned known-good artifacts.

These files are deliberately outside every task repository and agent grant.  They
exist to prove that the fixture is solvable; the runtime never exposes them to a
model or learner workspace.
"""

from __future__ import annotations

from pathlib import Path


SOLUTIONS: dict[str, dict[str, str]] = {
    "token-expiry-boundary": {
        "app/tokens.py": '''def is_token_valid(*, expires_at: int, now: int) -> bool:
    """Return whether a token may still be used."""
    return expires_at > now
''',
        "tests/test_tokens.py": '''import unittest

from app.tokens import is_token_valid


class TokenTest(unittest.TestCase):
    def test_future_token_is_valid(self) -> None:
        self.assertTrue(is_token_valid(expires_at=101, now=100))

    def test_past_token_is_expired(self) -> None:
        self.assertFalse(is_token_valid(expires_at=99, now=100))

    def test_equal_boundary_is_expired(self) -> None:
        self.assertFalse(is_token_valid(expires_at=100, now=100))


if __name__ == "__main__":
    unittest.main()
''',
    },
    "dry-run-multifile": {
        "app/service.py": '''from __future__ import annotations


def apply_setting(
    store: dict[str, str], name: str, value: str, *, dry_run: bool = False
) -> str:
    if dry_run:
        return f"dry-run: would apply {name}={value}"
    store[name] = value
    return f"applied {name}={value}"
''',
        "app/cli.py": '''from __future__ import annotations

import argparse

from .service import apply_setting


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="settings")
    parser.add_argument("--dry-run", action="store_true", help="show the change without applying it")
    parser.add_argument("name")
    parser.add_argument("value")
    return parser


def run(argv: list[str], store: dict[str, str]) -> str:
    args = build_parser().parse_args(argv)
    return apply_setting(store, args.name, args.value, dry_run=args.dry_run)


if __name__ == "__main__":
    import sys

    print(run(sys.argv[1:], {}))
''',
        "README.md": '''# Settings fixture

Apply a setting with `python3 -m app.cli NAME VALUE`.

Use `--dry-run` before `NAME` to print the planned change without mutating the store.
''',
        "tests/test_cli.py": '''import unittest

from app.cli import run


class CliTest(unittest.TestCase):
    def test_normal_apply(self) -> None:
        store: dict[str, str] = {}
        self.assertEqual(run(["color", "blue"], store), "applied color=blue")
        self.assertEqual(store, {"color": "blue"})

    def test_dry_run_does_not_mutate(self) -> None:
        store: dict[str, str] = {}
        self.assertIn("dry-run", run(["--dry-run", "color", "blue"], store))
        self.assertEqual(store, {})


if __name__ == "__main__":
    unittest.main()
''',
    },
    "refresh-token-race": {
        "app/store.py": '''from __future__ import annotations

import threading
from collections.abc import Callable


class RefreshTokenStore:
    def __init__(self) -> None:
        self._used: set[str] = set()
        self._lock = threading.Lock()

    def consume(self, token: str, *, before_commit: Callable[[], None] | None = None) -> bool:
        # The hook deterministically aligns contenders before the atomic section.
        if before_commit is not None:
            before_commit()
        with self._lock:
            if token in self._used:
                return False
            self._used.add(token)
            return True
''',
        "tests/test_store.py": '''import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.store import RefreshTokenStore


class StoreTest(unittest.TestCase):
    def test_token_can_only_be_consumed_once(self) -> None:
        store = RefreshTokenStore()
        self.assertTrue(store.consume("one"))
        self.assertFalse(store.consume("one"))

    def test_concurrent_consumers_have_one_winner(self) -> None:
        store = RefreshTokenStore()
        barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: store.consume("race", before_commit=barrier.wait), range(2)))
        self.assertEqual(sorted(results), [False, True])


if __name__ == "__main__":
    unittest.main()
''',
    },
}


def install_known_good(task_id: str, repository: Path) -> tuple[str, ...]:
    """Install evaluator-owned expected files into a disposable fixture only."""
    changed: list[str] = []
    for relative, content in SOLUTIONS[task_id].items():
        target = repository / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        changed.append(relative)
    return tuple(changed)
