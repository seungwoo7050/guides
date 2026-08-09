"""Capstone starter: the model-facing tool gateway."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .git_adapter import GitAdapter
from .patching import PatchEngine
from .policy import PolicyEngine
from .process import ProcessRunner
from .types import ToolReceipt, ToolRequest


KnowledgeSearch = Callable[[str, Sequence[str], int], Sequence[Mapping[str, Any]]]


class ToolGateway:
    def __init__(
        self,
        workspace: Path,
        *,
        policy: PolicyEngine,
        patch_engine: PatchEngine,
        process_runner: ProcessRunner | None = None,
        git_adapter: GitAdapter | None = None,
        knowledge_search: KnowledgeSearch | None = None,
        state_dir: Path | None = None,
        max_read_bytes: int = 1_000_000,
        max_results: int = 200,
    ) -> None:
        raise NotImplementedError("wire policy before every retrieval or effect")

    def invoke(self, request: ToolRequest) -> ToolReceipt:
        raise NotImplementedError("dispatch lowercase tool IDs and return structured receipts")
