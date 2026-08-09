#!/usr/bin/env python3
"""Generate deterministic synthetic fixtures for the cumulative exercise."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Iterable

SEED = 7050
GENERATOR_VERSION = 1
ENTITY_COUNT = 240
SNAPSHOTS_PER_ENTITY = 3
DATASET_FIELDS = [
    "row_id",
    "entity_id",
    "snapshot_month",
    "tenure_months",
    "monthly_usage_hours",
    "usage_change_90d",
    "support_tickets_90d",
    "late_payments_180d",
    "plan_tier",
    "region",
    "marketing_contacts_30d",
    "future_refund_30d",
    "churn_30d",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_split(entity_id: str) -> str:
    bucket = int(hashlib.sha256(entity_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket < 6:
        return "train"
    if bucket < 8:
        return "validation"
    return "test"


def sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def rows() -> list[dict[str, str | int | float]]:
    rng = random.Random(SEED)
    result: list[dict[str, str | int | float]] = []
    plans = ("basic", "standard", "premium")
    regions = ("north", "south", "east", "west")

    for index in range(1, ENTITY_COUNT + 1):
        entity_id = f"customer-{index:04d}"
        base_tenure = rng.randint(1, 48)
        plan = rng.choices(plans, weights=(0.42, 0.38, 0.20), k=1)[0]
        region = regions[rng.randrange(len(regions))]
        latent_satisfaction = rng.gauss(0.0, 0.75)
        base_usage = max(1.0, rng.gauss(21.0 + 4.0 * latent_satisfaction, 5.0))

        for month_offset in range(SNAPSHOTS_PER_ENTITY):
            month = month_offset + 1
            snapshot_month = f"2025-{month:02d}"
            tenure = base_tenure + month_offset
            usage_change = max(-25.0, min(25.0, rng.gauss(-1.5 - 3.5 * latent_satisfaction, 5.5)))
            usage = max(0.0, base_usage + usage_change * 0.35 + rng.gauss(0.0, 2.5))
            ticket_lambda = max(0.2, 1.3 - 0.65 * latent_satisfaction)
            tickets = min(8, int(rng.expovariate(1.0 / ticket_lambda)))
            late_probability = min(0.65, max(0.02, 0.12 - 0.07 * latent_satisfaction))
            late_payments = sum(1 for _ in range(3) if rng.random() < late_probability)
            marketing_contacts = rng.randint(0, 4)

            risk_logit = (
                -2.05
                + 0.34 * tickets
                + 0.58 * late_payments
                - 0.035 * tenure
                - 0.060 * usage_change
                + (0.32 if plan == "basic" else -0.12 if plan == "premium" else 0.0)
                - 0.33 * latent_satisfaction
                + rng.gauss(0.0, 0.45)
            )
            churn = 1 if rng.random() < sigmoid(risk_logit) else 0
            future_refund = 1 if rng.random() < (0.72 if churn else 0.04) else 0

            result.append(
                {
                    "row_id": f"{entity_id}-{snapshot_month}",
                    "entity_id": entity_id,
                    "snapshot_month": snapshot_month,
                    "tenure_months": tenure,
                    "monthly_usage_hours": f"{usage:.3f}",
                    "usage_change_90d": f"{usage_change:.3f}",
                    "support_tickets_90d": tickets,
                    "late_payments_180d": late_payments,
                    "plan_tier": plan,
                    "region": region,
                    "marketing_contacts_30d": marketing_contacts,
                    "future_refund_30d": future_refund,
                    "churn_30d": churn,
                }
            )
    return result


def schema() -> dict[str, object]:
    columns = [
        {"name": "row_id", "type": "string", "role": "identifier", "description": "customer-month snapshot identity", "available_at": "snapshot_time", "allowed_for_prediction": False},
        {"name": "entity_id", "type": "string", "role": "group", "description": "customer identity used only for split and audit", "available_at": "snapshot_time", "allowed_for_prediction": False},
        {"name": "snapshot_month", "type": "year-month", "role": "time", "description": "observation cutoff month", "available_at": "snapshot_time", "allowed_for_prediction": False},
        {"name": "tenure_months", "type": "integer", "role": "feature", "minimum": 0, "available_at": "snapshot_time", "allowed_for_prediction": True},
        {"name": "monthly_usage_hours", "type": "number", "role": "feature", "minimum": 0, "unit": "hours", "available_at": "snapshot_time", "allowed_for_prediction": True},
        {"name": "usage_change_90d", "type": "number", "role": "feature", "unit": "hours", "available_at": "snapshot_time", "allowed_for_prediction": True},
        {"name": "support_tickets_90d", "type": "integer", "role": "feature", "minimum": 0, "available_at": "snapshot_time", "allowed_for_prediction": True},
        {"name": "late_payments_180d", "type": "integer", "role": "feature", "minimum": 0, "available_at": "snapshot_time", "allowed_for_prediction": True},
        {"name": "plan_tier", "type": "category", "role": "feature", "allowed_values": ["basic", "standard", "premium"], "available_at": "snapshot_time", "allowed_for_prediction": True},
        {"name": "region", "type": "category", "role": "feature", "allowed_values": ["north", "south", "east", "west"], "available_at": "snapshot_time", "allowed_for_prediction": True},
        {"name": "marketing_contacts_30d", "type": "integer", "role": "feature", "minimum": 0, "available_at": "snapshot_time", "allowed_for_prediction": True},
        {"name": "future_refund_30d", "type": "integer", "role": "forbidden-feature", "allowed_values": [0, 1], "available_at": "after_label_window", "allowed_for_prediction": False, "leakage_reason": "refund outcome may occur after prediction cutoff and is correlated with churn"},
        {"name": "churn_30d", "type": "integer", "role": "label", "allowed_values": [0, 1], "available_at": "30_days_after_snapshot", "allowed_for_prediction": False},
    ]
    return {
        "schema_version": "synthetic-churn-v1",
        "observation_unit": "customer-month",
        "observation_time": "end of snapshot_month",
        "label": "voluntary churn within the following 30 days",
        "columns": columns,
    }


def write_csv(path: Path, fieldnames: list[str], data: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    generated_rows = rows()
    dataset_path = output / "dataset.csv"
    manifest_path = output / "split_manifest.csv"
    schema_path = output / "schema.json"
    policy_path = output / "split-policy.json"
    card_path = output / "dataset-card.md"

    write_csv(dataset_path, DATASET_FIELDS, generated_rows)
    manifest_rows = [
        {
            "row_id": row["row_id"],
            "entity_id": row["entity_id"],
            "split": stable_split(str(row["entity_id"])),
        }
        for row in generated_rows
    ]
    write_csv(manifest_path, ["row_id", "entity_id", "split"], manifest_rows)
    write_json(schema_path, schema())
    write_json(
        policy_path,
        {
            "policy_version": "entity-hash-v1",
            "group_key": "entity_id",
            "hash": "sha256 first 32 bits modulo 10",
            "buckets": {"train": [0, 1, 2, 3, 4, 5], "validation": [6, 7], "test": [8, 9]},
            "purpose": "evaluate generalization to entities not seen during training",
            "limitations": [
                "does not model future calendar-time shift",
                "synthetic entities and labels do not establish real-world representativeness",
            ],
        },
    )

    split_counts: dict[str, int] = {"train": 0, "validation": 0, "test": 0}
    positives: dict[str, int] = {"train": 0, "validation": 0, "test": 0}
    entity_sets: dict[str, set[str]] = {"train": set(), "validation": set(), "test": set()}
    split_by_row = {str(row["row_id"]): str(row["split"]) for row in manifest_rows}
    for row in generated_rows:
        split = split_by_row[str(row["row_id"])]
        split_counts[split] += 1
        positives[split] += int(row["churn_30d"])
        entity_sets[split].add(str(row["entity_id"]))

    card_path.write_text(
        f"""# Synthetic churn fixture dataset card

## Purpose

이 fixture는 group-aware split, leakage audit, baseline, threshold와 artifact 계약을 연습하기 위한 합성 dataset이다. 실제 고객 행동이나 특정 산업의 분포를 나타내지 않으며 실제 의사결정에 사용하면 안 된다.

## Observation and label

- Observation unit: `customer-month`
- Observation cutoff: `snapshot_month` 말
- Label: 이후 30일 안의 합성 `churn_30d`
- Entities: {ENTITY_COUNT}
- Rows: {len(generated_rows)}
- Generator seed: {SEED}
- Generator version: {GENERATOR_VERSION}

## Split

Entity identity의 안정적인 SHA-256 bucket으로 분리해 같은 entity가 여러 split에 나타나지 않는다.

| split | rows | entities | positives |
|---|---:|---:|---:|
| train | {split_counts['train']} | {len(entity_sets['train'])} | {positives['train']} |
| validation | {split_counts['validation']} | {len(entity_sets['validation'])} | {positives['validation']} |
| test | {split_counts['test']} | {len(entity_sets['test'])} | {positives['test']} |

## Deliberate hazard

`future_refund_30d`는 label window 이후에만 알 수 있으며 label과 강하게 연관되도록 생성됐다. 누출 조사 연습을 위해 dataset에 포함하지만 prediction에는 사용할 수 없다. `schema.json`의 `allowed_for_prediction`을 확인한다.

## Known limitations

- 합성 규칙과 noise가 실제 churn process를 표현하지 않는다.
- Calendar-time shift를 평가하지 않는다.
- Region과 plan category는 실제 보호 집단이나 제품 구조를 나타내지 않는다.
- Missing data, consent, deletion과 label adjudication 문제를 충분히 재현하지 않는다.
- Model quality 숫자는 이 fixture 밖으로 일반화할 수 없다.
""",
        encoding="utf-8",
    )

    files = [dataset_path, manifest_path, schema_path, policy_path, card_path]
    write_json(
        output / "fixture-manifest.json",
        {
            "generator_version": GENERATOR_VERSION,
            "seed": SEED,
            "entity_count": ENTITY_COUNT,
            "row_count": len(generated_rows),
            "snapshots_per_entity": SNAPSHOTS_PER_ENTITY,
            "files": {path.name: sha256(path) for path in files},
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("exercises/model-lifecycle/fixtures"))
    args = parser.parse_args()
    generate(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
