# 동시성 검토 산출물

자동 SQL fixture가 보장하는 범위는 membership **존재**, tenant foreign key, ticket 상태 조합, migration과 세 workload다. 현재 축소 schema에는 membership 활성 상태와 activity table이 없으므로, 비활성화 경쟁이나 activity 기록의 원자성을 자동 검증했다고 주장하지 않는다.

## 두 session 순서

실제 시스템에 `memberships.active`가 추가된 경우 다음 두-session 검토를 수행한다.

| 단계 | session A: membership 비활성화 | session B: ticket 담당자 변경 | 기대 관찰 |
|---|---|---|---|
| 1 | `BEGIN`; 대상 membership을 `SELECT ... FOR UPDATE` | `BEGIN` | A가 membership row lock 보유 |
| 2 | `active=false` 갱신 | 같은 membership을 `SELECT ... FOR UPDATE` | B가 A의 종료까지 대기 |
| 3 | `COMMIT` | 재확인 뒤 inactive이면 담당자 갱신 없이 `ROLLBACK` | inactive assignee가 새로 생기지 않음 |

두 경로 모두 membership row를 먼저, ticket row를 다음에 잠근다. 반대 순서를 섞지 않아 deadlock cycle을 만들지 않는다.

## 허용·금지 결과

- A가 먼저 commit하면 B는 inactive membership을 관찰하고 담당자 변경을 거부한다.
- B가 먼저 membership과 ticket lock을 얻어 commit하면 해당 변경은 허용할 수 있지만, A는 비활성화 전 담당 ticket 처리 정책을 적용해야 한다.
- inactive membership인데 새 assignee만 남는 최종 상태는 금지한다.

## 책임과 재시도

Membership·ticket row lock과 tenant foreign key는 DB transaction 책임이다. “비활성화 시 기존 ticket을 해제할지” 정책, serialization/deadlock 오류의 bounded retry, 외부 알림과 activity 전달은 application 책임이다. 제출물에는 두 session의 SQL, blocking 관찰 시각, 최종 row snapshot과 재시도 결과를 함께 남긴다.
