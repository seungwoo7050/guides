# Dataset card

## Purpose and relation to the problem contract
The fixture supports customer-month churn lifecycle practice, not deployment claims.
## Sources and provenance
Repository-owned deterministic synthetic data generated with seed 7050; no personal data.
## Observation unit, period and population
Three monthly snapshots for each of 240 synthetic entities.
## Inclusion, exclusion and sampling
All committed rows are included and entities are assigned by the fixed hash manifest.
## Features and availability cutoff
Only schema fields marked `allowed_for_prediction` and available at snapshot time are used.
## Label creation and maturity
`churn_30d` is observed after 30 days; `future_refund_30d` is post-cutoff and forbidden.
## Missing values and measurement limits
The fixture has no missing values and does not simulate production measurement failure.
## Split policy and leakage audit
Entity-disjoint train/validation/test splits prevent one customer appearing across partitions.
## Representation and unsupported populations
Synthetic tiers and regions do not represent any actual customers or demographic groups.
## Privacy, access, retention and deletion
No personal data; keep real customer data outside this exercise.
## Known limitations
No calendar holdout, concept drift, delayed telemetry, or causal intervention evidence.
## Versions and checksums
Dataset `synthetic-churn-v1`; split `entity-hash-v1`; digests are recorded in reproduction evidence.
