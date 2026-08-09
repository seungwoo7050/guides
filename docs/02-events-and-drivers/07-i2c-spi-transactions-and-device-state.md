# I2C·SPI transaction과 device state

I2C와 SPI는 byte를 이동하는 bus이지만 application은 “sensor sample을 읽는다”, “flash page를 쓴다” 같은 device operation을 원합니다. controller transfer가 성공했다고 device operation이 성공한 것은 아니며, retry가 항상 안전한 것도 아닙니다.

## 학습 목표

- bus, controller, target device와 application operation 상태를 분리합니다.
- I2C와 SPI의 addressing·chip select·clock·mode 계약을 비교합니다.
- partial transfer, timeout, retry, duplicate command와 bus recovery를 설계합니다.
- driver가 register protocol과 application policy 사이에서 소유할 책임을 정합니다.

## 네 층의 성공을 구분합니다

```text
application operation
→ device protocol command
→ bus transaction
→ controller/electrical transfer
```

예를 들어 temperature sample read:

1. application이 fresh sample을 요청합니다.
2. driver가 conversion 시작 command를 씁니다.
3. device가 conversion을 수행합니다.
4. ready를 기다립니다.
5. result register를 읽습니다.
6. raw value를 검증·변환합니다.

I2C write가 ACK됐다는 사실은 conversion 완료나 sample freshness를 보장하지 않습니다.

## I2C state

대표 state:

- controller idle/busy/error
- START, address, read/write direction
- ACK/NACK
- repeated START
- STOP
- SDA/SCL level
- bus arbitration 또는 clock stretching
- target internal register pointer

NACK 의미는 하나가 아닙니다.

- address에 device가 없음
- device가 busy
- command/register가 잘못됨
- write data를 거부
- power 또는 wiring 문제

driver는 context와 retry policy를 함께 사용해야 합니다.

## SPI state

SPI에는 보편적인 device addressing이 없고 chip select와 protocol이 device별입니다.

확인 항목:

- CPOL/CPHA mode
- bit order
- word size
- max/min clock
- chip select setup/hold와 transaction 동안 유지 여부
- full-duplex dummy byte
- command/address/data phase
- busy pin 또는 status polling

controller transfer 완료는 external flash program 완료가 아닐 수 있습니다. status busy bit와 timeout을 별도로 확인합니다.

## transaction boundary를 명시합니다

```text
lock bus
→ configure controller if needed
→ assert/select device
→ command/address phase
→ data transfer
→ deassert
→ release bus
```

여러 device가 bus를 공유하면 configuration과 chip select도 shared state입니다. driver가 transaction 중 lock을 놓으면 다른 device 설정이 끼어들 수 있습니다.

## device driver는 register protocol을 상태 기계로 만듭니다

예시 sensor:

```text
OFF
→ RESETTING
→ CONFIGURING
→ IDLE
→ CONVERTING
→ DATA_READY
→ READING
→ IDLE

모든 상태에서
→ BUS_ERROR
→ RECOVERING
→ IDLE 또는 FAILED
```

공개 API:

```text
init
configure
start_sample
poll/wait_ready
read_sample
cancel
reset/recover
```

각 operation의 valid state, timeout, side effect와 duplicate call을 정의합니다.

## retry가 안전한지 operation 의미로 판단합니다

### 안전할 가능성이 높은 경우

- read-only status query
- 동일 값을 configuration register에 쓰는 idempotent operation
- request identity가 있는 command

### 위험한 경우

- FIFO pop/read-clear register
- “한 단계 이동” command
- flash program/erase
- actuator pulse
- device 내부 pointer가 전진하는 stream write

timeout은 command가 실행되지 않았다는 증거가 아닙니다. 결과가 UNKNOWN이면 device status를 재조정하거나 reset해야 합니다.

## partial transfer와 buffer 상태

controller가 `n` byte 중 일부만 옮겼다면:

- 몇 byte가 실제 wire에 나갔습니까?
- device가 command prefix를 받아 state를 바꿨습니까?
- receive buffer의 어느 부분이 새 값입니까?
- retry는 처음부터 가능합니까?
- chip select/STOP이 transaction을 abort했습니까?

API가 단순 error code만 반환하면 driver 내부에서 partial state를 제거하거나 전체 operation을 failure atomic하게 만들어야 합니다.

## bus recovery는 장치 recovery와 다릅니다

I2C에서 SDA가 low에 고정되면 controller reset만으로 해결되지 않을 수 있습니다. clock pulse와 STOP을 생성하거나 power cycle이 필요할 수 있습니다. 하지만 bus line을 되살렸다고 device internal state가 정상인 것은 아닙니다.

```text
controller recovery
→ physical bus idle 확인
→ target identity/status 확인
→ device reset 또는 reconfigure
→ application state 재조정
```

## CRC, identity와 freshness

일부 device는 data CRC를 제공합니다. CRC 성공은 다음을 보장하지 않습니다.

- 올바른 sensor instance
- 최신 sample
- 올바른 configuration
- physical quantity의 정상 범위

driver 또는 application은 device ID, sequence, ready timestamp와 configuration generation을 필요에 따라 확인합니다.

## concurrency와 bus ownership

- bus controller는 하나의 transaction owner만 가져야 합니다.
- device driver는 자신의 protocol state를 직렬화합니다.
- ISR에서 synchronous I2C/SPI transfer를 시작하지 않습니다.
- cancellation과 timeout 뒤 controller와 device state를 둘 다 정리합니다.
- DMA를 사용하면 buffer ownership까지 추가합니다.

## 실패와 검증

fault injection 목록:

- address NACK
- command 중간 NACK
- bus busy timeout
- stuck SDA/SCL
- wrong device ID
- CRC error
- conversion timeout
- stale sample
- reset 직후 default configuration
- retry 중 duplicate side effect

각 fault 뒤 driver state와 다음 허용 operation을 검사합니다.

## 실습 연결

[sensor driver 상태 기계](../../exercises/03-sensor-driver-state-machine/README.md)에서 mock bus를 사용해 controller error와 device protocol error를 분리합니다.

## 직접 확인할 문제

1. I2C write가 ACK됐지만 sensor sample이 준비되지 않은 상태 trace를 작성해 보세요.
2. SPI flash program command를 timeout 뒤 무조건 다시 보내면 위험한 이유를 설명해 보세요.
3. bus recovery 뒤 device configuration을 다시 확인해야 하는 이유를 적어 보세요.
4. read-clear status register를 retry-safe API로 감싸려면 어떤 snapshot이 필요합니까?

## 이 장이 보장하지 않는 것

pull-up 저항, rise time, voltage level, trace length, signal integrity와 device별 timing은 electrical design과 datasheet 영역입니다. logic analyzer 결과를 protocol state와 함께 해석하되 회로 검증을 대체하지 않습니다.
