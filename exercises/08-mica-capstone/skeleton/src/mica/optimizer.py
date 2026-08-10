from __future__ import annotations


def optimize(module: object) -> tuple[object, list[str]]:
    """Return verified optimized IR and the names of changed passes."""
    del module
    raise NotImplementedError("Exercise 05: implement verifier-backed meaning-preserving passes")
