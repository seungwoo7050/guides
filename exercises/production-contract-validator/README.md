# Production Contract Validator

운영 서비스의 공개 endpoint, 관리 경계, 복구 가능한 data inventory, RTO/RPO, availability measurement, threat model, residual risk, readiness gate를 하나의 YAML contract로 검증하는 CLI다.

## Usage

```sh
python -m pip install .
production-contract-validator examples/notes-service.yaml
```

개발 환경에서는 package install 없이 실행할 수 있다.

```sh
PYTHONPATH=src python -m production_contract_validator examples/notes-service.yaml
```

유효한 contract는 exit code `0`, 정책 위반은 exit code `1`, 잘못된 CLI 사용은 `argparse`의 exit code를 반환한다.

## Contract boundaries

Validator는 다음을 요구한다.

- public HTTPS endpoint와 제한된 management endpoint
- `business`, `secret`, `configuration` data classification
- host 밖의 recovery source와 명시적인 RPO
- user-facing path를 사용하는 external availability probe
- prevention, detection, recovery, owner가 있는 threat scenario
- accepted residual risk
- immutable release, external backup, rollback, certificate monitoring, restore drill readiness

## Tests

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Design decisions

Contract는 실제 deployment를 생성하지 않는다. 대신 운영 전제와 검증 조건을 machine-checkable form으로 고정한다. `user_capability`에 implementation component 목록을 적는 것을 거부하고, availability probe가 `/healthz` 같은 process-only route에 머무르지 않도록 제한한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 0 | Installable package and CLI boundary | `pyproject.toml` |
| 1 | YAML document input boundary | `src/production_contract_validator/validator.py` |
| 2 | Service and endpoint policy | `src/production_contract_validator/validator.py` |
| 3 | Recoverable data inventory policy | `src/production_contract_validator/validator.py` |
| 4 | Availability objective policy | `src/production_contract_validator/validator.py` |
| 5 | Threat and residual risk policy | `src/production_contract_validator/validator.py` |
| 6 | Production readiness gate | `src/production_contract_validator/validator.py` |
| 7 | CLI exit and report contract | `src/production_contract_validator/cli.py` |
| 8 | Validation regression suite | `tests/test_validator.py` |

## Scope and limitations

이 도구는 선언된 contract의 구조와 baseline policy만 검증한다. 실제 port exposure, backup 존재 여부, rollback 성공, certificate expiry, external probe 결과를 직접 측정하지 않는다. 이러한 evidence는 별도 deployment 및 observability system에서 수집해야 한다.
