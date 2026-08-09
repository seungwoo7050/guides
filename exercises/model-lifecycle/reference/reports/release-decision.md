# Release decision

## Decision
APPROVE WITH CONDITIONS
## Reviewed versions
Synthetic dataset v1, entity-hash split v1, churn-logistic v1, preprocessing v1 and review policy v1.
## Supported claim
The reference is suitable for the next synthetic learning stage and reproducible local review.
## Blocking findings
Real-world release remains blocked because there is no representative data, privacy review, intervention evidence or production validation.
## Non-blocking findings
Slice counts are small and neural evidence is didactic, but both limitations are explicit.
## Required controls and owners
Keep manual review, strict validation, checksums, version logs and owner-reviewed monitoring evidence.
## Rollout and rollback
No service rollout is authorized. For exercise regression, revert to the previous immutable bundle or no score.
## Revalidation triggers
Any data, feature, fitted state, model, threshold, runtime, intended-use or monitoring change.
