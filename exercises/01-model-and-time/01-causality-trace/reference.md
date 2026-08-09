# Causality trace 해설

이 문서는 trace.json에서 직접 계산할 수 있는 결과와 사람이 설명해야 하는 근거를 분리합니다. 숫자를 그대로 옮기는 것보다 어떤 edge가 clock 증가를 강제했는지 설명하는 것이 중요합니다.

## clock-and-order

event별 결과는 다음과 같습니다. Vector 순서는 A, B, C입니다.

| Event | Lamport | Vector |
|---|---:|---|
| a1 | 1 | [1, 0, 0] |
| a2 | 2 | [2, 0, 0] |
| b1 | 1 | [0, 1, 0] |
| c1 | 1 | [0, 0, 1] |
| b2 | 3 | [2, 2, 0] |
| b3 | 4 | [2, 3, 0] |
| a3 | 3 | [3, 0, 0] |
| c2 | 5 | [2, 3, 2] |
| c3 | 6 | [2, 3, 3] |
| a4 | 7 | [4, 3, 3] |

같은 process의 바로 이전 event가 만드는 edge는 a1→a2, a2→a3, a3→a4, b1→b2, b2→b3, c1→c2, c2→c3입니다. Message edge는 a2→b2, b3→c2, c3→a4입니다. 이 열 개가 direct edge이고 나머지 causal relation은 transitive closure에서 나옵니다.

예를 들어 a2와 b1, a3와 b2, a3와 b3, a1과 c1, b1과 c1은 어느 방향으로도 도달 경로가 없으므로 concurrent합니다. 두 vector도 서로 component-wise 지배하지 않습니다.

사람 검토에서는 최소 다섯 concurrent pair 각각에 대해 두 방향의 causal path가 모두 없음을 보여야 합니다. 자동 검사는 fixture가 명시한 process 순서와 send/receive만 사용하므로 실제 runtime에서 누락된 message나 잘못 수집된 process 순서는 판정하지 못합니다.

## cut-1

cut-1은 consistent합니다. 포함된 receive b2의 send a2와 receive c2의 send b3가 모두 포함되고, 각 process에서 선택한 event가 prefix를 이룹니다.

사람 검토 evidence는 process별 prefix와 receive별 send를 별도 표로 제시하는 것입니다. 이 fixture의 cut가 consistent하다는 사실은 다른 임의의 global snapshot이 consistent하다는 증거가 아닙니다.

## cut-2

cut-2는 c2를 포함하지만 그 causal predecessor인 b3를 제외하므로 inconsistent합니다. 최소 수정은 b3를 추가하거나 c2를 제거하는 것입니다. b3를 추가하면 cut-1과 같은 event 집합이 됩니다.

첫 위반 edge는 b3→c2입니다. 자동 검사는 이 직접 message edge와 process prefix를 찾지만, application-level dependency처럼 fixture에 기록되지 않은 causality는 알 수 없습니다.
