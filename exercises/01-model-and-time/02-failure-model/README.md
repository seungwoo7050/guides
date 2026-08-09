# 실습: failure model과 보장 범위

## 목표

같은 사건을 crash-stop, crash-recovery, omission과 partition model에서 해석하고 어떤 safety·liveness 주장을 할 수 있는지 구분합니다.

## 입력

[`scenarios.json`](scenarios.json)의 각 scenario는 일부 관찰만 제공합니다. 누락된 사실을 추측하지 않습니다.

## 작업

각 scenario에 다음 표를 작성합니다.

| 항목 | 내용 |
|---|---|
| 실제로 관찰한 것 | timeout, ack, restart state 등 |
| 가능한 실제 상태 | 하나 이상 |
| 필요한 failure model | crash-stop·crash-recovery·omission·partition |
| safety risk | 잘못된 commit·double vote·conflict 등 |
| liveness risk | election churn·blocking 등 |
| 추가 evidence | disk record·term·message trace 등 |
| protocol 수정 | persist-before-send·quorum·fencing 등 |

### FLP 적용

`slow-or-crashed` scenario에서 완전 비동기 model이라면 timeout만으로 정확한 failure 판정을 할 수 없는 이유를 적습니다. 이것이 election safety를 포기해야 한다는 뜻이 아닌 이유도 적습니다.

### CAP 적용

`partitioned-register`에서 partition 양쪽 write availability와 linearizable register를 동시에 요구할 때 생기는 모순을 client history로 작성합니다.

## 대표 오답

- timeout을 crash 확정으로 기록합니다.
- ack를 durable write evidence로 자동 해석합니다.
- FLP를 이유로 consensus safety가 불가능하다고 씁니다.
- CAP를 평상시 latency와 uptime의 일반 trade-off로 설명합니다.
- model 밖 Byzantine behavior를 crash-only protocol의 결함으로 섞습니다.

## 완료 조건

- 관찰과 실제 상태를 분리합니다.
- 각 scenario의 durable·network 가정을 명시합니다.
- safety 위반과 progress 실패를 구분합니다.
- 더 강한 보장을 위해 필요한 protocol state를 제안합니다.

## 기대 결과와 검토

- [해설](reference.md)은 scenario별 관찰, 가능한 상태, 최초 안전성 위험과 필요한 evidence를 제공합니다.
- [기계 판정값](expected.json)은 fixture scenario와 분류가 어긋나지 않는지 검사합니다.
- 저장소 루트에서 다음 명령을 실행합니다.

    python3 scripts/check_exercises.py exercises/01-model-and-time/02-failure-model
