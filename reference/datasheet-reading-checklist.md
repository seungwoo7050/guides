# datasheet와 reference manual 읽기 점검표

register 이름을 검색해 code부터 작성하지 않습니다. 다음 순서로 hardware contract를 복원합니다.

## 1. 대상 식별

- [ ] 제조사와 exact part number
- [ ] silicon/device revision
- [ ] package와 pin variant
- [ ] board revision
- [ ] datasheet/reference manual 문서 번호와 revision/date
- [ ] 최신 errata와 application note
- [ ] 실제 chip marking과 build target 일치

같은 family 이름이어도 peripheral instance, memory, package와 errata가 다를 수 있습니다.

## 2. 전원·clock·reset

- [ ] supply voltage와 power domain
- [ ] power-up/reset timing
- [ ] brownout 조건
- [ ] reset source와 reset되는 register/domain
- [ ] default clock source와 frequency
- [ ] oscillator/PLL startup와 lock
- [ ] peripheral clock gate/reset dependency
- [ ] sleep/wakeup 동안 유지되는 상태

reset value는 모든 reset 종류에서 같다고 가정하지 않습니다.

## 3. memory와 address

- [ ] memory map와 alias
- [ ] register block base/size
- [ ] access width와 alignment
- [ ] endianness
- [ ] cacheable/coherent attribute
- [ ] secure/privileged access 조건
- [ ] reserved region
- [ ] flash erase/program unit와 execution restriction

## 4. register 표

각 사용 register에 대해:

- [ ] offset와 width
- [ ] reset value
- [ ] read/write permission
- [ ] write-one-to-clear/set/toggle
- [ ] read-to-clear 또는 latch
- [ ] self-clearing command
- [ ] reserved bit write rule
- [ ] atomic set/clear alias
- [ ] update order와 synchronization
- [ ] 관련 errata

bit field 표만 보지 말고 register 주변의 operation sequence 설명을 읽습니다.

## 5. operation sequence

- [ ] enable 전 prerequisite
- [ ] configuration 가능한 state
- [ ] command acceptance 조건
- [ ] busy/ready/done 의미
- [ ] data validity 시점
- [ ] interrupt status와 clear 순서
- [ ] error status와 recovery
- [ ] abort/reset procedure
- [ ] disable/suspend sequence
- [ ] timeout upper/lower bound

“write command → delay → read”에서 delay의 근거와 ready indicator를 확인합니다.

## 6. interrupt

- [ ] source와 status bit
- [ ] level/edge/pulse behavior
- [ ] mask/enable/pending의 위치
- [ ] clear/acknowledge semantic
- [ ] 여러 source 동시 발생
- [ ] interrupt가 disabled일 때 event 보존
- [ ] reset/suspend 뒤 pending 상태
- [ ] priority/route와 shared line

## 7. DMA와 buffer

- [ ] DMA request source
- [ ] transfer direction/width/alignment
- [ ] max length와 boundary
- [ ] FIFO와 burst
- [ ] descriptor visibility
- [ ] completion vs peripheral wire completion
- [ ] abort 결과
- [ ] cache maintenance/coherency
- [ ] active buffer lifetime

## 8. serial bus/device

### I2C류

- [ ] address format
- [ ] ACK/NACK 의미
- [ ] repeated-start
- [ ] clock stretching
- [ ] maximum bus speed
- [ ] transaction framing
- [ ] bus recovery 조건

### SPI류

- [ ] mode/CPOL/CPHA
- [ ] bit order와 word size
- [ ] chip-select setup/hold
- [ ] command/address/dummy/data phase
- [ ] maximum clock
- [ ] multi-byte atomicity

## 9. timing·electrical

- [ ] min/typ/max를 구분
- [ ] voltage/temperature 조건
- [ ] clock tolerance
- [ ] setup/hold
- [ ] startup/conversion time
- [ ] output drive와 pull
- [ ] pin multiplexing conflict
- [ ] 외부 component 요구

software test만으로 electrical compliance를 증명하지 않습니다.

## 10. driver contract로 옮기기

- [ ] public operation과 hardware sequence 대응
- [ ] invalid argument는 hardware access 전 거부
- [ ] timeout와 cancellation
- [ ] raw status → semantic error mapping
- [ ] state owner와 lock/context
- [ ] reset/recovery 후 configuration 상태
- [ ] suspend/resume
- [ ] logging에 민감하거나 unbounded data 없음
- [ ] register access를 fake/emulator/target에서 검증하는 계획

## 읽기 결과 템플릿

```text
대상:
문서 revision:
사용한 장/표:
전원/clock/reset 전제:
register/operation sequence:
interrupt/DMA 계약:
timeout와 recovery:
확인한 errata:
driver API에 반영할 state:
실제 보드에서 확인할 항목:
미확인/추측 금지 항목:
```
