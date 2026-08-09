# 결정적 Platform Control Plane 실습

실제 cloud 계정이나 Kubernetes cluster 없이 self-service 환경 요청의 상태 전이와 실패 격리를 관찰하는 Python 표준 라이브러리 실습입니다. 구현 도구가 아니라 **공개 API, desired/observed state, operation identity, evidence와 cleanup 불변식**을 검증합니다.

## 공개 API

`skeleton/platform_model.py`의 다음 함수를 완성합니다. 모든 입력과 출력은 JSON으로 직렬화할 수 있어야 하며 입력 state를 직접 변경하면 안 됩니다.

```python
request_environment(state, request) -> {"state": object, "result": object}
reconcile(state, request) -> {"state": object, "result": object}
observe_drift(state, request) -> {"state": object, "result": object}
request_migration(state, request) -> {"state": object, "result": object}
retire_service(state, request) -> {"state": object, "result": object}
snapshot(state) -> object
```

구현 내부 자료구조는 자유롭습니다. validator는 위 공개 함수와 snapshot만 관찰합니다.

## 정상·경계·대표 실패

| Check | 종류 | 공개 행동 |
|---|---|---|
| `PE-001` | 정상 | 유효 요청은 `Progressing`에서 시작하고 `generation == observed_generation`이며 revision·generation에 묶인 통과 `external-smoke` evidence가 있을 때만 `Ready`가 됩니다. |
| `PE-002` | 경계 | 동일 idempotency key·동일 payload는 기존 operation을 반환하고 변경된 payload는 원자적으로 충돌합니다. |
| `PE-003` | 실패 | evidence 없는 `Ready`를 거부하고 일부 생성된 외부 resource ID와 cleanup 필요 상태를 숨기지 않습니다. |
| `PE-004` | 격리 | tenant quota 초과가 partial state를 만들지 않고 다른 tenant queue는 계속 진행합니다. |
| `PE-005` | drift | 허가되지 않은 live drift를 desired artifact로 수렴시키고 before/after evidence를 남깁니다. |
| `PE-006` | break-glass | 긴급 변경은 approver·expiry·reason·evidence가 모두 있을 때만 bounded exception이 됩니다. |
| `PE-007` | identity | 장기 static credential fallback을 거부하고 workload identity만 환경에 연결합니다. |
| `PE-008` | migration | wave 실패 시 이후 wave가 실행되지 않고 abort evidence와 상태가 남습니다. |
| `PE-009` | retirement | 열린 break-glass exception이 있는 상태에서 환경·operation·credential·exception을 정리하고 audit tombstone만 남기며 다른 서비스는 보존합니다. |
| `PE-010` | evidence | snapshot은 결정적 deep copy이고 secret material을 노출하지 않습니다. |

## 시작과 검증

tracked skeleton을 직접 정답으로 바꾸지 말고 별도 learner workspace로 복사합니다.

```sh
mkdir -p .workspace/13-platform-control-plane
cp exercises/13-platform-control-plane/skeleton/platform_model.py \
  .workspace/13-platform-control-plane/platform_model.py

python3 scripts/verify_platform_model.py \
  --implementation .workspace/13-platform-control-plane/platform_model.py
```

기준 구현과 의도한 starter 상태는 다음처럼 확인합니다.

```sh
python3 scripts/verify_platform_model.py \
  --implementation exercises/13-platform-control-plane/reference/platform_model.py
python3 scripts/verify_platform_model.py \
  --implementation exercises/13-platform-control-plane/skeleton/platform_model.py
```

기준 구현은 `PE-001..010`을 모두 통과하고 starter는 계약에 선언된 check에서 실패해야 합니다. `tests/mutants/`의 단일 결함 구현은 validator가 특정 불변식의 잘못된 구현도 거부하는지 확인하는 검증기용 fixture입니다.

## 결정적 Evidence Report

`--report`는 기존 파일과 symlink를 덮어쓰지 않고 새 파일만 만듭니다.

```sh
report_dir="$(mktemp -d)"
python3 scripts/verify_platform_model.py \
  --implementation exercises/13-platform-control-plane/reference/platform_model.py \
  --report "$report_dir/platform-model-report.json"
python3 -m json.tool "$report_dir/platform-model-report.json"
```

report에는 구현, 공개 `contract.json`, 실제 `tests/contract.py`의 경로·SHA-256, stable check ID, Capstone의 여섯 canonical ID, 공개 관찰값과 실행 한계가 포함됩니다. Capstone에 제출할 때는 학습자 구현으로 새 report를 만들고 manifest가 그 구현·report hash를 선언해야 합니다. `checks`는 학습자 모듈을 import하지 않는 별도 계약 프로세스에서 만들어지므로 학습자 import가 계약 모듈을 monkeypatch해 통과 record를 대신 만들 수 없습니다.

## 사람 검토와 한계

자동 검사는 합성 in-memory 상태만 판단합니다. 리뷰어는 다음을 별도로 확인합니다.

1. operation·resource·tenant identity가 실제 platform API와 같은 scope를 가집니까?
2. partial effect 뒤 유지와 cleanup 중 어느 선택이 비용·데이터 수명 계약에 맞습니까?
3. queue fairness와 quota가 실제 concurrent controller에서도 atomic합니까?
4. break-glass가 실제 identity·policy·GitOps owner와 연결되고 만료 뒤 수렴합니까?
5. migration abort가 이미 바뀐 data·policy·artifact의 rollback 또는 roll-forward를 설명합니까?

validator는 계약 runner와 learner RPC를 서로 다른 child process에서 실행하고 전체 실행을 5초로 제한합니다. learner process의 Python socket/subprocess audit event와 file write를 거부하지만 OS sandbox는 아닙니다. 검토하지 않은 코드를 실행하지 마십시오. 실제 IAM, network policy, provider operation, Kubernetes controller, concurrency, crash recovery와 물리적 삭제를 검증하지 않으며 외부 network나 resource를 사용하지 않습니다.
