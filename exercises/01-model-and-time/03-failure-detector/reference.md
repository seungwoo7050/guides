# Failure detector 실습 해설

## stable-heartbeats

step 2 heartbeat 뒤 last heartbeat는 2, step 6 뒤에는 6입니다. step 10 tick에서 elapsed는 4이므로 timeout 5보다 작고 최종 상태는 ALIVE입니다. Suspicion transition은 없습니다.

사람 evidence는 각 tick에서 elapsed 계산과 heartbeat incarnation 검사를 포함해야 합니다. 이 정상 trace는 message loss나 process pause가 있는 실행의 liveness를 보장하지 않습니다.

## delayed-heartbeat

step 4에서는 elapsed 4이므로 ALIVE입니다. step 5에서는 elapsed 5가 되어 SUSPECT가 됩니다. Step 6 heartbeat는 monitored incarnation 1과 일치하므로 last heartbeat를 6으로 갱신하고 ALIVE로 돌아갑니다.

SUSPECT는 관찰 가능한 detector output이지 A의 crash fact가 아닙니다. 사람이 false suspicion 중 election이 일어나더라도 term, durable vote와 quorum이 safety를 지키는 이유를 설명해야 합니다. 실제 detector timeout 튜닝 품질은 이 세 event로 판정할 수 없습니다.

## timeout-as-proof

f1과 f2의 suspicion은 허용 가능한 detector 동작입니다. f3은 timeout 하나만 evidence로 configuration member를 영구 제거하므로 첫 계약 위반입니다. f4에서 같은 incarnation heartbeat가 도착해 이전 관찰이 delay 또는 pause와도 양립했음을 보여 줍니다.

올바른 membership 변경에는 consensus로 정렬된 configuration entry, quorum rule과 removed actor fencing이 필요합니다. 사람이 어떤 reversible action은 suspicion만으로 허용하고 어떤 irreversible action은 추가 evidence를 요구하는지 표로 제출해야 합니다. Late heartbeat 하나는 A가 전체 기간 내내 정상 처리 가능했다는 증거까지 제공하지는 않습니다.
