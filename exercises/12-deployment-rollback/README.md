# 배포와 rollback 상태 기계

실제 Docker daemon 대신 임시 파일 시스템에서 배포 전이를 모델링합니다. 핵심은 명령의 수가 아니라 **현재 release를 언제 확정하고 실패 뒤 어떤 상태를 남기는가**입니다.

관련 문서: [`docs/12-ci-cd-deployment-and-rollback.md`](../../docs/12-ci-cd-deployment-and-rollback.md)

## 구현 계약

`workspace/deploy.py`의 `deploy(state_dir, manifest)`를 완성합니다.

- 환경별 lock을 먼저 획득합니다.
- preflight 실패 시 current 상태를 바꾸지 않습니다.
- candidate를 staged 상태로 기록합니다.
- readiness와 smoke 성공 뒤에만 current를 교체합니다.
- 실패 시 staged 상태를 제거하고 이전 release를 유지합니다.
- migration target이 이전 release의 호환 범위를 벗어나면 자동 rollback 가능한 배포로 허용하지 않습니다.
- 호환 migration이 적용된 뒤 candidate가 실패하면 schema 상태는 남고 current release만 이전 값으로 유지됩니다.
- 모든 전이를 append-only `events.jsonl`에 기록합니다.
- current 파일은 임시 파일과 원자 교체를 사용합니다.

## 검증

```sh
python3 scripts/new-workspace.py exercises/12-deployment-rollback
cd exercises/12-deployment-rollback
./verify.sh workspace
```

작업공간 생성 명령은 저장소 루트에서 실행합니다. 검증기는 정상 v2, schema 4 migration 뒤 smoke 실패, schema 비호환과 이미 획득된 lock을 각각 독립 환경에서 확인합니다. smoke 실패에서는 v1 release가 계속 current이지만 database schema는 이미 4임을 검사합니다. 자기 설명까지 마친 뒤에만 `reference/`와 `./verify.sh reference`를 비교합니다.

## 권장 구현 순서

아래 번호는 실제 Git 이력이 아니라 `reference/` 전체의 학습용 construction order입니다. 파일마다 번호를 다시 시작하지 않습니다.

| 번호 | 구현 경계 |
|---:|---|
| 1 | durable atomic state primitive |
| 2 | append-only transition evidence |
| 3 | deployment lock과 manifest preflight |
| 4 | candidate stage와 simulated migration state |
| 5 | readiness·external smoke failure gate |
| 6 | current·previous·compatibility commit |

Migration은 JSON state model 안의 중간 전이이며 실제 migration CLI나 Implementation 0이 아닙니다.

## 완료 기준

- [ ] `./verify.sh workspace`가 정상 배포, smoke 실패, schema 비호환, lock 충돌 시나리오를 모두 통과한다.
- [ ] readiness와 smoke 성공 전에는 `current`가 바뀌지 않고 실패 뒤 후보 staged 상태만 제거되며 이전 release가 유지된다.
- [ ] 각 전이가 append-only event에 남고 `current` 공개는 임시 파일을 거친 원자 교체임을 확인한다.

## 자기 설명

1. migration 뒤 candidate가 실패했을 때 release는 돌아가도 schema가 자동으로 돌아가지 않는 이유는 무엇인가?
2. readiness 통과와 사용자 smoke 통과 중 어느 시점에 `current`를 확정해야 하며 그 이유는 무엇인가?
3. 환경별 lock이 없으면 두 배포가 어떤 중간 상태를 서로 덮어쓸 수 있는가?
