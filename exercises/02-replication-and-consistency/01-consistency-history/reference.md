# Consistency history 실습 해설

각 판정은 histories.json의 invocation, completion, process와 result만 사용합니다. 한 history의 통과는 구현 전체의 consistency 보장이 아닙니다.

## h1

w1이 완료된 뒤 r1이 시작하고 r1은 1을 반환합니다. Legal order는 w1, r1이며 linearizable하고 sequentially consistent합니다. Read는 write를 관찰하므로 causal visibility도 맞습니다.

사람 evidence는 real-time edge w1→r1과 sequential state 0→1을 포함해야 합니다. 두 operation만으로 concurrent path나 failure behavior는 평가하지 못합니다.

## h2

w1 완료 뒤 r1이 시작했지만 r1은 0을 반환합니다. Real-time edge 때문에 w1을 r1 뒤로 옮길 수 없어 linearizable하지 않습니다. 두 process 사이 real-time을 무시하는 sequential consistency에서는 r1, w1 순서가 가능하므로 통과합니다.

최소 linearizability 반례는 w1과 r1입니다. 이 history에는 cross-process causal dependency가 기록되지 않아 causal consistency 위반이라고 단정하지 않습니다.

## h3

w1 완료 뒤 첫 read r1이 0을 반환하므로 linearizable하지 않습니다. Sequential order r1, w1, r2는 c2의 r1→r2 program order를 보존하고 결과도 맞으므로 sequentially consistent합니다. 같은 session이 0 다음 1을 보므로 monotonic read도 깨지지 않습니다.

사람 evidence는 real-time order와 process order를 서로 다른 edge 집합으로 제시해야 합니다. Fixture는 write를 c2가 causally 관찰했다는 별도 token을 포함하지 않습니다.

## h4

w1은 r1과 r2 모두와 겹칩니다. r1은 0, r2는 1을 반환하므로 r1, w1, r2에 linearization point를 둘 수 있습니다. 따라서 linearizable하고 sequentially consistent합니다.

Completion timestamp만 정렬하면 w1을 잘못 배치할 수 있으므로 invocation과 overlap을 함께 보여야 합니다.

## h5

c1은 x=1을 쓴 뒤 읽고, 그 관찰에 의존해 y=1을 씁니다. c2가 y=1을 본 뒤 x=0을 읽었습니다. wx→rx→wy→ry→rx2라는 process/read-from causal chain이 있으므로 rx2가 초기 x를 반환하면 causal visibility를 위반합니다.

같은 chain 때문에 하나의 legal sequential order도 없고, wx가 완료된 뒤 rx2가 시작했으므로 linearizable하지도 않습니다. 최소 causal 설명에는 wx, wy, ry, rx2와 dependency가 필요합니다.

## h6

w1은 pending이지만 r1이 1을 관찰했습니다. Pending write를 drop하면 legal하지 않지만 w1이 적용되고 response만 사라졌다고 completion을 보완하면 w1, r1 순서가 가능합니다. 따라서 admissible completion 아래 linearizable합니다.

사람 evidence는 w1을 포함한 해석과 제거한 해석을 모두 기록해야 합니다. 내부 commit evidence가 없으므로 실제 적용 여부를 확정하는 것은 아닙니다.
