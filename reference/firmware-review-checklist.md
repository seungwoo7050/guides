# firmware 변경 검토표

모든 항목을 모든 patch에 적용하지 않습니다. 변경한 상태와 실패 경로에 해당하는 항목을 선택하고, 확인하지 않은 항목은 명시합니다.

## 범위와 재현

- [ ] main의 해당 `owns`와 `exit_capabilities`를 [계약 추적표](../docs/00-roadmap.md#main-계약-추적표)에서 찾아 정확한 개념 문서, 실습 fixture, capstone scenario와 evidence까지 연결했습니다.
- [ ] 문제와 target/board/revision이 명확합니다.
- [ ] exact build command, configuration와 toolchain을 남겼습니다.
- [ ] failure를 작은 fixture로 재현합니다.
- [ ] 변경 소유 계층(board/SoC/driver/subsystem/application)을 설명합니다.
- [ ] 비소유 영역과 미확인 hardware를 기록합니다.

## API와 상태

- [ ] public operation의 valid state가 있습니다.
- [ ] 성공, terminal failure와 `UNKNOWN`을 구분합니다.
- [ ] timeout/cancel 뒤 실제 hardware 상태를 설명합니다.
- [ ] stale callback/interrupt/completion을 구분할 generation이 있습니다.
- [ ] error code가 원인 분류와 recovery에 충분합니다.
- [ ] partial success 뒤 상태가 문서화돼 있습니다.

## context와 concurrency

- [ ] 호출 가능 context(thread/ISR/boot/fault)가 명확합니다.
- [ ] ISR work가 bounded입니다.
- [ ] blocking, allocation와 formatting이 허용 context에만 있습니다.
- [ ] shared state의 lock/atomic/interrupt policy가 있습니다.
- [ ] callback lifetime와 reentrancy를 검토했습니다.
- [ ] lock order와 priority inversion을 검토했습니다.
- [ ] shutdown/suspend 중 in-flight operation을 처리합니다.

## memory와 DMA

- [ ] buffer owner와 lifetime이 transition별로 명확합니다.
- [ ] length, alignment와 integer overflow를 검사합니다.
- [ ] stack 사용 증가를 검토했습니다.
- [ ] allocation/pool exhaustion 경로가 있습니다.
- [ ] DMA direction과 cache maintenance를 확인했습니다.
- [ ] descriptor와 payload visibility를 함께 검토했습니다.
- [ ] timeout/abort 뒤 buffer 재사용 시점을 확인했습니다.

## register와 peripheral

- [ ] official manual/errata revision을 기록했습니다.
- [ ] access width와 alignment가 맞습니다.
- [ ] reserved bit와 W1C/read-to-clear 의미를 보존합니다.
- [ ] read-modify-write가 안전한지 확인했습니다.
- [ ] ready/busy와 data validity를 분리합니다.
- [ ] reset/default state를 모든 관련 reset에서 확인합니다.
- [ ] clock/pin/power dependency가 ready입니다.

## time와 scheduling

- [ ] timeout clock와 unit이 명확합니다.
- [ ] wrap-safe comparison을 사용합니다.
- [ ] deadline 시작/종료 사건이 명확합니다.
- [ ] queueing, interference와 blocking을 포함합니다.
- [ ] 평균/측정 최대를 worst-case guarantee로 표현하지 않습니다.
- [ ] clock/power transition 뒤 conversion을 갱신합니다.

## persistence와 update

- [ ] write/erase cut point가 있습니다.
- [ ] record/image에 version, length, integrity가 있습니다.
- [ ] incomplete state를 valid로 사용하지 않습니다.
- [ ] old complete state를 너무 일찍 제거하지 않습니다.
- [ ] schema migration와 downgrade/rollback를 검토합니다.
- [ ] trial/confirm/revert state가 durable합니다.
- [ ] reset loop와 recovery mode가 있습니다.

## power와 recovery

- [ ] sleep entry precondition이 있습니다.
- [ ] wake source와 pending event race를 검토했습니다.
- [ ] wake 뒤 clock/peripheral state를 복원합니다.
- [ ] watchdog feed가 모든 critical progress를 반영합니다.
- [ ] reset cause와 crash evidence를 덮기 전에 보존합니다.
- [ ] recovery 실패가 무한 boot/reset loop를 만들지 않습니다.

## configuration와 portability

- [ ] hardware fact는 Devicetree/board description에 있습니다.
- [ ] software policy는 Kconfig/application config에 있습니다.
- [ ] final generated tree와 `.config`를 확인했습니다.
- [ ] public API/binding/Kconfig compatibility를 검토했습니다.
- [ ] board-specific workaround를 공통 driver에 넣지 않았습니다.
- [ ] build matrix에서 affected target을 검사했습니다.

## verification

- [ ] 정상·경계·실패 fixture가 있습니다.
- [ ] 변경한 실습 또는 capstone에 reference, 실행 가능한 starter와 대표 known-wrong이 있습니다.
- [ ] 공개 checker가 `--submission PATH [--json]`을 지원합니다.
- [ ] reference `0`, starter·모든 known-wrong `1`, 존재하지 않는 submission `2`의 종료 코드 polarity를 확인했습니다.
- [ ] 검사기는 source 모양이 아니라 결과 state를 판정합니다.
- [ ] virtual time/event injection으로 race boundary를 고정합니다.
- [ ] simulator가 빠뜨리는 hardware behavior를 기록합니다.
- [ ] 실제 보드 결과에는 raw trace와 환경이 있습니다.
- [ ] binary/RAM/stack/timing 영향이 있습니다.
- [ ] cleanup 뒤 test가 known state를 복원합니다.
- [ ] 6개 host 실습과 capstone 12개 필수 시나리오를 모두 실행했으며 선택 Zephyr/board slice를 대체재로 세지 않았습니다.
- [ ] 자동 결과와 사람 판단을 분리했고 raw evidence 검토 전 상태는 `human_review: NOT_TESTED`(미검증)이며 자동 PASS 집계 밖입니다.

## 안전과 복구

- [ ] host 검사에 network, root 권한, 유료 cloud 자원이나 실제 서비스 변경이 필요하지 않습니다.
- [ ] checker/helper가 submission, 학습자 workspace나 raw evidence를 덮어쓰거나 삭제하지 않습니다.
- [ ] board의 전압, pin direction, current limit, 전원 source와 위험한 actuator를 확인하고 필요한 격리를 했습니다.
- [ ] flash/update/power-cut 전에 factory 또는 last-known-good image와 calibration·identity를 백업했습니다.
- [ ] probe 또는 recovery mode로 복구하는 절차를 시험 전에 확인했습니다.
- [ ] 임시 wiring, 전원, probe, image와 설정을 정리하고 known state로 복원했습니다.
- [ ] 복구하지 못한 상태와 실행하지 못한 필수 검사를 성공으로 표시하지 않았습니다.

## 기여와 운영

- [ ] version 주장은 [공식 자료](sources.md)에 release/revision, URL과 확인일 2026-08-10을 기록했습니다.
- [ ] Zephyr profile이라면 4.4.0, Python 3.12+, C17, SDK 1.0.1을 실제 도구 출력과 manifest로 확인했고 host Python 3.10+ 계약과 구분했습니다.
- [ ] 문서와 sample/test를 함께 갱신했습니다.
- [ ] release note가 필요한 compatibility 변화인지 검토했습니다.
- [ ] exact ELF/map/configuration을 보존합니다.
- [ ] 로그에 secret·개인정보·unbounded payload가 없습니다.
- [ ] 현장 telemetry가 build ID와 연결됩니다.
- [ ] 실제 production/security/safety 비보장 범위를 명시합니다.
- [ ] 문서에는 [CC BY 4.0](../LICENSES/CC-BY-4.0.txt), 실행 코드에는 [MIT](../LICENSES/MIT.txt)를 적용하고 외부 자료의 저작자·원본·라이선스·변경 표시를 보존했습니다.
