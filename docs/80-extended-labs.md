# 확장 상태·binary image 실습

이 문서는 핵심 11장을 마친 뒤 선택하는 확장 과정입니다. 이전 평면형 과정에 있던 page-table 계산, MLFQ 정책 기록, 학습용 filesystem image와 device descriptor ring처럼 새 핵심 경로에 완전히 흡수되지 않은 실습을 보존합니다. 실제 kernel 구조를 복제하기보다 입력 계약과 손상 거부 기준을 먼저 고정합니다.

## 학습 목표

- 상태 모델과 binary representation 사이의 변환 경계를 검증합니다.
- 정상 입력뿐 아니라 길이·index·checksum·소유권이 깨진 입력을 안전하게 거부합니다.
- 정책 결과, parser 안전성, concurrency ownership을 서로 다른 검증 근거로 설명합니다.

## 핵심 모델

확장 실습은 다음 artifact를 함께 제출합니다.

```text
입력 format 또는 workload 계약
상태와 소유권 표
정상 결과 하나
한 조건만 깨는 failure fixture 둘 이상
실행 상한과 timeout
결과를 판정하는 독립 계산 또는 checksum
```

완성 reference를 먼저 복사하지 않습니다. 작은 입력을 손으로 계산한 뒤 parser·scheduler·ring 모델을 구현합니다.

## 1. 주소 변환 산술

page 크기가 `2^k` byte라면 virtual address를 VPN과 offset으로 나눕니다.

```text
vpn = virtual_address // page_size
offset = virtual_address % page_size
physical_address = frame * page_size + offset
```

page size 256, virtual address 300, VPN 1이 frame 2를 가리키면 offset은 44, physical address는 556입니다. offset이 변환 전후에 같다는 성질을 작은 oracle로 사용합니다.

추가 계약:

- address와 page size는 음수가 아닙니다.
- page size는 2의 거듭제곱입니다.
- VPN이 page table 범위를 벗어나면 mapping 없음입니다.
- present bit가 꺼졌다면 frame 값이 있어도 바로 변환하지 않습니다.
- read/write/execute 권한을 address 계산과 별도로 판정합니다.

다단계 page table에서는 index bit 수와 level 수를 parameter로 둡니다. “항상 4단계” 같은 특정 architecture 결론을 core 원리로 일반화하지 않습니다.

## 2. MLFQ 정책 trace

MLFQ는 이름 하나가 아니라 규칙 묶음입니다.

```text
queue 수와 queue별 quantum
새 작업의 시작 level
quantum 소진 때 강등 규칙
I/O block·wakeup 때 level 규칙
주기적 priority boost
같은 queue 안의 tie-break
```

세 workload를 비교합니다.

1. 긴 CPU burst 하나
2. 짧은 CPU burst와 I/O를 반복하는 작업
3. 긴 작업이 기다리는 동안 짧은 작업이 계속 도착하는 입력

각 tick의 `running`, queue별 ready 목록, blocked 목록과 남은 quantum을 기록합니다. boost를 끈 trace에서 starvation 가능성을 보이고, boost를 켠 trace에서 가장 긴 ready wait 상한이 어떻게 달라지는지 설명합니다.

독립 검증은 작은 tick 수에서 가능한 후보 선택을 정책 규칙으로 직접 다시 계산합니다. 구현과 같은 heap·queue helper를 oracle에서 공유하지 않습니다.

## 3. `KMODFS01` 학습용 image

이 실습은 실제 filesystem on-disk format이 아닙니다. 256-byte block 6개로 이름, inode, data block의 연결을 파싱하는 제한된 format을 직접 정의합니다.

```text
block 0: superblock
block 1: inode table
block 2: root directory entries
block 3: /hello.txt data
block 4: /docs directory entries
block 5: /docs/note.txt data
```

superblock에는 magic, format version, block size, block count, inode-table 시작, root inode와 image checksum을 둡니다. 모든 multi-byte integer의 byte order를 명시합니다. inode에는 번호, file/directory kind, byte size와 direct block 하나만 둡니다. directory entry에는 inode 번호, name length와 최대 27-byte UTF-8 name을 둡니다.

Parser는 offset을 계산한 뒤 읽기 전에 범위를 검사합니다.

```text
offset >= 0
field_size >= 0
offset <= image_size
field_size <= image_size - offset
```

`offset + field_size <= image_size`만 사용하면 고정 폭 정수 overflow를 놓칠 수 있습니다. Python 구현도 format의 최대값을 검사해 다른 언어로 옮길 때의 계약을 보존합니다.

Checksum은 checksum field 자체를 0으로 둔 전체 image의 SHA-256으로 정의합니다. Parser와 builder가 같은 잘못된 byte range를 공유하지 않도록 test에서는 독립적으로 digest를 다시 계산합니다.

최소 corruption fixture:

- magic 또는 version 불일치
- block size와 전체 image 길이 불일치
- checksum 불일치
- 중복 inode 번호
- image 밖 block index
- 존재하지 않는 inode를 가리키는 directory entry
- name length 초과 또는 잘못된 UTF-8
- root에서 다시 root로 이어지는 directory cycle

이 저장소는 위 format의 완성 CLI를 제공하지 않습니다. disposable workspace에서 구현하고 결과 image는 Git에 추가하지 않습니다. 핵심 filesystem checkpoint의 page-cache·durability 모델과 binary parser 안전성을 같은 과제로 혼동하지 않기 위해서입니다.

## 4. Device descriptor ring

descriptor ring에는 producer index, consumer index와 ownership generation이 필요합니다.

```text
FREE -> DRIVER_OWNED -> DEVICE_OWNED -> COMPLETED -> FREE
```

불변식:

- 한 descriptor는 동시에 driver와 device 소유가 아닙니다.
- producer가 미완료 descriptor를 덮어쓰지 않습니다.
- ownership을 넘기기 전에 descriptor와 buffer가 장치에 보입니다.
- completion을 관측한 뒤 장치가 쓴 buffer가 CPU에 보입니다.
- reset·timeout·double interrupt에서도 buffer를 정확히 한 번 회수합니다.

ring index가 wrap되므로 단순 `producer < consumer` 비교를 사용하지 않습니다. 단조 증가 sequence와 `sequence % capacity`를 분리하거나 generation bit를 둡니다.

작은 model에서 capacity 2, sequence 0부터 다음 사건을 실행합니다.

1. 두 요청 제출
2. 세 번째 요청의 backpressure
3. 첫 요청 장치 소유권 이전과 완료
4. 사용자 회수 전 index wrap 시도
5. 회수 뒤 slot 재사용
6. 이전 generation의 늦은 completion 거부

## 연결 실습

주소 변환은 [주소 공간과 page fault](03-virtual-memory/01-address-spaces-and-faults.md), MLFQ는 [CPU scheduling](01-boundary-and-execution/03-cpu-scheduling.md), image는 [filesystem과 장애 일관성](04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md), ring은 [device I/O와 DMA](04-storage-and-io/02-device-io-interrupts-and-dma.md)의 완료 기준을 먼저 통과한 뒤 진행합니다.

구현은 `exercises/kernel-model/workspace/`의 core module을 임의로 확장하지 않고 별도 ignored 실험 디렉터리에서 시작합니다. core checker의 8개 checkpoint 이름과 결과 계약을 바꾸지 않습니다.

## 완료 기준

- 네 실습 중 둘을 선택해 정상 입력과 corruption fixture를 각각 두 개 이상 제출합니다.
- parser 또는 state machine이 모든 입력에서 명시한 timeout 안에 종료합니다.
- checksum·oracle·불변식 검사 중 하나 이상이 후보 구현과 독립된 경로로 결과를 판정합니다.
- 특정 CPU, kernel 또는 storage가 있어야만 성립하는 가정은 환경 전제로 분리합니다.

## 실패 조건

- image 길이를 확인하기 전에 offset 위치의 field를 읽습니다.
- builder 결과를 그대로 정답으로 저장해 builder와 parser의 공통 결함을 놓칩니다.
- MLFQ의 queue 수·quantum·boost 규칙 없이 이름만으로 결과를 주장합니다.
- ring index와 ownership generation을 섞어 늦은 completion이 새 요청을 완료하게 합니다.
- timeout 후에도 child process나 generated image가 남습니다.

## 자기 설명

- checksum이 맞더라도 directory graph와 inode 범위를 별도로 검사해야 하는 이유는 무엇입니까?
- page-table 산술의 offset 보존이 permission·present 판정을 대신하지 못하는 이유는 무엇입니까?
- MLFQ가 interactive workload를 우대하면서 긴 CPU-bound 작업을 굶길 수 있는 조건은 무엇입니까?
- descriptor slot 번호가 같아도 이전 generation의 completion을 거부해야 하는 이유는 무엇입니까?
