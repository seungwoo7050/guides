from __future__ import annotations

from .diagnostic import Diagnostic


def lint(semantic_model: object) -> list[Diagnostic]:
    del semantic_model
    raise NotImplementedError("Exercise 07: implement stable semantic lint rules")
