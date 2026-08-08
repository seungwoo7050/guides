# 멱등성과 Outbox 실습

## 목표

PostgreSQL 완료 결과를 정본으로, Redis를 복구 가능한 힌트로 사용한다. 같은 멱등성 키의 동시 요청을 직렬화하고 업무 행과 Outbox 행을 같은 transaction에 기록한다.

## 완료 기준

- Redis가 정상일 때 commit된 결과가 양수 TTL의 cache로 저장되고 재요청에 재사용된다.
- Redis 접근이 실패해도 동시 요청 20개의 operation ID가 하나이며 업무 행과 Outbox 행이 각각 하나다.
- 첫 발행 실패는 시도 횟수·오류·다음 시각을 남기고 다음 poll에서 같은 Outbox 행을 성공 처리한다.

## 자기 설명

- Redis lock이나 cache hit를 정확성의 정본으로 삼으면 어떤 장애에서 중복이 생기는가?
- Outbox 발행 실패를 transaction 전체 rollback으로 처리하지 않는 이유는 무엇인가?

## 검증

canonical skeleton에는 advisory transaction lock과 Outbox 저장이 빠져 있으며 고정 실패 fixture로 남는다. tracked skeleton은 수정하지 않고 학습자 workspace를 고치며, workspace와 reference는 같은 공개 test 파일을 사용한다.

```sh
./scripts/new-workspace.sh idempotency-outbox
#학습 구현: .workspace/idempotency-outbox/src/main을 수정한다.
./scripts/check-workspace.sh idempotency-outbox
./scripts/mvn-guide.sh -pl :idempotency-outbox-reference -am test
```

PostgreSQL `18.4-alpine`과 Redis `8.8.0-alpine`의 immutable image를 사용한다.
