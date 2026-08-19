# 웹 인프라 가이드 학습 로드맵

이 가이드는 한 개의 HTTP server가 요청을 처리하는 지점에서 시작해, containerized service를 구성하고 운영 가능한 단일-host deployment의 주요 경계를 이해하는 데 목적이 있습니다.

## 1. 기초 구간

다음 순서로 local runtime을 구성합니다.

1. 웹 요청과 server process
2. Docker image와 container lifecycle
3. Compose network와 persistent storage
4. Nginx, TLS와 application runtime
5. database lifecycle
6. idempotent application bootstrap
7. 장애 진단과 recovery

이 구간을 마치면 외부 요청, container 내부 통신, process 상태와 persistent data의 위치를 구분할 수 있어야 합니다.

## 2. 운영 구간

local stack을 이해한 뒤 다음 주제로 확장합니다.

1. production contract와 threat model
2. Linux host provisioning과 hardening
3. DNS, ACME와 public TLS
4. immutable image와 release artifact
5. deployment와 rollback
6. production secret과 configuration
7. observability와 alerting
8. backup, restore와 disaster recovery
9. capacity와 component update lifecycle
10. incident response와 runbook
11. clean-host rebuild

## 3. docs와 exercises의 관계

`docs/`는 개념, 실패 조건과 운영 판단 기준을 설명합니다. `exercises/`는 별도의 learner workspace나 reference answer가 아니라, 독립적으로 실행하거나 검증할 수 있는 completed project로 유지합니다.

각 project는 필요한 경우 자체 `README.md`, source, runtime configuration, sample data와 project-local tests를 가집니다.

## 4. 완료 기준

전체 가이드를 마쳤다면 다음 질문에 답할 수 있어야 합니다.

- 요청 실패가 DNS, connection, TLS, gateway, application, database 중 어디에서 발생했는가?
- 어떤 상태가 container와 함께 사라지고 어떤 상태가 별도 storage에 남는가?
- release를 어떤 immutable identity로 식별하고 rollback compatibility를 어떻게 판단하는가?
- secret, telemetry와 backup을 application source와 어떤 경계로 분리하는가?
- host 전체를 잃어도 어떤 external state를 사용해 service를 복구할 수 있는가?
