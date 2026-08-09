# firmware 변경 검토표

모든 항목을 모든 patch에 적용하지 않습니다. 변경한 상태와 실패 경로에 해당하는 항목을 선택하고, 확인하지 않은 항목은 명시합니다.

## 범위와 재현

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
- [ ] 검사기는 source 모양이 아니라 결과 state를 판정합니다.
- [ ] virtual time/event injection으로 race boundary를 고정합니다.
- [ ] simulator가 빠뜨리는 hardware behavior를 기록합니다.
- [ ] 실제 보드 결과에는 raw trace와 환경이 있습니다.
- [ ] binary/RAM/stack/timing 영향이 있습니다.
- [ ] cleanup 뒤 test가 known state를 복원합니다.

## 기여와 운영

- [ ] 문서와 sample/test를 함께 갱신했습니다.
- [ ] release note가 필요한 compatibility 변화인지 검토했습니다.
- [ ] exact ELF/map/configuration을 보존합니다.
- [ ] 로그에 secret·개인정보·unbounded payload가 없습니다.
- [ ] 현장 telemetry가 build ID와 연결됩니다.
- [ ] 실제 production/security/safety 비보장 범위를 명시합니다.
