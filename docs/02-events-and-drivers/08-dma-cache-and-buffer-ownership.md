# DMA, cache와 buffer ownership

Direct Memory Access(DMA)는 CPU 대신 peripheral와 memory 사이의 data를 이동합니다. 성능을 높이지만 CPU, cache, DMA controller와 device가 같은 byte를 서로 다른 시점에 볼 수 있습니다. 핵심은 “주소를 넘겼다”가 아니라 **buffer ownership과 visibility를 명시적으로 전환하는 것**입니다.

## 학습 목표

- DMA request, descriptor, channel, buffer와 completion 상태를 구분합니다.
- CPU→DMA와 DMA→CPU 방향의 cache maintenance를 설명합니다.
- alignment, lifetime, cancellation와 late completion 문제를 설계합니다.
- scatter/gather, circular buffer와 double buffering의 ownership을 추적합니다.

## DMA path

```text
CPU configures descriptor
→ DMA channel armed
→ peripheral request
→ DMA reads/writes memory
→ progress/error/completion
→ interrupt or polling
→ CPU reclaims buffer
```

DMA controller는 CPU와 독립된 bus master일 수 있습니다. CPU가 function을 반환하거나 cache에 값을 썼다는 사실만으로 DMA가 같은 값을 읽는 것은 아닙니다.

## buffer state를 고정합니다

```text
FREE
→ CPU_FILLING
→ READY_FOR_DMA
→ DMA_OWNS
→ DMA_COMPLETE
→ CPU_CONSUMING
→ FREE
```

각 transition에 필요한 작업:

| transition | 필요한 계약 |
|---|---|
| CPU_FILLING → READY_FOR_DMA | length·descriptor 확정, 필요하면 cache flush |
| READY_FOR_DMA → DMA_OWNS | channel submit 성공, CPU write 금지 |
| DMA_OWNS → DMA_COMPLETE | hardware completion/error와 generation 확인 |
| DMA_COMPLETE → CPU_CONSUMING | 필요하면 cache invalidate, actual length 확인 |
| CPU_CONSUMING → FREE | reference 제거, 재사용 가능 표시 |

DMA가 소유하는 동안 stack local buffer가 scope를 벗어나거나 pool에 반환되면 use-after-free와 같습니다.

## 방향에 따라 cache 작업이 다릅니다

### CPU가 쓰고 DMA가 읽음

```text
CPU writes payload
→ data cache flush/clean
→ DMA reads shared memory
```

### DMA가 쓰고 CPU가 읽음

```text
DMA writes shared memory
→ completion
→ CPU invalidates stale cache lines
→ CPU reads payload
```

cache가 없는 MCU에서는 maintenance가 필요 없을 수 있습니다. 그러나 driver가 architecture-independent라고 가정해 생략하면 cache가 있는 target으로 이동할 때 깨집니다.

flush, invalidate와 memory barrier의 정확한 순서는 architecture와 RTOS API를 따릅니다.

## alignment와 cache line 공유

DMA buffer가 cache line 일부만 차지하면 invalidate가 같은 line의 unrelated CPU data까지 버릴 수 있습니다.

대안:

- cache line 크기에 맞춰 정렬
- buffer 크기를 line 단위로 배치
- uncached/coherent region 사용
- DMA 전용 pool
- unrelated mutable data와 같은 line 공유 금지

linker section과 memory attribute도 buffer contract의 일부입니다.

## descriptor도 DMA-visible state입니다

scatter/gather descriptor에는 다음이 있을 수 있습니다.

- source/destination address
- length
- next pointer
- control flags
- completion ownership bit

payload만 flush하고 descriptor를 flush하지 않으면 DMA가 오래된 address/length를 사용할 수 있습니다. completion bit를 CPU와 DMA가 공유한다면 ordering과 volatile/atomic accessor를 명확히 합니다.

## circular buffer와 double buffering

### circular DMA

DMA가 ring을 계속 채우고 CPU가 producer position을 읽습니다.

위험:

- position read 동안 DMA wrap
- CPU가 아직 소비하지 않은 영역 overwrite
- cache line 단위 invalidation이 active write와 겹침
- overrun count 손실

### ping-pong buffer

```text
DMA fills A, CPU consumes B
→ completion
DMA fills B, CPU consumes A
```

각 buffer의 owner를 명시하기 쉽지만 CPU가 deadline 안에 소비하지 못하면 overwrite 또는 drop policy가 필요합니다.

## completion과 data validity를 분리합니다

DMA completion interrupt가 발생해도 다음을 확인할 수 있습니다.

- status/error bit
- transferred length
- FIFO drain 또는 peripheral shift completion
- descriptor generation
- cache visibility
- protocol-level frame integrity

UART TX DMA가 memory를 모두 읽었다고 마지막 bit가 wire를 떠났다는 뜻은 아닐 수 있습니다.

## cancellation와 late completion

```text
request generation 41 시작
→ timeout
→ channel abort 요청
→ generation 42에 buffer 재사용
→ 이전 completion interrupt 도착
```

대응:

- channel이 실제 idle임을 확인
- status와 pending interrupt drain
- generation/token 비교
- buffer quarantine
- peripheral FIFO/reset 상태 확인

abort API 반환만으로 bus transaction과 peripheral state가 끝났다고 가정하지 않습니다.

## DMA channel도 single-owner resource입니다

동일 channel을 여러 driver가 공유하려면 allocator 또는 explicit lease가 필요합니다. driver 내부 mutex로 모든 문제를 해결할 수 없습니다. ISR, callback와 application의 request lifecycle도 연결해야 합니다.

## 실패와 검증

- cache disabled/enabled build 비교
- unaligned buffer
- length 0, 1, cache-line−1, cache-line, cache-line+1
- timeout 직전/직후 completion
- partial transfer와 error interrupt 동시 발생
- ring wrap와 slow consumer
- descriptor chain 중간 failure
- power transition 중 DMA active

실제 board에서는 known pattern, checksum와 logic analyzer를 함께 사용합니다. simulator가 cache coherence를 자동으로 제공하면 결함이 숨을 수 있습니다.

## 실습 연결

[sensor driver 상태 기계](../../exercises/03-sensor-driver-state-machine/README.md)의 선택 확장으로 DMA read path와 buffer pool을 추가합니다.

## 직접 확인할 문제

1. CPU가 payload를 쓴 뒤 flush하지 않으면 DMA가 오래된 값을 읽을 수 있는 경로를 설명해 보세요.
2. DMA write buffer를 invalidate할 때 unrelated data가 같은 cache line에 있으면 어떤 손실이 생깁니까?
3. DMA completion과 UART wire completion을 구분해야 하는 이유를 적어 보세요.
4. timeout 뒤 buffer를 즉시 재사용하지 않도록 어떤 state가 필요합니까?

## 이 장이 보장하지 않는 것

DMA API, coherent interconnect, cache line size, memory region와 descriptor format은 SoC마다 다릅니다. Zephyr의 DMA API도 모든 controller 특성을 완전히 통일하지 않으므로 driver와 SoC 문서를 확인합니다.
