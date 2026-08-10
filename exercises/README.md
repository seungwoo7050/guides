# 실습 안내

이 디렉터리는 문서에서 다룬 상태·실패·검증 계약을 실행 가능한 artifact로 바꾸는 6개 필수 host 실습을 제공합니다. 각 실습에는 starter, 비교 reference, 정상·경계·실패 fixture와 공개 행동 checker가 있습니다. 완성된 vendor project는 아니며 hardware가 없어도 실행할 수 있습니다. Zephyr/QEMU/보드 경로는 host 계약을 통과한 뒤 선택적으로 옮기는 별도 profile입니다.

## 실습 목록

| 순서 | 실습 | 중심 계약 | 기본 환경 |
|---:|---|---|---|
| 1 | [firmware image와 memory audit](01-image-and-memory-audit/README.md) | ELF·map·linker·startup·budget | manifest + JSON audit |
| 2 | [interrupt event 경로](02-interrupt-event-path/README.md) | ISR·ack·queue·deferred work·overflow | 결정적 Python event model |
| 3 | [sensor driver 상태 기계](03-sensor-driver-state-machine/README.md) | bus/device/operation state, timeout·cancel | fake bus + generated configuration |
| 4 | [deadline과 priority 검토](04-deadline-and-priority-review/README.md) | response time·blocking·jitter·measurement | response-time/queue 분석 model |
| 5 | [power-loss-safe persistence](05-power-loss-persistence/README.md) | erase/program cut point와 recovery | NOR byte-array model |
| 6 | [update와 rollback 모델](06-update-rollback-model/README.md) | candidate·trial·confirm·revert | durable boot metadata model |

여섯 실습을 모두 통과한 뒤 [현장 센서 노드 capstone](../capstone/field-sensor-node/README.md)의 12개 필수 시나리오로 상태를 연결합니다. 선택 경로를 수행해도 실습이나 capstone을 생략할 수 없습니다.

## 공개 checker 계약

저장소 루트에서 reference를 검사하는 명령은 다음과 같습니다.

```sh
python3 exercises/01-image-and-memory-audit/check.py --submission exercises/01-image-and-memory-audit/reference/submission.json --json
python3 exercises/02-interrupt-event-path/check.py --submission exercises/02-interrupt-event-path/reference --json
python3 exercises/03-sensor-driver-state-machine/check.py --submission exercises/03-sensor-driver-state-machine/reference --json
python3 exercises/04-deadline-and-priority-review/check.py --submission exercises/04-deadline-and-priority-review/reference --json
python3 exercises/05-power-loss-persistence/check.py --submission exercises/05-power-loss-persistence/reference --json
python3 exercises/06-update-rollback-model/check.py --submission exercises/06-update-rollback-model/reference --json
python3 capstone/field-sensor-node/check.py --submission capstone/field-sensor-node/reference --json
```

모든 checker의 공통 CLI는 `--submission PATH [--json]`입니다.

| 종료 코드 | 의미 | 제공 artifact 기대값 |
|---:|---|---|
| `0` | 공개 행동과 불변식 통과 | reference |
| `1` | 실행 가능한 submission의 의미 실패 | starter, 모든 known-wrong |
| `2` | 인터페이스 불일치 또는 누락·손상 입력 | 존재하지 않는 submission |

`--json`은 같은 판정을 기계가 읽을 수 있는 형태로 출력할 뿐 종료 코드를 바꾸지 않습니다. checker는 source 문구나 reference와의 텍스트 동일성을 요구하지 않고 fixture 결과, bounded resource, durable state 같은 공개 계약을 관찰합니다. `make exercises-check`는 6개 실습의 reference/starter/known-wrong/missing polarity를, `make capstone-check`는 capstone polarity와 12개 시나리오를 한꺼번에 검사합니다.

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

## 자동 판정과 사람 검토

reference는 공개 계약을 만족하는 비교 구현이지 유일한 설계나 production 정답이 아닙니다. checker가 통과해도 아래 판단은 사람이 [evidence 템플릿](../reference/evidence-template.md)과 [firmware 검토표](../reference/firmware-review-checklist.md)로 확인합니다.

- 문서의 불변식과 모순되지 않는가?
- 실패 주입 뒤 허용되지 않은 중간 상태가 남지 않는가?
- 검사기가 source 문구가 아니라 결과 상태를 판정하는가?
- timeout/cancel 뒤 늦은 completion을 처리하는가?
- build, image, configuration와 evidence를 다시 연결할 수 있는가?
- simulator와 실제 hardware의 보장 범위를 구분하는가?

사람이 raw evidence와 설명을 실제로 읽기 전에는 제출 상태를 정확히 `human_review: NOT_TESTED`(미검증)로 두고 자동 PASS 집계에서 제외합니다. 자동 검사 성공을 교육적 완료, 실제 timing·electrical·power 보장, 보안·안전 인증으로 표현하지 않습니다.

## 안전, cleanup과 복구

- host 실습은 저장소 source를 수정하지 않는 임시 작업 공간에서 실행하고 network, root 권한, cloud 자원이나 실제 서비스 배포를 요구하지 않습니다.
- checker 입력으로 학습자 경로를 받더라도 예고 없이 덮어쓰거나 삭제하지 않습니다. `workspace/`와 raw evidence는 사용자가 직접 관리합니다.
- 실제 board를 선택하면 전압·pin direction·current limit, debug access, flash layout와 복구 가능한 programmer 경로를 먼저 확인합니다. 위험한 actuator와 외부 전원은 격리합니다.
- power-cut/update 실험 전에는 factory image, calibration·identity 자료와 last-known-good slot의 복구 절차를 기록합니다. 시험 뒤에는 전원, probe, 임시 wiring와 test image를 정리하고 알려진 정상 상태로 복원합니다.
- 회복하지 못한 board, 필수 검사를 실행하지 못한 환경 또는 잃어버린 raw evidence를 통과로 기록하지 않습니다.

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
