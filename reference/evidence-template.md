# 임베디드 변경 evidence 템플릿

## 1. 문제

```text
기대 동작:
실제 동작:
영향:
재현 빈도:
최초 확인 시점:
```

## 2. target와 build

```text
repository/source revision:
board와 revision:
SoC/MCU part와 revision:
external device:
toolchain/SDK:
build command:
Kconfig fragment:
Devicetree overlay:
image build ID/hash:
bootloader version:
```

첨부:

- final `.config`
- merged Devicetree/generated description
- ELF와 map 보관 위치
- size/stack report

## 3. 실행 조건

```text
power supply/voltage:
clock configuration:
temperature 또는 환경:
debugger 연결 여부:
logging/tracing configuration:
fixture/probe/analyzer:
firmware state before run:
```

## 4. 재현 절차

```text
1.
2.
3.
```

reset/flash/cleanup을 포함해 다른 사람이 known state에서 시작할 수 있게 작성합니다.

## 5. 상태와 사건

```text
state owner:
state before:
input event/context:
transition:
state after:
유지해야 할 invariant:
```

## 6. raw evidence

```text
serial log:
trace:
register dump:
crash record:
bus capture:
logic analyzer:
current measurement:
flash bytes/metadata:
```

원시 파일의 hash와 decoder/version을 남깁니다.

## 7. 원인과 반증

```text
확인한 사실:
현재 가설:
가설을 지지하는 evidence:
이미 배제한 원인:
아직 확인하지 못한 조건:
```

의도를 code에서 확인하지 못했다면 사실로 표현하지 않습니다.

## 8. 변경

```text
변경한 owner/contract:
왜 이 계층이 맞는가:
호환성 영향:
RAM/flash/stack 영향:
timing/power 영향:
reset/update 영향:
```

## 9. 검증

| 검사 | 환경 | 기대 | 실제 | 판정 |
|---|---|---|---|---|
| normal | | | | |
| boundary | | | | |
| failure | | | | |
| recovery | | | | |

추가:

```text
host/model test:
simulator/emulator:
actual board:
미검증 범위:
```

## 10. rollback와 운영

```text
변경 rollback 방법:
field device migration:
telemetry/alert:
known residual risk:
후속 작업:
```
