# Atomic Deployment

Exact image digest와 database compatibility range가 포함된 release manifest를 durable local state machine에 적용한다. Preflight, candidate staging, compatible migration, readiness, external smoke, atomic current publication, append-only evidence를 명시적으로 분리한다.

## Usage

```sh
python -m pip install -r requirements.txt
cp -R examples/state /tmp/atomic-deployment-state
python deployment.py /tmp/atomic-deployment-state examples/manifests/v1.yaml
python deployment.py /tmp/atomic-deployment-state examples/manifests/v2.yaml
```

Current state는 `current.json`, 진행 중 candidate는 `staged.json`, lifecycle evidence는 `events.jsonl`에 저장된다.

## State transitions

1. environment lock 획득
2. exact digest, image availability, current schema, candidate range 검증
3. previous release가 migration target을 계속 사용할 수 있는지 검증
4. candidate stage와 compatible migration 적용
5. readiness와 external smoke gate
6. `current`, `previous`, compatibility, image를 하나의 atomic JSON write로 공개

Smoke 실패 시 candidate는 공개되지 않는다. Migration은 이미 적용될 수 있으므로 preflight에서 previous release compatibility를 먼저 증명한다.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Design decisions

Deployment lock은 lock file의 존재 여부가 아니라 `flock` ownership으로 판단한다. Process crash 뒤 stale file이 남아도 새 process가 lock을 획득할 수 있다. `current.json`과 event log는 file `fsync`를 수행하고 atomic replace 뒤 parent directory도 `fsync`한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Durable atomic state write | `deployment.py` |
| 2 | Append-only deployment evidence | `deployment.py` |
| 3 | Environment deployment lock | `deployment.py` |
| 4 | Compatibility preflight and candidate staging | `deployment.py` |
| 5 | Readiness and external smoke gates | `deployment.py` |
| 6 | Atomic release commit | `deployment.py` |
| 7 | YAML CLI boundary | `deployment.py` |
| 8 | Deployment state-machine verification | `tests/test_deployment.py` |

## Scope and limitations

이 프로젝트는 실제 container runtime, registry, database migration command, load balancer를 호출하지 않는다. Manifest의 `available`, `readiness`, `smoke` field는 외부 adapter가 수집한 결과를 표현한다. Local filesystem의 atomic rename과 `fsync` semantics를 전제로 한다.
