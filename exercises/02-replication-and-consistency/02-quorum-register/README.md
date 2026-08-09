# 실습: quorum register

## 목표

quorum set의 교차 여부와 version 선택·conflict·membership이 제공하는 보장을 따로 판정합니다.

## 입력

[`topology.json`](topology.json)은 `N=5`, `R=3`, `W=3`인 home set과 네 scenario를 제공합니다.

## 작업

### q1: stale replica가 포함된 read

- read set과 write set의 교차 node를 찾습니다.
- 어떤 version을 반환해야 하는지 설명합니다.
- response 전·후 read repair의 차이를 적습니다.
- 이 trace 하나만으로 linearizability를 증명할 수 없는 이유를 적습니다.

### q2: concurrent sibling

- 두 version이 component-wise 비교 가능한지 확인합니다.
- 한 값을 버리지 않고 반환·merge하는 API를 설계합니다.
- last-write-wins를 선택한다면 필요한 clock 가정과 data loss를 기록합니다.

### q3: sloppy quorum

- 두 actual write set이 교차하는지 확인합니다.
- home set의 `W=3`이라는 표기가 actual durability·consistency를 설명하지 못하는 이유를 적습니다.
- hinted handoff와 read path에 필요한 metadata를 설계합니다.

### q4: membership

- old/new quorum이 교차하는지 확인합니다.
- stale coordinator write를 storage node가 거절할 epoch contract를 작성합니다.
- 안전한 transition state를 제안합니다.

## 제출

```text
analysis.md
protocol.md
- version compare
- read selection
- conflict response
- repair
- membership epoch
```

선택 구현은 JSON fixture를 읽고 quorum 교차와 vector dominance를 계산합니다.

## 대표 오답

- `R+W>N`만으로 q2 conflict를 제거합니다.
- replica C가 두 write를 받았다는 이유로 어느 것이 최신인지 timestamp 없이 판정합니다.
- sloppy quorum의 fallback node를 home replica와 동일하게 취급합니다.
- membership epoch를 coordinator에서만 검사합니다.

## 완료 조건

- quorum 교차와 최신 version 판정을 구분합니다.
- concurrent sibling을 보존합니다.
- partial write와 repair owner를 명시합니다.
- old/new membership write authority를 fencing합니다.

## 기대 결과와 검토

- [해설](reference.md)은 quorum 교차, vector relation과 membership 전이를 scenario별로 풉니다.
- [기계 판정값](expected.json)은 실제 replica set과 version vector에서 결과를 다시 계산합니다.
- 저장소 루트에서 다음 명령을 실행합니다.

    python3 scripts/check_exercises.py exercises/02-replication-and-consistency/02-quorum-register
