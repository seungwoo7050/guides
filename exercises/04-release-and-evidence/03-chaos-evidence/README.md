# 장애 전·중·복구 후의 근거

## 목표

장애 실험을 한 번에 하나의 실패 조건으로 실행하고, 정리나 복구가 실패 당시의 상태를 덮어쓰기 전에 증거를 보존합니다.

## 문제 계약

실습은 브로커가 중단된 상태에서 다음 흐름을 실행합니다.

1. 장애 전 상태를 기록합니다.
2. 예약과 Outbox를 같은 로컬 변경으로 남깁니다.
3. 브로커 전송 실패 뒤 장애 중 상태를 기록합니다.
4. 브로커를 복구하고 재조정합니다.
5. 업무 상태가 수렴한 뒤 복구 후 상태를 기록합니다.

이 결정적 모델이 지원하는 실패 주입은 `BROKER_DOWN` 하나입니다.
`DATABASE_DOWN`은 다른 시나리오가 조용히 성공한 것처럼 보이지 않도록 명시적으로
거절합니다. 데이터베이스 장애의 transaction·복제·복구 의미론은 이 실습 범위가 아닙니다.

각 snapshot은 이후 상태와 분리된 불변 값이어야 합니다. `processUp=true`만으로 복구를 선언할 수 없으며, Outbox가 비어 있고 읽기 모델이 원본과 같아야 합니다.

## 실패 조건

skeleton은 장애 중 snapshot을 남기지 않고 마지막 상태만 반환합니다. 이 경우 복구는 성공해도 장애 당시 어떤 중간 상태가 존재했는지 증명할 수 없습니다.

## 권장 구현 순서

`reference/` 전체가 하나의 numbering scope입니다. 아래 Implementation 번호는 권장
구현 순서이며 실제 과거 작성 순서를 뜻하지 않습니다.

| 구현 단계 | 파일·경계 | 책임 |
|---:|---|---|
| Implementation 1 | `Phase`, `Failure`, `Result` | 지원 실패 단계와 독립 판정 vocabulary를 고정합니다. |
| Implementation 2 | `Snapshot` | 한 시점의 업무 상태를 이후 mutation과 분리합니다. |
| Implementation 2-1 | `Report` | 가설·예산·판정과 snapshot을 하나의 evidence로 묶습니다. |
| Implementation 3 | `Scenario` | 원본·Outbox·읽기 모델 상태를 소유합니다. |
| Implementation 3-1 | canonical `run` | 단일 지원 실패와 evidence budget을 mutation 전에 검증합니다. |
| Implementation 3-2 | `report` | primary와 cleanup 결과를 독립적으로 판정합니다. |
| Implementation 3-3 | `publishPending` | broker 복구 뒤 업무 상태를 수렴시킵니다. |

먼저 `./scripts/new-workspace.sh chaos-evidence`로 안전한 복사본을 만들고
`.workspace/chaos-evidence`만 수정합니다. 정본 검사를 통과하고 장애 전·중·후 근거가
필요한 이유를 설명한 뒤에만 `reference/`의 순서와 결과를 비교합니다.

## 완료 기준

- 같은 operation ID와 단조 증가한 경과 시간으로 연결된 `BEFORE`, `DURING`, `AFTER` 증거가 모두 남습니다.
- 장애 중 snapshot은 복구·정리 뒤에도 변하지 않고 Outbox 미수렴을 보여 줍니다.
- primary 결과와 cleanup 결과를 분리하며 최종 상태는 시간 한도 안의 원본·읽기 모델 수렴을 증명합니다.
- 지원하지 않는 실패 종류는 snapshot이나 성공 보고서를 만들기 전에 거절합니다.

## 자기 설명

- cleanup 전에 장애 증거를 고정해야 하는 이유는 무엇입니까?
- 실험 실패와 정리 실패를 하나의 상태로 합치면 어떤 진단 정보가 사라집니까?

## 검증

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/chaos-evidence
```

workspace 검사가 통과하고 자기 설명을 마친 뒤에만 `reference/`의 snapshot과
권장 구현 순서를 비교합니다.

- `BEFORE`, `DURING`, `AFTER` snapshot이 모두 남습니다.
- 장애 중에는 원본 1건, Outbox 1건, 읽기 모델 0건입니다.
- 복구 뒤에는 Outbox가 비고 읽기 모델이 원본과 같습니다.
- 여러 실패를 한 시나리오에 동시에 주입하려 하면 거절합니다.
- 저장된 장애 중 snapshot은 복구 뒤에도 바뀌지 않습니다.
- 최종 상태가 수렴해도 시간 한도를 넘기면 primary 결과는 실패합니다.
