"""Stage 01 starter: provider-neutral model adapters."""

from typing import Protocol

INCOMPLETE_STAGE = "01"


def parse_action(value):
    raise NotImplementedError("TODO(stage-01): parse one strict action")


class ModelAdapter(Protocol):
    def stream(self, request): ...


class ScriptedModelAdapter:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("TODO(stage-01): implement deterministic scripted turns")


class HttpModelAdapter:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("TODO(stage-01): implement bounded injectable HTTP transport")
