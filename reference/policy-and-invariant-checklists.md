# 운영체제 정책과 불변식 점검표

이 문서는 새로운 운영체제 문제를 만났을 때 복사해 사용하는 분석 양식입니다. 알고리즘 이름이나 도구를 먼저 고르지 않고 **제한된 자원, 상태 소유자, 사건, 정책, 불변식, 진행과 관측 근거**를 먼저 적습니다.

## 공통 분석 양식

```text
문제와 사용자에게 보이는 증상:
제한된 자원:
자원 단위:
요청자와 소유자:
현재 상태:
가능한 상태 전이:
전이를 일으키는 사건:
후보 집합:
선택 정책과 동률 해소:
실패·취소·timeout 전이:
항상 참이어야 하는 불변식:
진행 보장:
관측 가능한 증거:
복구와 마지막 정리 책임:
```

정책 변경 전후에는 같은 작업량, 같은 초기 상태, 같은 지표와 같은 실패 주입을 사용합니다.

## 커널 경계와 사건

```text
진입 원인은 system call, exception, fault 또는 interrupt 중 무엇입니까?
현재 instruction과 동기적입니까?
처리 뒤 같은 instruction을 다시 실행할 수 있습니까?
사용자 pointer와 length를 어디서 검증합니까?
현재 문맥에서 block할 수 있습니까?
부분 성공이 가능합니까?
오류를 반환값, signal 또는 process 종료 중 무엇으로 전달합니까?
```

불변식:

- kernel은 검증되지 않은 사용자 주소와 길이를 신뢰하지 않습니다.
- 사용자 모드로 복귀하기 전 register, stack과 권한 상태가 일관됩니다.
- interrupt acknowledge와 후속 completion이 중복되거나 유실되지 않습니다.
- 실패 뒤 임시 allocation과 kernel object reference가 정해진 소유자에게 돌아갑니다.

## 작업 수명과 queue 위치

```text
작업 식별자:
현재 상태: NEW / READY / RUNNING / BLOCKED / TERMINATED
현재 위치: ready queue / CPU / wait queue / completed
block 이유와 wait channel:
wakeup 사건:
취소와 종료 요청:
join·reap 책임:
```

불변식:

- 한 작업은 같은 순간에 하나의 실행 위치만 가집니다.
- `READY` 작업은 정확히 하나의 ready queue에 있습니다.
- `RUNNING` 작업은 해당 CPU의 현재 작업과 일치합니다.
- `BLOCKED` 작업은 정확한 wait queue와 block 이유를 가집니다.
- `TERMINATED` 작업은 실행·대기 queue에 남지 않습니다.
- stack과 control object는 마지막 관찰자보다 오래 살아 있습니다.

## CPU scheduling

```text
CPU 수:
작업 도착 시점:
CPU burst와 I/O wait:
READY 후보 조건:
선택 key와 동률 해소:
선점 시점:
quantum:
깨운 작업의 삽입 위치:
aging·fairness 정책:
CPU affinity와 migration:
```

필수 지표:

- throughput
- CPU utilization
- response time
- turnaround time
- ready queue waiting time
- context switch 수
- 작업 또는 class별 CPU share
- 최대·상위 percentile 대기 시간

불변식:

- 아직 도착하지 않았거나 `BLOCKED`인 작업을 선택하지 않습니다.
- 완료한 작업을 다시 실행하지 않습니다.
- 같은 CPU에 두 작업이 동시에 `RUNNING`이지 않습니다.
- 실행한 tick과 burst 감소량이 일치합니다.
- I/O 완료 전 작업을 ready queue에 넣지 않습니다.

## block, wakeup과 조건 대기

```text
진행 predicate:
predicate를 보호하는 lock:
wait queue:
조건 검사 시점:
대기 등록 시점:
lock 해제와 block 시점:
notification 또는 event generation:
timeout·cancel 경로:
```

불변식:

- predicate 검사와 wait 등록 사이에 사건을 놓치지 않습니다.
- wakeup은 `BLOCKED → READY`이며 즉시 실행을 보장하지 않습니다.
- waiter는 깨어난 뒤 predicate를 다시 검사합니다.
- 같은 작업이 둘 이상의 wait queue에 존재하지 않습니다.
- timeout, cancel과 정상 completion 중 결과를 정확히 한 번 공개합니다.
- 마지막 cleanup 주체가 하나로 정해져 있습니다.

깨우기 손실 재현:

```text
1. consumer가 predicate를 거짓으로 관찰합니다.
2. consumer를 등록하기 전에 producer가 상태를 바꾸고 알립니다.
3. consumer가 뒤늦게 sleep합니다.
4. 이후 사건이 없을 때 영원히 기다리는지 확인합니다.
```

## 공유 상태와 동기화

```text
공유 object:
읽는 실행 주체:
쓰는 실행 주체:
복합 상태 전이:
보호할 관계식:
선택한 synchronization primitive:
lock order:
공개와 관찰 사이의 ordering:
resource 회수 시점:
```

불변식:

- 같은 불변식을 바꾸는 모든 경로가 같은 동기화 계약을 따릅니다.
- 개별 load·store 원자성과 복합 전이 원자성을 구분합니다.
- 오류와 조기 반환에서도 lock과 permit을 정확히 한 번 반납합니다.
- 공유 object 수명은 마지막 접근보다 깁니다.
- interrupt·timer·다른 CPU 접근도 참여자로 포함합니다.
- 공개된 상태를 본 작업은 그 상태가 의존하는 선행 write도 볼 수 있습니다.

## deadlock과 진행

```text
자원 종류와 instance 수:
각 작업의 allocation:
각 작업의 outstanding request:
wait-for graph:
전역 lock order:
try·rollback 정책:
timeout:
탐지 주기:
victim 선택 기준:
```

진단 순서:

1. 작업별 보유 자원과 대기 자원을 같은 식별자로 기록합니다.
2. 한 시점뿐 아니라 wait graph가 유지되는 시간을 확인합니다.
3. cycle, 다중 instance available 상태와 외부 completion 가능성을 구분합니다.
4. CPU 사용과 유효한 완료 여부로 deadlock, starvation과 livelock을 분리합니다.
5. 복구 뒤 ownership과 queue 위치를 다시 검사합니다.

불변식:

- 문서화한 순서보다 낮은 rank의 lock을 높은 rank 뒤에 획득하지 않습니다.
- 취소·종료한 작업이 자원을 계속 보유하지 않습니다.
- 같은 victim만 반복 선택해 starvation을 만들지 않습니다.
- rollback과 recovery를 반복해도 추가 손상이 생기지 않습니다.

## 주소 공간과 page fault

```text
process와 가상 주소:
해당 mapping 범위:
접근 종류: read / write / execute
mapping 권한:
resident 여부:
backing: zero / file / swap / COW
fault 동안 필요한 I/O와 block:
복구 뒤 instruction 재시도 여부:
```

불변식:

- 한 process의 한 VPN은 최대 하나의 현재 mapping을 가집니다.
- resident mapping은 존재하는 frame을 가리킵니다.
- frame reference count는 그 frame을 가리키는 mapping과 일치합니다.
- 권한 없는 접근을 일반 성공으로 처리하지 않습니다.
- COW 공유 frame을 직접 writable 상태로 공개하지 않습니다.
- mapping 제거와 translation 무효화 전에 frame을 재사용하지 않습니다.
- fault 실패 뒤 임시 frame, I/O request와 wait entry를 회수합니다.

hardware page-table walk, TLB 구조와 ISA별 fence는 컴퓨터 구조 가이드에서 확인합니다.

## reclaim과 page replacement

```text
resident capacity:
reference trace 또는 working set:
후보 page:
clean / dirty / anonymous / file-backed:
pinned·writeback·COW 상태:
선택 정책: FIFO / LRU 근사 / Clock / working set
writeback 실패 처리:
```

필수 관측:

- minor·major fault
- resident set과 working set 추정
- reclaim scan과 성공 수
- dirty writeback 양과 지연
- swap 또는 compressed backing 사용
- pinned page 양
- storage queue latency

불변식:

- pinned 또는 장치 사용 중인 frame을 교체하지 않습니다.
- dirty data를 backing 없이 버리지 않습니다.
- victim의 이전 mapping을 제거한 뒤 frame을 재사용합니다.
- writeback 중 새 write generation을 놓치지 않습니다.
- repeated fault로 유효한 계산이 멈추는 thrashing을 관측합니다.

## 파일시스템과 durability

```text
namespace 변경:
file object와 link count:
page cache 상태:
file data durability:
directory durability:
필요한 write ordering:
장애 모델: process / kernel / power loss
recovery 절차:
```

불변식:

- directory entry는 존재하는 file object를 가리킵니다.
- link count는 durable namespace 참조와 일치합니다.
- 같은 storage block을 상충하는 두 소유자에게 할당하지 않습니다.
- file size와 초기화된 data 범위가 모순되지 않습니다.
- commit되지 않은 journal transaction은 replay하지 않습니다.
- committed transaction replay는 idempotent합니다.
- file data와 parent directory durability를 별도로 검증합니다.

안전한 교체 점검:

```text
같은 filesystem에 임시 file을 만들었습니까?
전체 write와 오류를 확인했습니까?
임시 file을 flush했습니까?
rename의 atomicity 범위는 무엇입니까?
parent directory를 durable하게 만들었습니까?
각 단계 직후 장애 결과를 시험했습니까?
```

## 장치 I/O와 DMA

```text
request id와 owner:
상태: QUEUED / IN_FLIGHT / CANCEL_PENDING / COMPLETED / CANCELLED / REAPED
software queue와 hardware queue 위치:
buffer page와 DMA mapping:
pin 상태:
전송 길이와 partial result:
interrupt 또는 polling completion:
timeout·cancel·reset 경로:
```

불변식:

- 한 request는 한 시점에 하나의 queue 위치만 가집니다.
- in-flight 또는 cancel-pending request만 DMA pin을 유지합니다.
- 장치가 buffer를 사용할 수 있는 동안 free·COW·reclaim하지 않습니다.
- completion 결과와 오류를 owner에게 정확히 한 번 전달합니다.
- 정상 completion, cancel과 timeout 경쟁에서 cleanup 승자가 하나입니다.
- reset 전 늦은 completion을 새 request로 오인하지 않습니다.
- partial transfer 길이는 요청 범위를 벗어나지 않습니다.

필수 지표:

- submission queue 대기
- in-flight 수
- device service time
- interrupt rate 또는 polling CPU 사용
- completion batch 크기
- timeout·cancel·reset 수
- end-to-end percentile latency

## 변경 검증 기록

```text
가설:
변경한 메커니즘 또는 정책:
고정한 초기 상태와 작업량:
정상 상태 전이:
경계값:
실패 주입:
의도적으로 만든 실행 교차:
변경 전 관측값:
변경 후 관측값:
새로 생긴 비용과 위험:
rollback 방법:
```

“더 빠릅니다”나 “안전합니다”로 끝내지 않습니다. 어떤 상태와 입력에서 어떤 지표가 바뀌었고, failure fixture와 불변식 검사가 그대로 통과하는지 기록합니다.
