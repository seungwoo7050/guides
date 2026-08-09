#!/usr/bin/env python3
"""Create run-level lineage events without depending on a vendor SDK."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class Dataset:
    namespace: str
    name: str
    snapshot: str


@dataclass(frozen=True)
class RunEvent:
    event_type: str
    event_time: str
    run_id: str
    job_namespace: str
    job_name: str
    inputs: tuple[Dataset, ...]
    outputs: tuple[Dataset, ...]
    code_revision: str

    def as_dict(self) -> dict:
        result = asdict(self)
        return result


def build_event(
    *,
    event_type: str,
    run_id: str,
    job_name: str,
    inputs: Iterable[Dataset],
    outputs: Iterable[Dataset],
    code_revision: str,
    event_time: datetime | None = None,
) -> RunEvent:
    if event_type not in {"START", "COMPLETE", "FAIL"}:
        raise ValueError("unsupported event type")
    observed_at = datetime.now(timezone.utc) if event_time is None else event_time
    if (
        not isinstance(observed_at, datetime)
        or observed_at.tzinfo is None
        or observed_at.utcoffset() is None
    ):
        raise ValueError("event_time must be timezone-aware")
    return RunEvent(
        event_type=event_type,
        event_time=observed_at.astimezone(timezone.utc).isoformat(),
        run_id=run_id,
        job_namespace="guides/data-engineering",
        job_name=job_name,
        inputs=tuple(inputs),
        outputs=tuple(outputs),
        code_revision=code_revision,
    )
