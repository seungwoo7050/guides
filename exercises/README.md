# 실습 안내

이 디렉터리의 실습은 완성된 vendor project를 제공하지 않습니다. 각 과제는 문서에서 다룬 상태·실패·검증 계약을 실제 artifact로 바꾸기 위한 **설계 명세**입니다. hardware가 없어도 시작할 수 있으며, 선택한 Zephyr/QEMU/보드 환경으로 단계적으로 옮길 수 있습니다.

## 실습 목록

| 순서 | 실습 | 중심 계약 | 기본 환경 |
|---:|---|---|---|
| 1 | [firmware image와 memory audit](01-image-and-memory-audit/README.md) | ELF·map·linker·startup·budget | 공개 또는 직접 만든 ELF/map |
| 2 | [interrupt event 경로](02-interrupt-event-path/README.md) | ISR·ack·queue·deferred work·overflow | Python model 또는 host C |
| 3 | [sensor driver 상태 기계](03-sensor-driver-state-machine/README.md) | bus/device/operation state, timeout·cancel | fake bus + optional target |
| 4 | [deadline과 priority 검토](04-deadline-and-priority-review/README.md) | response time·blocking·jitter·measurement | worksheet + event trace |
| 5 | [power-loss-safe persistence](05-power-loss-persistence/README.md) | erase/program cut point와 recovery | byte-array flash model |
| 6 | [update와 rollback 모델](06-update-rollback-model/README.md) | candidate·trial·confirm·revert | 제공 state model 확장 |

마지막에는 [현장 센서 노드 capstone](../capstone/field-sensor-node/README.md)으로 상태를 연결합니다.

## 공통 작업 공간

각 과제는 다음 구조를 권장합니다.

```text
workspace/
├── README.md              선택한 target, 범위와 비범위
├── design.md              상태·소유권·불변식
├── evidence/              map, trace, log, 측정 원본
├── fixtures/              결정적 입력과 failure case
├── implementation/        선택 구현
└── report.md              결과, 한계와 다음 단계
```

`workspace/`는 이 가이드의 자동 검사 대상이 아니며 `.gitignore`에 포함됩니다. 별도 저장소에서 작업하거나 경로를 바꿔도 됩니다.

빈 작업 구조는 다음처럼 만들 수 있습니다. 기존 목적지는 덮어쓰지 않습니다.

```sh
./scripts/new-workspace.sh exercises/03-sensor-driver-state-machine
./scripts/new-workspace.sh capstone/field-sensor-node /tmp/field-sensor-workspace
```

## 세 단계 구현 프로필

### A. 문서·상태 모델

필수 단계입니다.

- 상태와 사건을 표 또는 작은 프로그램으로 표현합니다.
- 정상·경계·실패 trace를 고정합니다.
- 완료 판정이 가능한 artifact를 만듭니다.
- 실제 hardware에서만 확인 가능한 주장을 분리합니다.

### B. RTOS 또는 emulator

선택 단계입니다.

- Zephyr `native_sim` 또는 QEMU target
- generated Devicetree/Kconfig/ELF/map 확인
- timer, queue, driver API와 boot path 연결

simulator가 구현하지 않은 peripheral와 timing은 fake 또는 별도 target test로 남깁니다.

### C. 실제 보드

선택 단계입니다.

- 정확한 board/SoC/device revision
- toolchain과 build configuration
- serial/debug/bus analyzer evidence
- power cycle과 recovery path
- 측정 환경과 오차

실기기에서 한 번 성공한 결과를 모든 보드의 보장으로 확대하지 않습니다.

## 모든 실습의 공통 완료 조건

1. **초기 상태**가 재현 가능합니다.
2. **입력 사건**과 발생 context가 명시돼 있습니다.
3. **상태 소유자**와 buffer/resource lifetime을 설명합니다.
4. **정상·경계·실패 사례**가 각각 있습니다.
5. **독립된 검사**가 결과를 판정합니다.
6. **reset, timeout 또는 power loss 뒤 복구 상태**를 기록합니다.
7. **관찰 도구의 한계**와 실제 보드에서 미검증인 주장을 구분합니다.
8. 구현하지 않은 범위를 숨기지 않습니다.

## reference를 대신하는 검토 방식

이 실습에는 전체 정답이 없을 수 있습니다. 다음 근거로 설계를 검토합니다.

- 문서의 불변식과 모순되지 않는가?
- 실패 주입 뒤 허용되지 않은 중간 상태가 남지 않는가?
- 검사기가 source 문구가 아니라 결과 상태를 판정하는가?
- timeout/cancel 뒤 늦은 completion을 처리하는가?
- build, image, configuration와 evidence를 다시 연결할 수 있는가?
- simulator와 실제 hardware의 보장 범위를 구분하는가?

## 제출 단위

한 실습의 좋은 결과물은 큰 codebase보다 다음을 포함합니다.

```text
작은 상태 기계 또는 구현
+ failure fixture
+ 자동 검사
+ raw evidence
+ 설계 설명
+ 검증 한계
```
