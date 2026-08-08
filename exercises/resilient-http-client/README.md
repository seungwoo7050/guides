# 복원력 있는 HTTP 클라이언트 실습

## 목표

업무 거절과 의존성 장애를 분리하고, `Duration` 기반 connect/read timeout과 두 번의 고정 retry budget을 적용한다. 재시도에서도 같은 요청 식별자를 보존한다.

## 완료 기준

- `409` 업무 거절은 Circuit Breaker 실패에 포함되지 않고 반복해도 circuit이 닫혀 있다.
- `500`, 연결 reset, read timeout과 잘못된 JSON은 `DependencyUnavailableException`으로 번역된다.
- 한 호출은 최대 두 번이며 두 요청 본문에 같은 request ID가 기록된다.

## 자기 설명

- 쓰기 요청 timeout이 서버의 미처리를 뜻하지 않는 이유와 멱등성 키의 관계는 무엇인가?
- 업무 거절을 Circuit Breaker 실패로 기록하면 정상 트래픽에서 어떤 잘못된 상태 전이가 생기는가?

## 검증

canonical skeleton은 기록할 예외 범위가 너무 넓은 고정 실패 fixture다. tracked skeleton은 수정하지 않고 학습자 workspace를 고치며, 동일한 공개 test suite가 오류 분류, timeout과 호출 횟수를 검사한다.

```sh
./scripts/new-workspace.sh resilient-http-client
#학습 구현: .workspace/resilient-http-client/src/main을 수정한다.
./scripts/check-workspace.sh resilient-http-client
./scripts/mvn-guide.sh -pl :resilient-http-client-reference -am test
```
