"""Audit a row-level split manifest with entity isolation."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ALLOWED_SPLITS = ("train", "validation", "test")


@dataclass(frozen=True)
class SplitSummary:
    rows: dict[str, int]
    entities: dict[str, int]
    positives: dict[str, int]
    entity_overlap: list[str]
    duplicate_row_ids: list[str]
    missing_manifest_rows: list[str]
    unknown_manifest_rows: list[str]
    invalid_splits: list[str]

    @property
    def valid(self) -> bool:
        return not any(
            (
                self.entity_overlap,
                self.duplicate_row_ids,
                self.missing_manifest_rows,
                self.unknown_manifest_rows,
                self.invalid_splits,
            )
        )

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["valid"] = self.valid
        return data


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader)


def audit_rows(
    rows: Iterable[dict[str, str]],
    manifest_rows: Iterable[dict[str, str]],
) -> SplitSummary:
    data = list(rows)
    manifest = list(manifest_rows)

    row_counts = Counter(row.get("row_id", "") for row in data)
    duplicate_row_ids = sorted(row_id for row_id, count in row_counts.items() if not row_id or count != 1)
    data_ids = set(row_counts)

    manifest_by_row: dict[str, str] = {}
    invalid_splits: list[str] = []
    manifest_duplicate_ids: set[str] = set()
    for entry in manifest:
        row_id = entry.get("row_id", "")
        split = entry.get("split", "")
        if row_id in manifest_by_row:
            manifest_duplicate_ids.add(row_id)
        manifest_by_row[row_id] = split
        if split not in ALLOWED_SPLITS:
            invalid_splits.append(f"{row_id}:{split}")
    duplicate_row_ids.extend(sorted(manifest_duplicate_ids))
    duplicate_row_ids = sorted(set(duplicate_row_ids))

    manifest_ids = set(manifest_by_row)
    missing_manifest_rows = sorted(data_ids - manifest_ids)
    unknown_manifest_rows = sorted(manifest_ids - data_ids)

    rows_per_split = Counter({name: 0 for name in ALLOWED_SPLITS})
    positives_per_split = Counter({name: 0 for name in ALLOWED_SPLITS})
    entities_per_split: dict[str, set[str]] = {name: set() for name in ALLOWED_SPLITS}
    entity_splits: dict[str, set[str]] = defaultdict(set)

    for row in data:
        row_id = row.get("row_id", "")
        split = manifest_by_row.get(row_id)
        if split not in ALLOWED_SPLITS:
            continue
        entity_id = row.get("entity_id", "")
        rows_per_split[split] += 1
        entities_per_split[split].add(entity_id)
        entity_splits[entity_id].add(split)
        try:
            positives_per_split[split] += int(row.get("churn_30d", "0"))
        except ValueError as exc:
            raise ValueError(f"invalid churn_30d for {row_id}") from exc

    entity_overlap = sorted(entity for entity, splits in entity_splits.items() if len(splits) > 1)
    return SplitSummary(
        rows={name: rows_per_split[name] for name in ALLOWED_SPLITS},
        entities={name: len(entities_per_split[name]) for name in ALLOWED_SPLITS},
        positives={name: positives_per_split[name] for name in ALLOWED_SPLITS},
        entity_overlap=entity_overlap,
        duplicate_row_ids=duplicate_row_ids,
        missing_manifest_rows=missing_manifest_rows,
        unknown_manifest_rows=unknown_manifest_rows,
        invalid_splits=sorted(invalid_splits),
    )


def audit_files(dataset: Path, manifest: Path) -> SplitSummary:
    return audit_rows(_read_csv(dataset), _read_csv(manifest))
