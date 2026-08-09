# Membership change 기대 결과

## Safe joint consensus

D는 e2에서 committed prefix index 10까지 따라잡은 뒤에만 new voter set에 들어갑니다. e5의 joint configuration commit은 old quorum `{A,B}`와 new quorum `{B,C}`를 동시에 만족하며 두 집합은 B에서 교차합니다.

A가 crash한 뒤 B의 vote `{B,C,D}`는 old set `{A,B,C}`에서 B·C 두 표, new set `{B,C,D}`에서 세 표를 가져 joint election 조건을 만족합니다. final configuration entry index 12도 B·C가 old quorum, B·C·D가 new quorum을 만족하므로 commit할 수 있습니다.

final configuration이 commit된 뒤 A는 voter가 아닙니다. e11의 epoch 10 write는 current configuration epoch 12보다 오래됐으므로 storage boundary에서 `STALE_CONFIGURATION`으로 거절합니다.

## Unsafe disjoint switch

old majority `{A,B}`와 new majority `{D,E}`는 교차하지 않습니다. e2의 direct switch 뒤 새 group은 index 21에 `x=2`를 commit할 수 있지만 old group은 같은 index에 이미 `x=1`을 commit했습니다. e2가 첫 unsafe transition이며 state-machine safety와 leader completeness를 보존할 연결 evidence가 없습니다.

## Catch-up 전 승격

D의 match index 8은 committed index 10보다 뒤처집니다. e1의 승격은 거절돼야 합니다. D는 log freshness 검사에서도 candidate가 될 수 없으며, D를 quorum 계산에 넣는 구현은 committed prefix를 잃을 위험을 만듭니다.

## 사람 검토 질문

- configuration을 external metadata가 아니라 replicated log의 ordered state로 다뤘습니까?
- joint phase에서 election과 log commit 모두 dual quorum을 사용합니까?
- learner catch-up 기준이 단순 snapshot copy가 아니라 committed frontier입니까?
- removed node fencing이 client redirect가 아닌 write 적용 경계에 있습니까?

## 이 결과가 증명하지 않는 것

한 번의 joint transition만 다룹니다. 여러 변경의 동시 진행, learner snapshot chunking, configuration rollback, witness node와 large-cluster quorum 성능은 별도 검증이 필요합니다.
