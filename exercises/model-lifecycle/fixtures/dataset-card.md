# Synthetic churn fixture dataset card

## Purpose

이 fixture는 group-aware split, leakage audit, baseline, threshold와 artifact 계약을 연습하기 위한 합성 dataset이다. 실제 고객 행동이나 특정 산업의 분포를 나타내지 않으며 실제 의사결정에 사용하면 안 된다.

## Observation and label

- Observation unit: `customer-month`
- Observation cutoff: `snapshot_month` 말
- Label: 이후 30일 안의 합성 `churn_30d`
- Entities: 240
- Rows: 720
- Generator seed: 7050
- Generator version: 1

## Split

Entity identity의 안정적인 SHA-256 bucket으로 분리해 같은 entity가 여러 split에 나타나지 않는다.

| split | rows | entities | positives |
|---|---:|---:|---:|
| train | 390 | 130 | 50 |
| validation | 156 | 52 | 19 |
| test | 174 | 58 | 23 |

## Deliberate hazard

`future_refund_30d`는 label window 이후에만 알 수 있으며 label과 강하게 연관되도록 생성됐다. 누출 조사 연습을 위해 dataset에 포함하지만 prediction에는 사용할 수 없다. `schema.json`의 `allowed_for_prediction`을 확인한다.

## Known limitations

- 합성 규칙과 noise가 실제 churn process를 표현하지 않는다.
- Calendar-time shift를 평가하지 않는다.
- Region과 plan category는 실제 보호 집단이나 제품 구조를 나타내지 않는다.
- Missing data, consent, deletion과 label adjudication 문제를 충분히 재현하지 않는다.
- Model quality 숫자는 이 fixture 밖으로 일반화할 수 없다.
