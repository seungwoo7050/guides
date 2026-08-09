# 실습: anti-entropy와 안전한 수렴

## 목표

Replica version을 비교해 dominant update를 복구하고 concurrent sibling을 보존합니다. Tombstone을 충분한 evidence 없이 제거했을 때 오래된 replica가 값을 되살리는 실패를 추적합니다.

## 입력

[repairs.json](repairs.json)은 세 scenario를 제공합니다.

- dominant-repair: 새 version이 오래된 replica를 repair합니다.
- concurrent-siblings: 두 vector가 concurrent여서 둘 다 보존해야 합니다.
- tombstone-resurrection: offline replica가 delete를 관찰하기 전에 tombstone을 GC합니다.

## 작업

각 scenario에서 다음을 제출합니다.

1. 모든 version pair의 dominates, equal, concurrent 관계
2. source와 target을 선택한 이유
3. repair 뒤 replica별 sibling set
4. tombstone 또는 value를 버려도 되는 evidence
5. membership epoch가 바뀌면 기존 repair task를 어떻게 fencing하는지

## 정상·경계·실패

- 정상: dominant-repair에서 v2가 v1을 지배하고 C가 v2로 수렴합니다.
- 경계: concurrent-siblings에서 red와 blue를 모두 보존합니다.
- 실패: tombstone-resurrection에서 모든 replica frontier 확인 전 tombstone GC가 첫 위반입니다.

## 제출과 사람 검토

analysis.md에 version comparison, event별 replica state, first violation, safe retry와 model gap을 기록합니다. Merge가 제품 의미와 맞는지는 자동 checker가 결정하지 않습니다.

[해설](reference.md)과 [기계 판정값](expected.json)을 비교한 뒤 저장소 루트에서 실행합니다.

    python3 scripts/check_exercises.py exercises/02-replication-and-consistency/03-anti-entropy

## 한계

Merkle tree 효율, bandwidth, 실제 storage corruption과 background scheduling은 다루지 않습니다. Fixture의 vector와 event가 정확하다는 가정 아래 수렴 state만 검사합니다.

## 완료 조건

- dominant version과 concurrent sibling을 구분합니다.
- repair message 중복에도 같은 state로 수렴하는 설계를 제시합니다.
- tombstone GC를 replica frontier, membership과 bootstrap policy에 연결합니다.
- 정상 divergence와 corruption을 구분할 추가 evidence를 적습니다.
