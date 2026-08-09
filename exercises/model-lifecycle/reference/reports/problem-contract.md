# Problem contract

## Prediction subject and observation unit
One customer-month snapshot is scored independently; entity identity is retained only for split audit.
## Observation time and available information
Only fields available at the end of `snapshot_month` may be used.
## Label and label window
`churn_30d` records voluntary churn in the following 30 days and is mature only after that window.
## Primary user and decision
A retention analyst uses ranked probabilities to choose cases for manual review.
## Intended use
Demonstrate a reproducible offline model lifecycle on the committed synthetic fixture.
## Prohibited and out-of-scope use
No automated customer action, real-world eligibility decision, or claim of population representativeness.
## False positive, false negative and abstention costs
False positives consume review capacity; false negatives miss possible churn; invalid inputs abstain by failing closed.
## Non-ML and incumbent baselines
Compare train prevalence and a declared declining-usage/late-payment rule before any fitted model.
## Success, stop and rollback conditions
Success means reproducible evidence and baseline comparison. Stop on leakage or contract mismatch; rollback to no automated score.
## Assumptions and unresolved questions
Costs and review capacity are illustrative; label reliability and population coverage need real-data review.
