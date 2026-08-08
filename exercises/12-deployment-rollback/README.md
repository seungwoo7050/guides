# 배포와 rollback 상태 기계

실제 Docker daemon 대신 임시 파일 시스템에서 배포 전이를 모델링합니다. 핵심은 명령의 수가 아니라 **현재 release를 언제 확정하고 실패 뒤 어떤 상태를 남기는가**입니다.

관련 문서: [`docs/12-ci-cd-deployment-and-rollback.md`](../../docs/12-ci-cd-deployment-and-rollback.md)

## 구현 계약

`skeleton/deploy.py`의 `deploy(state_dir, manifest)`를 완성합니다.

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
cd exercises/12-deployment-rollback
./verify.sh skeleton
./verify.sh reference
```

검증기는 정상 v2, schema 4 migration 뒤 smoke 실패, schema 비호환과 이미 획득된 lock을 각각 독립 환경에서 확인합니다. smoke 실패에서는 v1 release가 계속 current이지만 database schema는 이미 4임을 검사합니다.
