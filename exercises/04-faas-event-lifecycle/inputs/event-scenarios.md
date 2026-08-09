# Event 시나리오

문서가 object storage에 업로드되면 queue가 function을 호출합니다. function은 원본을 읽고 변환 결과를 object storage에 저장하며 database status와 tenant usage를 갱신합니다.

source는 managed queue이고 message lease가 끝나기 전에 function이 ack해야 합니다. batch는 최대 10건이며 record별 실패 응답을 사용할 수 있다고 가정합니다. 공급자가 정확히 한 번의 업무 효과를 보장한다고 가정하지 않습니다.

| 실패 ID | 입력 사건 | 반드시 판정할 source·invocation 상태 |
|---|---|---|
| `F04-01` | 결과 object 저장 뒤 database update·ack 전에 invocation timeout | `EFFECT_COMMITTED`, status unknown, ack 미완료, lease 뒤 재전달 |
| `F04-02` | 같은 tenant의 같은 producer event가 두 번 전달 | provider delivery ID가 아니라 tenant 범위 business key로 duplicate 판정 |
| `F04-03` | 변환할 수 없는 파일이 모든 retry에서 실패 | terminal 분류, bounded attempt·age, failure destination owner |
| `F04-04` | 10개 batch 중 한 건만 실패 | 성공 record ack, 실패 record 재전달, checkpoint/partial response |
| `F04-05` | 한 tenant가 event 10,000개를 생성해 공유 concurrency를 독점 | tenant별 in-flight·backlog·retry budget과 정상 tenant 잔존 처리량 |
| `F04-06` | tenant가 삭제된 뒤 늦은 retry 도착 | terminal reject, output·queue cleanup과 삭제 evidence |
| `F04-07` | 새 function version이 event schema v1을 더 이상 이해하지 못함 | version adapter·격리·failure destination 중 선택, 무한 retry 금지 |
| `F04-08` | failure destination의 event를 운영자가 수동 replay | replay ID, 선택 function version, 기존 effect, 승인과 correction record |

모든 판정에는 `event_id`, `tenant_id`, source position, attempt, function version, deadline, external effect, ack/checkpoint, retry decision, 비용 driver와 evidence field가 포함되어야 합니다.
