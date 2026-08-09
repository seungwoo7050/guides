# Monitoring plan

## Reviewed model, schema, preprocessing and policy versions
Track model, input, preprocessing and policy version on every evidence record.
## Service health signals
Track successful loads, checksum failure, rejection rate, latency and prediction availability.
## Data quality and feature drift
Track missing/unknown/rejected fields and numeric range/quantile changes against training evidence.
## Prediction, calibration and action volume
Track score distribution, threshold crossing and review volume separately.
## Delayed outcome quality and label maturity
Compute quality only after 30-day labels mature and preserve event-time cohorts.
## Slices, sample sizes and privacy
Report plan, region and tenure with counts and suppress conclusions from tiny samples.
## Feedback loops and exposure logging
Record whether a subject was reviewed or contacted before interpreting later outcomes.
## Alerts, owners, evidence and actions
The model owner investigates contract/quality alerts; the service owner disables scoring on integrity failure.
## Retraining triggers and release approval
Drift opens review, not automatic retraining; a new artifact requires fresh validation and approval.
## Incident containment and rollback
Fail closed, retain evidence, disable the artifact, and restore the documented manual baseline.
## Monitoring pipeline quality
Test missing/delayed labels, duplicate events, version joins and alert delivery independently.
