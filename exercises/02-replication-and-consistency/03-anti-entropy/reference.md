# Anti-entropy 실습 해설

## dominant-repair

A와 B의 vector A:2는 C의 A:1을 지배합니다. n2에서 v2를 C로 보내고 v1을 제거해도 causal information을 잃지 않습니다. n3 뒤 세 replica의 frontier는 A:2이고 값은 v2입니다.

사람 evidence는 source가 authoritative하다는 근거, repair task epoch와 duplicate delivery의 idempotence를 포함해야 합니다. 이 fixture는 checksum corruption 여부를 판정하지 않습니다.

## concurrent-siblings

red vector A:1과 blue vector B:1은 어느 쪽도 다른 쪽을 지배하지 않습니다. 따라서 b2 뒤 모든 replica는 red와 blue sibling을 모두 보존해야 합니다. b3의 duplicate exchange는 sibling을 추가로 늘리거나 한쪽을 제거하면 안 됩니다.

사람은 application merge를 선택할 경우 commutative, associative, idempotent 여부와 업무 의미를 검토해야 합니다. 자동 결과는 어떤 색이 제품상 정답인지 선택하지 않습니다.

## tombstone-resurrection

A/B의 tombstone A:2는 C의 value A:1을 지배합니다. C가 delete frontier를 관찰하지 않은 상태에서 f2가 age만 근거로 tombstone을 제거하므로 f2가 첫 안전한-GC 계약 위반입니다. 이후 f4에서 남은 v1이 A/B로 복사되면 삭제한 값이 부활합니다.

안전한 GC에는 모든 active replica frontier, removed replica fencing 또는 오래된 replica의 full bootstrap 정책이 필요합니다. 사람 evidence는 backup restore와 membership까지 포함한 tombstone horizon을 설명해야 합니다. 이 trace는 실제 GC 기간의 적절한 숫자를 정하지 않습니다.
