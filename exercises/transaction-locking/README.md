# PostgreSQL 트랜잭션 잠금 실습

## 목표

같은 재고 행에 대한 20개 동시 차감 요청을 PostgreSQL 비관적 잠금으로 직렬화한다. 테스트는 모든 worker가 준비된 뒤 함께 시작하며 각 대기와 결과 회수에 상한을 둔다.

## 완료 기준

- 1,000에서 100씩 차감하는 20개 요청 중 정확히 10개만 성공한다.
- 모든 Future를 제한 시간 안에 회수하고 최종 수량이 정확히 0임을 확인한다.
- executor는 성공·실패와 관계없이 종료되고 검증 뒤 PostgreSQL container가 남지 않는다.

## 자기 설명

- Java의 시작 latch만으로 데이터베이스 lost update를 막을 수 없는 이유는 무엇인가?
- 낙관적 잠금 대신 비관적 잠금을 선택했을 때 처리량과 실패 형태는 어떻게 달라지는가?

## 검증

canonical skeleton의 일반 조회는 고정 실패 fixture다. tracked skeleton은 수정하지 않고 학습자 workspace에서 잠금 조회로 바꾸고 transaction 범위를 유지한다.

```sh
./scripts/new-workspace.sh transaction-locking
#학습 구현: .workspace/transaction-locking/src/main을 수정한다.
./scripts/check-workspace.sh transaction-locking
./scripts/mvn-guide.sh -pl :transaction-locking-reference -am test
```

PostgreSQL `18.4-alpine`의 immutable image를 사용하므로 Docker daemon이 필수다.
