# upstream 기여와 production 경계

가이드의 종료점은 독자적인 RTOS나 완성 제품을 만드는 것이 아닙니다. 낯선 firmware 저장소에서 board·SoC·driver·subsystem·application 경계를 찾고, 작은 결함이나 기능을 재현 가능한 변경으로 제출할 수 있어야 합니다. 임베디드 기여는 code만 맞는 것으로 끝나지 않고 hardware variation, build matrix, binary size, timing과 backward compatibility를 함께 다룹니다.

## 학습 목표

- upstream 저장소에서 변경의 실제 소유 영역을 찾습니다.
- board-specific workaround와 reusable driver/subsystem 변경을 구분합니다.
- bug report와 patch에 필요한 hardware·artifact·trace 근거를 남깁니다.
- API, binding, Kconfig, Devicetree와 release compatibility를 함께 검토합니다.
- 교육용 가이드의 결과와 production qualification의 차이를 명시합니다.

## 처음 보는 firmware 저장소를 읽는 순서

```text
지원 target와 build 명령
→ board/SoC와 configuration
→ application entry와 init graph
→ driver/subsystem public API
→ tests/samples와 supported matrix
→ 최근 issue·change·release note
→ 작은 failure reproduction
```

처음부터 모든 architecture와 board를 읽지 않습니다. 하나의 target에서 변경 경로를 end-to-end로 추적합니다.

## 소유 영역을 찾습니다

대표 계층:

```text
application/sample
subsystem or service
class driver API
specific device driver
bus/controller driver
SoC support
board description
architecture/RTOS kernel
build/configuration/tooling
```

같은 증상도 원인은 다를 수 있습니다.

예: sensor가 동작하지 않음

- board pin/overlay 오류
- bus controller timing
- sensor compatible/binding 오류
- driver identity/probe logic
- application readiness 확인 누락
- power sequencing
- test fixture wiring

가장 아래 계층을 무조건 고치는 것은 맞지 않습니다. 재현과 반증으로 소유자를 찾습니다.

## 좋은 첫 기여

- 문서와 실제 build option 불일치
- sample의 누락된 오류 처리
- 작은 driver state bug
- boundary test 또는 regression fixture
- binding validation 강화
- board description의 검증 가능한 수정
- error code와 cleanup 개선

첫 변경으로 public driver API 전체를 재설계하거나 여러 vendor를 동시에 추상화하지 않습니다.

## bug report의 최소 정보

- repository revision/release
- board·SoC·device part number와 revision
- toolchain/SDK
- exact build command와 configuration
- Devicetree overlay/Kconfig fragment
- expected와 actual behavior
- reproduction frequency
- serial/debug/bus trace
- power·clock·wiring 조건
- 이미 확인한 반증
- minimal sample 또는 patch

사진만으로는 pin, timing와 transaction을 충분히 확인하기 어렵습니다. textual configuration와 analyzer artifact를 함께 제공합니다.

## patch 범위를 고릅니다

### board description 수정

실제 wiring이나 board-level property만 바뀝니다. 다른 board의 공통 driver에 workaround를 넣지 않습니다.

### device driver 수정

같은 component의 모든 supported instance에 적용되는 register semantic과 operation state를 고칩니다. 특정 board delay가 정말 device requirement인지 확인합니다.

### controller/SoC 수정

bus, DMA, interrupt, pinctrl 또는 clock controller의 공통 behavior를 고칩니다. 영향을 받는 device matrix를 넓게 검사합니다.

### subsystem/API 수정

여러 driver와 application의 public contract가 바뀝니다. compatibility, migration, sample와 documentation 비용이 가장 큽니다.

## compatibility를 검토합니다

- public C API와 struct layout
- Kconfig symbol 이름·default·dependency
- Devicetree compatible/property와 binding
- generated macro
- binary/image layout
- persisted data schema
- bootloader/application handoff
- supported compiler/architecture/board

새 optional property를 추가하는 것과 required property 의미를 바꾸는 것은 위험이 다릅니다. 기존 board description이 계속 build되는지 확인합니다.

## 변경 근거를 만듭니다

```text
failure fixture
→ current behavior 확인
→ 최소 patch
→ regression test
→ affected matrix build/run
→ binary size·stack·timing 영향
→ documentation와 release note
```

hardware가 한 대뿐이라도 다음을 분리합니다.

- 자동으로 재현 가능한 host/model test
- 해당 board에서만 확인한 evidence
- 아직 확인하지 못한 architecture/device

## review에서 자주 묻는 질문

- 이 state의 owner는 누구입니까?
- ISR/context에서 이 API를 호출할 수 있습니까?
- timeout·cancel·late completion은 어떻게 됩니까?
- reset/power transition 중 상태는 무엇입니까?
- buffer lifetime과 DMA/cache contract는 무엇입니까?
- image/RAM/stack 비용은 얼마입니까?
- 기존 board와 binding을 깨뜨립니까?
- 실제 hardware evidence가 있습니까?
- simulator가 증명하지 못하는 것은 무엇입니까?

## production으로 넘어갈 때 추가되는 책임

가이드는 production readiness를 인증하지 않습니다. 실제 제품에서는 최소한 다음을 별도로 다룹니다.

### hardware와 제조

- schematic/PCB review
- component tolerance와 errata
- production test와 calibration
- serial identity·provisioning
- manufacturing variation

### 신뢰성과 환경

- voltage/temperature 범위
- brownout·ESD·EMI/EMC
- flash endurance와 retention
- long-duration soak
- watchdog/reset-loop recovery

### 보안

- threat model
- secure boot와 update key lifecycle
- debug interface policy
- device identity와 secret provisioning
- vulnerability response와 patch distribution

### 기능 안전과 규제

- hazard analysis와 safety requirement
- traceability와 independent verification
- coding standard 또는 process evidence
- 인증기관·산업 규격

이 항목은 제품과 산업에 따라 별도 전문가와 절차가 필요합니다.

## 가이드 이후 프로젝트 경로

```text
문서와 상태 모델 완료
→ 공개 RTOS sample build
→ 한 board에서 peripheral application
→ bug reproduction/test contribution
→ small driver/board patch
→ 같은 subsystem에서 반복 기여
→ 하위 driver 또는 board support 소유
```

추천 결과물:

- 한 장짜리 board bring-up 기록
- logic analyzer가 포함된 bus bug report
- register semantic regression test
- power-loss-safe storage model
- update trial/revert fixture
- Devicetree binding·sample 개선
- driver timeout/cancel cleanup patch

## capstone과 연결

[현장 센서 노드](../../capstone/field-sensor-node/README.md)를 완성한 뒤 같은 요구사항을 선택한 RTOS와 board에 일부 구현합니다. 모든 기능을 hardware에 옮기기보다 다음 하나를 end-to-end로 증명하는 것이 좋습니다.

- interrupt-driven sampling과 bounded queue
- power-loss-safe record
- watchdog와 crash evidence
- trial update와 rollback
- sleep/wakeup와 energy measurement

## 완료 체크

다음에 답할 수 있으면 실제 프로젝트 진입 준비가 됐습니다.

- target build와 generated configuration을 재현할 수 있습니까?
- board/SoC/driver/application 중 변경 소유자를 설명할 수 있습니까?
- failure를 작은 fixture로 줄였습니까?
- patch가 보존해야 하는 state와 compatibility를 적었습니까?
- host·simulator·board evidence의 차이를 명시했습니까?
- 확인하지 못한 hardware와 production risk를 숨기지 않았습니까?

## 직접 확인할 문제

1. 특정 board에서만 필요한 delay를 공통 sensor driver에 넣기 전에 무엇을 확인해야 합니까?
2. Devicetree binding required property를 바꾸면 어떤 compatibility 검사가 필요합니까?
3. QEMU에서 통과한 driver patch를 production-ready라고 말할 수 없는 이유를 적어 보세요.
4. 작은 upstream PR에 binary size와 stack 영향이 중요한 이유를 설명해 보세요.

## 이 장이 보장하지 않는 것

특정 upstream 프로젝트의 governance, maintainer 판단과 release 일정은 바뀔 수 있습니다. 기여 전 해당 저장소의 최신 `CONTRIBUTING`, supported platforms, coding style와 issue 정책을 확인합니다.
