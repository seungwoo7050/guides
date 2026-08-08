# 동시성 검토 산출물

자동 SQL fixture는 tenant foreign key, 상태 조합, migration, 세 workload의 결과와 plan을 검사한다. 활성 membership의 비활성화와 assignee 변경이 동시에 일어나는 운영 경쟁은 자동으로 재현하지 않는다.

## 두 session 순서

| 단계 | session A: membership 변경 | session B: ticket 담당자 변경 | 관찰한 lock·결과 |
|---|---|---|---|
| 1 | 실행할 SQL | 실행 전 상태 | 기록 |
| 2 | 경쟁 지점 | 실행할 SQL | 기록 |
| 3 | commit 또는 rollback | commit 또는 rollback | 기록 |

## 허용·금지 결과

- 허용할 최종 상태와 그 불변식을 적는다.
- 금지할 최종 상태와 이를 차단하는 DB 또는 application 장치를 적는다.

## 책임과 재시도

Lock 순서 또는 isolation 수준, 재시도 가능한 오류, DB가 직접 보장하는 범위와 application이 보장해야 하는 범위를 적는다.
