# Quorum register 실습 해설

## q1

write ack set A,B,C와 read response set C,D,E의 교차는 C입니다. C의 vector A:1은 D와 E의 초기 vector를 지배하므로 v1을 반환하고 D,E를 repair 대상으로 둡니다.

이 한 trace는 membership freshness, concurrent write, coordinator crash와 read linearization point를 모두 검사하지 않으므로 linearizability 증명이 아닙니다. 사람 evidence는 실제 set 교차와 version comparison을 별도 표로 제시해야 합니다.

## q2

red의 vector A:1과 blue의 vector D:1은 어느 쪽도 다른 쪽을 component-wise 지배하지 않아 concurrent합니다. C가 두 sibling을 모두 가지고 있으므로 read API는 red와 blue를 보존해 반환하거나 application merge를 수행해야 합니다.

사람 검토에서는 last-write-wins를 선택할 경우 clock 가정과 손실 가능성을 별도로 기록합니다. Fixture는 업무적으로 올바른 merge 함수를 결정하지 않습니다.

## q3-sloppy

첫 actual write set A,B,X와 두 번째 set C,D,Y의 교차는 없습니다. Home set에 W=3이라고 적혀 있어도 실제 fallback placement가 겹치지 않으므로 strict quorum intersection을 사용할 수 없습니다.

Hint owner, home epoch, handoff 상태와 read가 fallback을 찾는 규칙이 필요합니다. 이 fixture만으로 실제 durability 수명이나 hinted handoff 완료 시간을 판정하지 않습니다.

## q4-membership

old set A,B,C,D,E와 new set F,G,H,I,J는 완전히 분리되어 majority도 교차하지 않습니다. 즉시 전환하면 old와 new coordinator가 독립적으로 write를 승인할 수 있습니다.

안전한 transition은 joint/overlap configuration 또는 해당 protocol이 증명한 단일-node change를 사용하고, storage owner가 epoch 7 request를 거절하도록 fencing해야 합니다. 사람 evidence는 transition 중 각 decision에 필요한 quorum을 보여야 합니다.
