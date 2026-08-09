# Failure model 실습 해설

timeout, acknowledgment와 restart 관찰은 실제 장애 상태 전체를 직접 알려 주지 않습니다. 아래 결과는 fixture에 주어진 관찰만 사용합니다.

## slow-or-crashed

heartbeat가 timeout 전 도착하지 않았다는 사실만 관찰했습니다. Leader crash, message delay, one-way partition, A 또는 B의 pause가 모두 가능합니다. 따라서 B가 A를 suspect하고 election을 시작할 수는 있지만 A의 durable state를 삭제하거나 external write 권한이 즉시 사라졌다고 결론내릴 수 없습니다.

Safety는 term, durable vote와 quorum으로 지켜야 합니다. Liveness는 connected majority, timer 실행과 eventual delivery 조건이 없으면 지연될 수 있습니다. 사람이 제출할 evidence는 양방향 link 관측, A의 process/incarnation, term과 quorum contact 기록입니다. 이 trace만으로 실제 원인을 하나로 좁힐 수 없습니다.

## vote-before-persist

A가 term 7의 B에게 vote를 승인한 사실을 durable하게 저장하기 전에 response를 보냈습니다. Crash 뒤 A는 같은 term의 C에게 다시 vote할 수 있으므로 Vote Safety와 Election Safety의 전제가 깨집니다.

최초 잘못된 promise는 granted response를 persist보다 먼저 보낸 event입니다. 수정은 currentTerm과 votedFor를 원자적으로 durable하게 저장한 뒤 success response를 내보내는 것입니다. 사람이 storage completion과 outbound response 순서를 trace로 제시해야 하며, 단순한 final leader 수만으로 persist ordering을 증명할 수는 없습니다.

## partitioned-register

A와 B/C가 서로 통신할 수 없는 동안 양쪽 write를 모두 성공시키고 linearizable single register도 유지하라는 요구는 충돌합니다. 두 write가 완료됐다고 응답한 뒤 서로의 값을 모르는 read를 허용하면 하나의 real-time sequential order를 보장할 수 없습니다.

선택지는 minority write 거절 또는 대기, 혹은 local write와 conflict를 허용하는 더 약한 consistency 계약입니다. 사람이 client invocation/completion history와 partition 방향을 제출해야 합니다. Fixture는 latency, session guarantee나 conflict merge 정책을 정하지 않으므로 그 품질은 자동 판정하지 않습니다.

## crash-recovery-log

C가 e9를 durable하게 보존했다는 의미로 acknowledgment를 보냈는데 restart 뒤 e8까지만 복원됐다면 acknowledgment 계약 위반입니다. Leader가 이 ack를 majority evidence로 사용했다면 acknowledged/committed write loss로 이어질 수 있습니다.

수정은 durable append 또는 flush 완료 뒤 success를 보내고, restart 시 checksum과 log boundary를 검증하는 것입니다. 사람이 ack 의미와 leader의 나머지 quorum evidence를 제시해야 실제 client-visible safety 영향까지 판정할 수 있습니다.
