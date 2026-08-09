# 관찰 예제

이 디렉터리는 실제 MCU, interrupt controller, flash 또는 bootloader를 대체하지 않는 작은 결정론적 상태 모델을 제공합니다. 문서에 등장하는 상태·세대·실패·복구를 hardware 없이 먼저 관찰하기 위한 도구입니다.

| 예제 | 관찰할 계약 |
|---|---|
| [interrupt event model](interrupt-event-model/README.md) | enable generation, pending/ack, bounded queue, overflow, stale event |
| [update state model](update-state-model/README.md) | candidate, trial, confirmation, reset attempts, revert와 recovery |

전체 예제 검사는 저장소 루트에서 실행합니다.

```sh
make examples-check
```

개별 fixture:

```sh
python3 examples/interrupt-event-model/model.py \
  examples/interrupt-event-model/fixtures/normal.json --check

python3 examples/update-state-model/model.py \
  examples/update-state-model/fixtures/normal-confirm.json --check
```

모델이 통과해도 다음은 증명하지 않습니다.

- 실제 interrupt priority와 latency
- peripheral register semantic
- CPU/DMA cache coherence
- flash program/erase atomicity
- bootloader image copy/swap
- cryptographic validation
- 실제 board의 power와 electrical behavior

모델의 상태를 선택 RTOS·QEMU·보드로 옮길 때 어떤 가정이 사라지고 어떤 새로운 상태가 생겼는지 기록합니다.
