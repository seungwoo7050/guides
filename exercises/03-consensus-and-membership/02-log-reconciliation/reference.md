# Log reconciliation 기대 결과

## Conflicting suffix

처음 세 시도는 각각 follower에 index 7이 없거나, index 6·5의 term이 leader가 제시한 term과 달라 거절됩니다. 이 실패는 follower log를 변경하지 않습니다.

`a4`의 `(prevLogIndex=3, prevLogTerm=3)`은 공통 prefix와 일치합니다. follower는 index 4부터 자신의 term 5 suffix를 제거하고 leader의 entry를 붙입니다. 최종 term sequence는 다음과 같습니다.

```text
[1, 1, 3, 4, 4, 7, 8]
```

성공 뒤 `matchIndex[F]=7`, `nextIndex[F]=8`입니다. conflict-term hint를 사용하면 follower의 term 5가 시작한 index 4로 한 번에 이동할 수 있고, 단순 decrement는 더 많은 round trip을 사용합니다.

## Current-term commit

`s1`에서 leader A는 index 5까지 갖지만 index 5(term 7)는 quorum에 복제되지 않았습니다. index 4(term 6)가 A·B·C에 존재해도 current-term counting rule로 직접 commit할 수 없으므로 commit index는 2에 머뭅니다.

`s2`에서는 term 7의 index 5가 A·B·C에 복제됐습니다. leader는 index 5를 commit하고 그 prefix인 index 3·4도 함께 committed로 만들 수 있습니다.

## 사람 검토 질문

- rejected AppendEntries가 follower suffix를 바꾸지 않았습니까?
- 같은 index의 term만 비교하지 않고 공통 prefix의 의미를 설명했습니까?
- `replicated`, `committed`, `applied`, `client-visible`을 구분했습니까?
- client response를 `append → persist → replicate → commit → apply` 뒤에 두었습니까?

## 이 결과가 증명하지 않는 것

이 fixture는 한 follower의 reconciliation과 두 replication snapshot만 다룹니다. leader crash, snapshot boundary, membership change와 모든 possible suffix를 포괄하지 않습니다.
