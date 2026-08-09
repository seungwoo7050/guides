# Model card

## Model details and reviewed versions
Dependency-free logistic model `churn-logistic-v1`, preprocessing `churn-preprocessing-v1`, and policy `churn-review-v1`.
## Intended use, users and subjects
Offline learning by a retention analyst on synthetic customer-month subjects.
## Prohibited and out-of-scope use
No real customer decision, automated intervention, eligibility use, or representativeness claim.
## Training data and split
Training-only fitted preprocessing on `synthetic-churn-v1`; entity-disjoint validation and test.
## Baselines, evaluation and threshold
Compared with prevalence and business-rule baselines; model and threshold selected on validation before final test.
## Slice, calibration and uncertainty
Test plan, region, and tenure slices plus fixed-bin calibration are reported; small samples make estimates unstable.
## Known limitations and failure modes
Synthetic data, no temporal shift, strict categories, and no missing-value path. Invalid input fails closed.
## Privacy, fairness, security and misuse considerations
No personal data is present. Real use requires privacy, subgroup, abuse, and intervention review.
## Operational controls and human review
Predictions only nominate manual review; checksum and exact schemas are mandatory.
## Monitoring, incident and rollback
Monitor input rejection, score/action volume and delayed quality; disable scoring and return to manual baseline on mismatch.
## Change history and revalidation triggers
Version 1. Revalidate any fixture, schema, preprocessing, weight, threshold, runtime, or intended-use change.
