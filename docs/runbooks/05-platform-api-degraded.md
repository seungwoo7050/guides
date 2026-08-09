# Platform API degraded

## 증상

- API error/latency가 SLO를 위반합니다.
- Request는 accepted됐지만 status를 조회할 수 없습니다.
- Portal과 CLI에서 동일한 오류가 발생합니다.
- Controller가 정상이어도 새 operation 생성이 막힙니다.

## 영향 분리

- 기존 workload는 계속 실행되는가?
- Read와 write가 모두 실패하는가?
- 특정 tenant/API version/resource kind만 영향받는가?
- Portal만 실패하고 API는 정상인가?
- API는 정상인데 identity/policy/dependency가 실패하는가?

## 검사 순서

1. 외부 synthetic journey와 API SLI를 확인합니다.
2. Request ID와 stable error code를 확보합니다.
3. API instance, load balancer, identity, policy, state store를 계층별로 확인합니다.
4. Queue와 downstream controller 상태를 확인합니다.
5. 최근 release/config/schema migration을 확인합니다.
6. Resource saturation, connection pool과 rate limit을 확인합니다.
7. Partial write와 idempotency 상태를 확인합니다.

## 안전한 완화

- 위험한 write를 차단하고 read/status를 유지할 수 있습니다.
- Bad release면 previous compatible version으로 되돌립니다.
- Hot tenant/request type이면 좁은 rate limit을 적용합니다.
- Dependency outage면 retry storm을 줄이고 명확한 `Retry-After`와 condition을 반환합니다.
- Portal 장애면 API/CLI 대체 경로를 안내합니다.

State store consistency를 확인하지 않고 instance를 반복 재시작하거나 schema를 되돌리지 않습니다.

## 복구 판정

- Synthetic journey가 성공합니다.
- Error budget burn과 latency가 정상화됩니다.
- Accepted operation의 status와 external effect가 일치합니다.
- Duplicate/partial resource가 없습니다.
- Queue backlog를 priority와 capacity에 맞게 drain합니다.
- 임시 read-only/rate limit을 제거합니다.
