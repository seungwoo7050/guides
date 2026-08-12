# 주소 변환과 TLB

프로그램이 생성한 주소는 프로세서가 최종적으로 캐시와 메모리에 전달하는 물리 주소와 같지 않을 수 있습니다. 주소 변환 경로는 가상 주소를 페이지 번호와 오프셋으로 나누고, 페이지 테이블 항목에서 물리 프레임 번호와 접근 권한을 얻으며, 최근 변환 결과를 TLB에 저장합니다.

이 장은 **주소 변환 하드웨어와 ISA에 보이는 계약**을 다룹니다. 운영체제가 페이지를 언제 배정·회수·교체하는지, copy-on-write와 파일 매핑을 어떤 정책으로 관리하는지는 운영체제 가이드의 범위입니다.

## 학습 목표

- 가상 주소를 VPN과 offset으로 나누고 TLB·page table 상태를 추적합니다.
- TLB miss, protection fault와 page fault를 서로 다른 사건으로 구분합니다.

## 선행 개념

주소 비트, cache lookup과 ISA 예외의 기본 흐름을 알아야 합니다.

## 가상 주소와 물리 주소를 구분합니다

서로 다른 주소 공간은 같은 가상 주소를 서로 다른 물리 프레임에 연결할 수 있습니다.

```text
address space A: virtual 0x4000 → physical frame 12
address space B: virtual 0x4000 → physical frame 91
```

프로세서가 메모리 접근을 완료하려면 다음 두 질문에 답해야 합니다.

1. 이 가상 주소가 어느 물리 주소에 대응합니까?
2. 현재 권한 수준과 접근 종류가 그 주소를 읽거나 쓰거나 실행할 수 있습니까?

주소 숫자만 같다고 같은 바이트를 가리키는 것은 아닙니다. 주소 공간 식별자, 페이지 테이블 기준 레지스터와 권한 상태도 변환의 입력입니다.

## 페이지 번호와 오프셋으로 나눕니다

페이지 크기가 `2^p`바이트라면 가상 주소의 하위 `p`비트가 페이지 오프셋입니다.

```text
virtual address
| virtual page number | page offset |
```

4KiB 페이지에서는 오프셋이 12비트입니다. 주소 변환은 페이지 번호를 물리 프레임 번호로 바꾸고 오프셋은 그대로 유지합니다.

```text
virtual address 0x12345
VPN    = 0x12
offset = 0x345
PFN    = 0x2a
physical address = 0x2a345
```

먼저 페이지 크기와 주소 폭을 고정하지 않으면 VPN, 오프셋과 페이지 테이블 인덱스를 계산할 수 없습니다.

## 다단계 페이지 테이블은 주소 비트를 단계별 인덱스로 사용합니다

큰 가상 주소 공간의 모든 페이지 항목을 하나의 평평한 배열로 만들면 표 자체가 매우 커집니다. 다단계 구조는 VPN 비트를 여러 인덱스로 나누고 실제로 필요한 하위 표만 연결합니다.

```text
VPN
| level 1 index | level 2 index | level 3 index |
```

일반적인 페이지 테이블 순회는 다음 상태를 거칩니다.

```text
root table address
→ level 1 entry
→ next table address
→ level 2 entry
→ ...
→ leaf PTE
→ physical frame number와 permission
```

각 단계는 메모리 접근을 요구할 수 있습니다. 구현에 따라 전용 page-walk cache가 중간 항목을 저장할 수 있지만, 특정 단계 수나 캐시 구조를 ISA 전체의 공통 규칙으로 가정하면 안 됩니다.

## PTE는 변환 결과와 접근 계약을 함께 담습니다

대표적인 leaf page-table entry에는 다음 정보가 포함될 수 있습니다.

- 항목의 유효 여부
- 물리 프레임 번호
- read, write, execute 권한
- user와 supervisor 접근 권한
- accessed 또는 referenced 상태
- dirty 또는 modified 상태
- memory type과 cacheability
- 큰 페이지 여부

정확한 비트 배치와 갱신 주체는 ISA의 권한 명세에 따라 다릅니다. 어떤 아키텍처는 accessed·dirty 상태를 하드웨어가 기록하고, 다른 아키텍처는 예외를 통해 소프트웨어가 보조할 수 있습니다.

PTE에서 물리 프레임 번호를 얻었다고 접근이 성공한 것은 아닙니다. 권한 검사를 통과한 뒤에야 해당 물리 주소로 load, store 또는 instruction fetch를 진행할 수 있습니다.

## TLB는 최근 변환을 저장합니다

Translation Lookaside Buffer는 최근의 `VPN → PFN` 결과와 권한을 저장합니다.

```text
virtual address
→ TLB lookup
   ├─ hit: PFN과 permission 사용
   └─ miss: page table walk 후 TLB fill
```

TLB 적중과 데이터 캐시 적중은 서로 다른 사건입니다.

```text
TLB hit + cache miss
TLB miss + cache hit
TLB miss + cache miss
```

첫 번째는 주소 변환은 빠르지만 데이터가 캐시에 없고, 두 번째는 변환을 다시 찾지만 물리 주소가 정해진 뒤 데이터는 캐시에 있을 수 있습니다. 성능 계수기나 모델에서 두 실패를 하나의 “메모리 실패”로 합치면 원인을 잃습니다.

## TLB 실패와 변환 예외를 구분합니다

### TLB 실패

TLB에 일치하는 항목이 없지만 페이지 테이블에는 유효한 leaf PTE가 있을 수 있습니다. 순회를 완료하고 TLB를 채운 뒤 원래 접근을 계속할 수 있습니다.

### 변환 또는 권한 예외

페이지 테이블 순회가 유효한 변환을 만들지 못하거나 접근 권한이 맞지 않으면 ISA가 정한 예외가 발생합니다. 예외 처리기는 매핑을 새로 만들거나, 권한을 바꾸거나, 프로세스에 실패를 전달할 수 있습니다.

여기서 구조가 보장하는 것은 **예외 원인과 재시작 가능한 상태를 전달하는 계약**입니다. demand-zero, copy-on-write, storage I/O, stack growth 같은 처리 정책은 운영체제가 결정합니다.

“TLB miss는 곧 page fault입니다” 또는 “page fault는 항상 디스크 I/O입니다”라는 설명은 모두 부정확합니다.

## 주소 공간 식별자는 전환 비용을 줄입니다

TLB 항목에 ASID 또는 PCID 같은 주소 공간 식별자를 붙이면 서로 다른 주소 공간의 같은 VPN을 구분할 수 있습니다.

```text
(ASID A, VPN 0x4) → PFN 12
(ASID B, VPN 0x4) → PFN 91
```

식별자가 없다면 주소 공간을 전환할 때 이전 변환을 광범위하게 비워야 할 수 있습니다. 식별자가 있어도 재사용, 권한 변경과 전역 매핑에 대한 무효화 규칙은 필요합니다.

## 매핑을 바꾸면 오래된 변환을 제거해야 합니다

페이지 테이블의 PFN이나 권한을 바꿔도 TLB에 이전 항목이 남아 있으면 프로세서는 오래된 변환을 계속 사용할 수 있습니다.

```text
PTE update
→ ISA가 요구하는 순서 보장
→ TLB invalidation
→ 새 translation 사용
```

멀티코어에서는 같은 주소 공간을 실행하는 다른 코어도 오래된 항목을 가질 수 있습니다. 아키텍처는 로컬·원격 무효화를 수행할 수단과 필요한 순서 규칙을 제공하고, 운영체제는 어떤 코어에 어떤 범위의 shootdown을 보낼지 결정합니다.

무효화는 단순한 성능 최적화가 아닙니다. write 권한을 제거했는데 오래된 writable 항목이 남거나, 해제한 프레임의 이전 변환이 남으면 격리와 메모리 안전이 깨질 수 있습니다.

## 큰 페이지는 TLB coverage를 늘립니다

TLB 항목 수가 같을 때 페이지가 클수록 한 번에 덮는 주소 범위가 커집니다.

```text
TLB coverage = entry count × page size
```

예를 들어 64개 항목이 4KiB 페이지를 가리키면 256KiB를, 2MiB 페이지를 가리키면 128MiB를 덮을 수 있습니다.

구조적 장점은 다음과 같습니다.

- TLB 실패 감소 가능성
- 페이지 테이블 leaf 항목 수 감소
- 큰 연속 작업 집합의 변환 비용 감소

운영체제는 이 장점과 물리 메모리 배치, 단편화, copy-on-write와 회수 비용을 함께 고려합니다. 이 장에서는 TLB coverage와 주소 비트 변화까지만 성능 모델에 포함합니다.

## 캐시 조회와 주소 변환은 겹칠 수 있습니다

가장 단순한 순서는 다음과 같습니다.

```text
virtual address → translation → physical address → cache lookup
```

L1 지연을 줄이기 위해 페이지 오프셋으로 set을 먼저 선택하고 TLB 결과의 물리 tag와 캐시 tag를 함께 비교하는 virtually indexed, physically tagged 구조를 사용할 수 있습니다.

이때 캐시 인덱스 비트가 페이지 오프셋 범위를 넘으면 서로 다른 가상 주소가 같은 물리 주소를 가리키는 alias 처리가 복잡해집니다. 실제 set 수, way 수와 page size를 사용해 index bit 범위를 계산해야 하며 모든 프로세서가 같은 구조를 사용한다고 가정하면 안 됩니다.

## 운영체제 정책과의 경계

다음은 이 장에서 결과만 입력으로 받는 운영체제 정책입니다.

- 주소 공간의 영역을 언제 생성하거나 해제하는지
- fault에서 물리 프레임을 새로 배정할지
- file-backed page를 언제 읽고 쓸지
- copy-on-write를 언제 해제할지
- memory pressure에서 어떤 페이지를 회수할지
- swap과 page replacement를 어떻게 수행할지

`processor-model`의 `MAP`과 `UNMAP` 명령은 이러한 정책을 구현하지 않습니다. 외부에서 결정된 매핑 변경을 입력으로 받아 TLB, 권한과 물리 주소 조립이 올바른지만 검사합니다.

## 직접 구현하기

`exercises/processor-model/workspace/processor_model/vm.py`에서 다음 상태 전이를 구현합니다.

- LRU TLB lookup과 fill
- page-table walk count
- read, write, execute permission
- `MAP`·`UNMAP` 뒤 관련 TLB entry 무효화
- PFN과 page offset을 사용한 physical address 조립

```sh
cd exercises/processor-model
make stage-07 EXERCISE_IMPL=workspace
```

처음에는 TLB 없이 페이지 테이블 순회와 권한 검사만 구현합니다. 그다음 entry 수를 `0 → 1 → 2`로 늘리며 hit, eviction과 stale-entry 제거를 비교하면 상태 수명을 분리하기 쉽습니다.

reference source를 열지 않고 완성 결과만 black-box oracle로 관찰하려면 저장소 루트에서 다음을 실행합니다.

```sh
python3 exercises/processor-model/reference/processor-model.py vm \
  exercises/processor-model/fixtures/vm/config.json \
  exercises/processor-model/fixtures/vm/trace.txt
```

## 주소 변환 문제를 푸는 순서

1. 가상 주소 폭과 페이지 크기를 적습니다.
2. 오프셋 비트 수와 VPN을 계산합니다.
3. VPN을 페이지 테이블 단계별 인덱스로 나눕니다.
4. 주소 공간 식별자와 TLB hit 여부를 확인합니다.
5. TLB miss면 page-table walk와 leaf PTE를 추적합니다.
6. 접근 종류와 PTE 권한을 비교합니다.
7. PFN과 오프셋을 합쳐 물리 주소를 만듭니다.
8. 매핑 변경 뒤 필요한 무효화 범위를 확인합니다.
9. 주소 변환 뒤 데이터·명령 캐시 접근을 별도로 판단합니다.

## 직접 확인할 문제

1. 48비트 가상 주소와 4KiB 페이지에서 VPN과 오프셋의 비트 수를 계산해 보세요.
2. TLB에 항목이 있어도 permission exception이 발생할 수 있는 이유를 설명해 보세요.
3. 페이지 테이블을 수정한 뒤 TLB invalidation을 생략했을 때 발생할 수 있는 보안 문제를 적어 보세요.
4. 64-entry TLB에서 4KiB와 2MiB 페이지의 coverage를 각각 계산해 보세요.
5. TLB miss, page-table walk와 운영체제의 demand paging을 서로 다른 상태로 구분해 보세요.

## 연결 실습

[`processor-model` stage-07](../../exercises/processor-model/README.md)에서 권한 검사와 TLB invalidation을 구현합니다.

## 완료 기준

- page size에서 offset 비트와 VPN을 계산할 수 있습니다.
- mapping 변경 뒤 stale TLB entry를 제거해야 하는 이유를 설명할 수 있습니다.
- `make stage-07 EXERCISE_IMPL=workspace`가 통과합니다.
