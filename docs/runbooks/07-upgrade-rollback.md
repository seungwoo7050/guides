# Upgrade rollback

## 증상

- Platform component/profile/cluster upgrade 뒤 journey 실패가 증가합니다.
- 특정 workload가 새 version에서 Ready가 되지 않습니다.
- Policy·telemetry·network 동작이 이전과 달라집니다.
- Migration wave가 abort criteria를 넘습니다.

## 먼저 고정할 것

```text
platform release와 component version
migration ID와 wave
영향받는 tenant/profile/workload
이전 version과 rollback target
변경 시점과 첫 실패
```

## 검사 순서

1. Canary와 current wave의 SLI·error·support signal을 비교합니다.
2. Platform defect, workload incompatibility, capacity와 dependency를 분류합니다.
3. Preflight에서 누락된 variation 또는 exception을 찾습니다.
4. State/data/schema write가 이미 발생했는지 확인합니다.
5. Previous binary/profile이 current state를 읽을 수 있는지 확인합니다.
6. Rollback이 node drain, credential, network와 data에 미치는 영향을 검토합니다.
7. 아직 변경되지 않은 wave를 중단합니다.

## Rollback 가능 조건

- 이전 component가 current state/schema와 호환됩니다.
- Old credential/trust root가 안전하게 사용 가능합니다.
- Data/storage format이 되돌릴 수 있습니다.
- Capacity가 reverse rollout surge를 감당합니다.
- Desired state와 profile reference를 함께 되돌립니다.

조건이 충족되지 않으면 forward repair 또는 restore를 선택합니다.

## 실행 원칙

```text
신규 wave 중단
→ 영향 범위 격리
→ rollback/forward repair 결정
→ canary 복구
→ 단계적 확대
→ user journey 검증
→ backlog drain
→ 임시 예외 정리
```

Component version만 되돌리고 migration marker 또는 policy/profile version을 그대로 두지 않습니다.

## 복구 판정

- 핵심 journey와 representative workload가 통과합니다.
- Current desired/observed version이 일치합니다.
- Migration 상태가 `RolledBack` 또는 `Completed`로 명확합니다.
- Stale node/object/credential가 없습니다.
- Queue와 error budget이 정상화됩니다.
- 영향받은 owner에게 결과와 다음 계획을 알립니다.

## 후속 action

- compatibility matrix
- canary coverage
- preflight fixture
- rollback drill
- state migration guard
- deprecation 일정 재검토
