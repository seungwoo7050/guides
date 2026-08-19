# Capacity and Update Planner

Time-series resource metric, capacity/SLO policy, component lifecycle inventory를 결합해 owner, deadline, verification, rollback이 포함된 deterministic action plan을 생성하는 Python CLI다.

## Usage

```sh
python planner.py examples/metrics.csv examples/policy.json examples/components.json
python planner.py --fail-on-actions \
  examples/metrics.csv examples/policy.json examples/components.json
```

`--fail-on-actions`는 action이 하나라도 있으면 exit code `1`을 반환하므로 scheduled review나 CI gate에 사용할 수 있다.

## Analysis boundaries

- latest와 minimum memory headroom
- disk growth rate와 backup staging reserve를 제외한 effective disk limit
- application DB pool과 administrator connection reserve
- OOM restart evidence
- p95 latency와 error-rate policy
- component support end
- base image rebuild age와 approved version gap

## Report contract

각 action은 다음 field를 가진다.

- `id`, `severity`, `evidence`
- `owner`, severity 기반 `deadline`
- 완료 여부를 확인할 `verification`
- 변경 실패 시 사용할 `rollback`

Action은 severity와 ID로 정렬되어 같은 input에서 같은 report를 생성한다.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Design decisions

Disk threshold는 단순한 `disk_alert_percent`가 아니라 backup staging peak를 미리 제외한 effective limit로 계산한다. Database application pool은 `db_max_connections` 전체를 사용할 수 없으며 administrator reserve를 뺀 budget을 넘으면 critical finding으로 처리한다. Version gap만 있는 component는 medium이지만 support expiry나 임박은 더 높은 severity가 우선한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Action schema | `planner.py` |
| 2 | Input validation and resource budget derivation | `planner.py` |
| 3 | Capacity and SLO findings | `planner.py` |
| 4 | Component support lifecycle | `planner.py` |
| 5 | Deterministic report projection | `planner.py` |
| 6 | JSON CLI boundary | `planner.py` |
| 7 | Planner regression suite | `tests/test_planner.py` |

## Scope and limitations

Disk projection은 observation window의 첫 값과 마지막 값 사이 선형 growth를 사용한다. 계절성, sudden workload change, inode exhaustion, cloud quota, cost model을 추정하지 않는다. Component inventory와 approved version은 caller가 유지해야 하며 이 도구는 external package registry를 조회하지 않는다.
