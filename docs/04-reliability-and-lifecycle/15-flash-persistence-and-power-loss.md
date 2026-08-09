# flash persistence와 power loss

비휘발성 memory에 값을 썼다는 사실만으로 durable state가 되지 않습니다. flash는 erase와 program granularity, 1→0 bit transition, 제한된 endurance와 power-loss 중 torn operation을 가집니다. persistent format은 reset과 firmware version 변경 뒤에도 마지막 유효 상태를 판별할 수 있어야 합니다.

## 학습 목표

- flash erase/program granularity와 endurance가 data structure에 미치는 영향을 설명합니다.
- torn write, partially erased sector와 stale metadata를 처리합니다.
- append log, dual-copy, sequence, version, CRC와 commit marker를 사용해 유효 record를 판별합니다.
- garbage collection와 migration 중 power loss cut point를 설계합니다.
- durability와 integrity, authenticity를 구분합니다.

## flash 특성

일반적인 on-chip NOR flash 특성:

- erase는 sector/page 단위
- program은 더 작은 word/line 단위
- erase 뒤 bit는 보통 1
- program은 1→0으로만 가능하고 0→1은 erase 필요
- erase/program 시간 동안 read 또는 execution 제약 가능
- erase cycle endurance 제한
- voltage/temperature와 silicon에 따른 조건

정확한 값은 SoC와 flash 문서를 확인합니다.

## in-place update가 위험한 이유

```text
old record
→ erase sector
→ write new record
```

erase 뒤 write 전에 전원이 꺼지면 old와 new가 모두 없습니다. write 중 power loss면 일부 byte만 program될 수 있습니다.

따라서 “한 번의 C assignment”가 persistent atomic update가 아닙니다.

## record format

대표 format:

```text
magic
format version
payload length
sequence/generation
payload
payload CRC
commit marker
```

검증 순서:

1. bounds와 alignment를 확인합니다.
2. magic과 format version을 확인합니다.
3. length가 region 안인지 확인합니다.
4. CRC/integrity를 확인합니다.
5. commit marker와 sequence를 확인합니다.
6. 지원하는 schema로 decode합니다.

CRC는 accidental corruption 탐지용입니다. malicious modification과 authenticity는 보안 설계가 필요합니다.

## append-only log

```text
empty flash
→ record 1 committed
→ record 2 committed
→ record 3 torn

boot scan 결과: record 2가 마지막 유효 상태
```

새 record를 빈 영역에 쓰고 마지막에 commit marker를 기록합니다. marker write의 atomic granularity와 ordering을 확인합니다.

장점:

- old record를 즉시 파괴하지 않음
- power-loss recovery가 단순
- history/diagnostics 가능

비용:

- scan 시간
- garbage collection
- space overhead
- sequence wrap와 wear distribution

## dual-copy/A-B slot

```text
slot A: generation 10, valid
slot B: generation 11, writing
```

새 값을 inactive slot에 쓰고 검증한 뒤 active generation을 선택합니다. selector 자체를 안전하게 갱신하거나 generation 비교로 selector를 제거할 수 있습니다.

두 copy가 모두 유효한 경우 sequence wrap와 tie-break rule이 필요합니다.

## power-loss cut point를 모두 열거합니다

예: 새 record commit

1. erase 시작 전
2. erase 중
3. header write 중
4. payload write 중
5. CRC write 중
6. commit marker 전
7. commit marker 중/후
8. old sector garbage collection 중

각 cut point 뒤 reboot했을 때 어떤 record가 선택돼야 하는지 표로 만듭니다.

## sequence wrap

unsigned sequence는 언젠가 wrap합니다. 단순 `a > b` 비교가 실패합니다. 비교 범위를 제한하거나 epoch, wider counter 또는 modular comparison을 사용합니다. factory reset과 storage migration도 generation policy에 포함합니다.

## garbage collection

log space가 부족하면 live record를 새 sector로 복사하고 old sector를 erase합니다.

```text
select destination
→ copy live records
→ verify destination
→ mark destination active
→ erase old source
```

active marker를 바꾸기 전에 destination이 완전해야 합니다. collection 중 reset을 반복해도 최소 하나의 complete set가 남아야 합니다.

## schema evolution

firmware update 뒤 record format이 바뀔 수 있습니다.

- format version
- backward-compatible reader
- migration result를 새 record로 commit
- migration 중 power loss
- rollback된 old firmware가 new format을 읽을 수 있는지

firmware rollback과 persistent schema compatibility를 함께 설계합니다. 새 firmware가 storage를 irreversible하게 바꾸면 old image로 revert해도 boot하지 못할 수 있습니다.

## wear budget

```text
writes per day
× product lifetime
÷ available sectors와 wear distribution
```

logging every second을 같은 sector에 쓰면 endurance를 빠르게 소모할 수 있습니다. coalescing, batching, ring rotation과 write-on-change를 고려합니다.

관찰 counter도 persistent write를 늘릴 수 있으므로 RAM aggregation 후 제한적으로 commit합니다.

## file system과 settings library도 계약을 확인합니다

library를 사용해도 다음은 확인해야 합니다.

- atomicity 단위
- power-fail behavior
- corruption recovery
- mount/scan 시간
- wear leveling
- maximum key/value와 record 수
- concurrent access
- format migration

“filesystem이므로 안전하다”는 충분한 설명이 아닙니다.

## failure와 검증

- every cut point에서 reset/power loss
- full region에서 append
- sequence wrap 인접 값
- CRC failure
- unknown version/length
- garbage collection 중 repeated reset
- storage nearly worn/full
- firmware rollback과 schema change

host state model, flash emulator와 HIL power switch를 단계적으로 사용합니다.

## 실습 연결

[power-loss-safe persistence](../../exercises/05-power-loss-persistence/README.md)에서 dual-copy 또는 append log를 설계하고 모든 cut point의 expected recovery를 제출합니다.

## 직접 확인할 문제

1. erase-then-write in-place update가 old state와 new state를 모두 잃는 cut point를 설명해 보세요.
2. CRC가 authenticity를 보장하지 않는 이유를 적어 보세요.
3. firmware rollback과 storage schema migration이 충돌하는 예를 작성해 보세요.
4. append log의 garbage collection을 power-loss-safe하게 만드는 commit 순서를 설계해 보세요.

## 이 장이 보장하지 않는 것

flash 전압·온도별 retention, vendor ECC, bad block와 NAND FTL을 완전히 다루지 않습니다. production storage는 target flash specification과 endurance test가 필요합니다.
