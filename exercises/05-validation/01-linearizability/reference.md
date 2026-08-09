# Linearizability history 기대 결과

| History | 판정 | Witness 또는 최소 모순 |
|---|---|---|
| `completed-write-then-read` | linearizable | `w1 → r1` |
| `stale-read-after-completion` | not linearizable | `w1` response가 `r1` invoke보다 먼저인데 `r1=0` |
| `overlapping-write-and-reads` | linearizable | `r1 → w1 → r2 → r3` |
| `new-then-old-during-one-write` | not linearizable | `r1=1`이면 write 뒤, 이후 `r2=0`은 write 앞으로 둘 수 없음 |
| `pending-write-observed` | linearizable | pending `w1`을 포함해 `w1 → r1`; drop만 하면 불가능 |
| `two-overlapping-writes` | linearizable | `w2 → w1 → r1` |

checker의 `explored_states` 수는 구현의 후보 순서와 memoization에 따라 달라질 수 있으므로 정답 값이 아닙니다. 판정, witness의 legality와 pending 포함 여부가 공개 결과입니다.

## 사람 검토 질문

- 모든 non-overlapping real-time edge를 먼저 만들었습니까?
- pending operation을 drop한 경우와 completion을 가정한 경우를 구분했습니까?
- 위반 history에서 관련 없는 operation을 제거해도 같은 모순이 남습니까?
- single-register 결과를 multi-key transaction의 atomicity 주장으로 확장하지 않았습니까?

## 이 결과가 증명하지 않는 것

작은 고정 history의 판정만 확인합니다. workload coverage, history recorder의 정확성, CAS·transaction semantics와 production 실행 전체의 linearizability는 별도 근거가 필요합니다.
