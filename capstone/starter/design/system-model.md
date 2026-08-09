# System model

> 이 문서의 `TODO`를 구현 전에 채웁니다.

## Node와 process

- node 집합: `TODO`
- 한 node의 crash가 보존하는 durable state: `TODO`
- restart가 초기화하는 volatile state: `TODO`

## Network

- delivery 보장: `TODO`
- 허용 fault: `TODO`
- Byzantine message 여부: `TODO`

partition 중 delivery attempt는 소비되어 `PARTITION_DROPPED`가 됩니다. heal은 이후 전송에만 적용하며, 오래된 packet 도착은 partition 전에 별도 delivery를 delay해 모델링합니다.

## Time

- clock 종류: virtual monotonic time
- election 진행에 필요한 bound와 fairness: `TODO`
- safety가 wall clock 정확성에 의존하는지: `TODO`

## Storage

- core의 persist 원자성: `TODO`
- persist 완료와 message send의 순서: `TODO`
- corruption 처리: `TODO`

atomic save fault는 `fail_next_save("before" | "after")`로 재현합니다. 실제 torn write와 filesystem flush 의미는 이 in-memory profile의 비보장 범위입니다.
