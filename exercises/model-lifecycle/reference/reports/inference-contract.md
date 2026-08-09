# Inference contract

## Inference unit and observation time
One customer-month payload containing only snapshot-time fields.
## Input schema and validation
All eight fields are required. Unknown fields/categories, booleans as numbers, non-finite values, and negative constrained values are rejected.
## Preprocessing and fitted state
Means, scales, categories and feature order are frozen in `preprocessing.json`, fitted on train only.
## Output schema and semantics
Each result has model/policy versions, a probability in [0,1], and `manual_review` or `no_review`.
## Decision policy and threshold
The threshold is selected on validation and versioned separately from model probability.
## Invalid input, timeout and partial failure
Invalid input or artifact mismatch exits non-zero without a prediction; no imputation or partial score.
## Batch and online behavior
CLI accepts one JSON object or JSONL and preserves input order. It is a CPU correctness path, not a latency SLO.
## Compatibility and versioning
Exact schema, preprocessing, feature order, model and policy versions must agree.
## Smoke, parity and performance tests
Golden predictions require 1e-12 absolute probability parity after clean-process loading.
## Rollout, fallback and rollback
Do not deploy this fixture model. A hypothetical mismatch disables scoring and returns to manual review baseline.
