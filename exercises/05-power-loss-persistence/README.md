# 실습 5 — power-loss-safe persistence

## 문제

flash는 일반 RAM처럼 byte를 덮어쓰지 못하며 erase/program 단위와 bit transition 제약이 있습니다. record를 갱신하는 중 전원이 끊겨도 boot 뒤 **마지막 완전한 상태 또는 새로 완성된 상태**를 판별해야 합니다. 이 실습은 byte-array flash model로 cut point를 전부 검사합니다.

## 학습 목표

- erase, program, verify와 commit을 별도 transition으로 나눕니다.
- version·sequence·length·checksum과 commit marker의 의미를 설명합니다.
- torn write, corrupted header와 sequence wrap에서 recovery를 설계합니다.
- wear, garbage collection와 schema migration의 범위를 구분합니다.
- 모든 의미 있는 power cut를 결정적으로 주입합니다.

## 제공 코드와 시작 방법

이 실습은 hardware 없이 실행되는 256-byte, two-slot NOR model을
제공합니다. `starter/persistence.py`의 공개 함수를 완성하고 같은
checker로 reference와 자신의 구현을 검사합니다.

```sh
python3 check.py --submission reference
python3 check.py --submission starter       # 초기 상태는 exit 1
python3 check.py --submission workspace/implementation
python3 check.py --submission reference --json
```

checker 종료 코드는 다음과 같습니다.

- `0`: 모든 공개 행동·불변식 검사 통과
- `1`: submission을 실행했지만 하나 이상의 행동 계약 실패
- `2`: 경로·import·공개 interface가 잘못됨

submission 디렉터리에는 `persistence.py`가 있어야 합니다. 공개 계약은
`NorFlash`, `seed_image`, `apply_update`, `recover`, `operation_lengths`,
`cut_points`와 두 예외 타입입니다. checker는 source 모양이 아니라 NOR
bit transition, byte-boundary cut 뒤 recovery, corruption, sequence wrap와
schema 분류를 관찰합니다.

`known-wrong/commit-polarity`는 erased marker를 committed로 해석하는
의도적 오답입니다. 다음 명령이 exit 1인지 확인하면 “commit 전에는 새
record가 보이지 않는다”는 검사가 실제로 작동함을 확인할 수 있습니다.

```sh
python3 check.py --submission known-wrong/commit-polarity
```

## 저장할 상태

작은 configuration record를 사용합니다.

```text
sample_interval_ms
threshold
mode
schema_version
```

두 개 slot 또는 append-only page 중 하나를 선택합니다.

## flash model

최소 contract:

- erased byte는 `0xFF`
- program은 허용된 방향의 bit transition만 수행
- erase는 erase unit 전체
- program alignment/granularity
- operation 중 임의 byte 경계에서 power loss 가능
- reboot는 RAM state를 모두 잃고 flash bytes만 사용

실제 장치의 정확한 규칙을 모델링한다면 datasheet 판본을 기록합니다.

## record format

예시:

```text
magic
format_version
payload_length
sequence
payload
checksum
commit_state
```

필드 순서와 commit protocol은 직접 설계합니다. commit marker를 먼저 쓰면 안 되는 이유를 trace로 보여야 합니다.

## update protocol

대표 흐름:

```text
active record A 확인
→ inactive slot B erase
→ B header/payload/checksum program
→ read-back와 integrity verify
→ B commit
→ optional A obsolete 표시
```

A를 언제 지워도 되는지 정합니다. B가 durable함을 확인하기 전에 A를 지우지 않습니다.

## recovery algorithm

boot 시 각 slot을 분류합니다.

- erased
- incomplete
- structurally invalid
- checksum invalid
- committed valid
- unsupported schema

valid record가 여러 개면 sequence ordering과 wrap rule을 사용합니다. 단순 signed/unsigned 비교가 wrap에서 깨지지 않는지 검사합니다.

## 필수 cut point

모든 erase/program operation의 다음 위치에서 전원을 끊습니다.

- operation 전
- 첫 byte/word 뒤
- 중간
- 마지막 data 뒤, commit 전
- commit 일부
- commit 완료 뒤
- old record obsolete 표시 중

각 reboot 뒤 허용 상태:

```text
old complete record
또는
new complete record
```

두 record 모두 invalid, 부분 payload를 valid로 해석, future schema를 잘못 읽는 상태는 금지합니다.

## corruption과 wear

power loss와 bit corruption을 분리합니다.

- checksum은 accidental corruption detection이지 authenticity가 아닙니다.
- sequence가 정상이어도 payload integrity가 실패할 수 있습니다.
- erase count와 bad region policy는 별도 metadata가 필요할 수 있습니다.
- 작은 configuration을 너무 자주 쓰지 않도록 coalesce/rate limit합니다.

## schema migration

- old schema를 읽을 수 있는 기간
- new record를 언제 commit하는지
- downgrade/rollback firmware가 읽을 수 있는지
- migration 중 power loss
- default와 invalid value 구분

firmware update와 persistent migration을 함께 설계할 때는 [update 실습](../06-update-rollback-model/README.md)과 연결합니다.

## 필수 결과물

```text
workspace/
├── format.md
├── update-protocol.md
├── recovery.md
├── flash-model/
├── fixtures/
│   ├── cut-points/
│   └── corruptions/
├── test-report.md
└── limitations.md
```

## 완료 조건

- flash physical constraint를 model이 실제로 거부합니다.
- every cut point 뒤 recovery가 old/new complete 중 하나를 선택합니다.
- incomplete/invalid record는 사용되지 않습니다.
- sequence wrap와 동률 정책이 결정적입니다.
- schema compatibility와 unsupported 상태가 명확합니다.
- wear와 write frequency를 정량 또는 정책으로 기록합니다.
- 실제 hardware test가 없다면 endurance/retention을 보장하지 않는다고 씁니다.

## 잘못된 완료

- 파일을 atomic rename하는 host filesystem로 flash를 대체
- payload를 쓴 뒤 checksum 없이 valid 처리
- old record를 먼저 erase
- power cut를 operation 사이에서만 주입하고 program 중은 무시
- magic 값만으로 integrity 판정
- sequence overflow 무시

## 선택 확장

- append-only log와 garbage collection
- bad block/failed program
- retained RAM cache
- encrypted/authenticated record의 lifecycle 경계
- 실제 보드의 controllable power-cut fixture

## 모델의 한계

reference는 byte 단위로 진행하는 추상 NOR입니다. 실제 controller의
word/page program, ECC, cache, voltage brownout, erase suspend, endurance와
retention을 증명하지 않습니다. 실제 target 결과에는 part number,
datasheet revision, program/erase geometry와 power-cut 장비 조건을 별도로
기록해야 합니다.

## 검토 질문

1. commit marker를 마지막에 쓰더라도 marker program 자체가 torn될 수 있는 문제를 어떻게 다룹니까?
2. 두 slot이 모두 valid일 때 sequence wrap를 안전하게 비교하는 방법을 제안해 보세요.
3. update rollback와 persistent schema migration이 충돌하는 trace를 작성해 보세요.
4. checksum 통과가 malicious modification 방어를 의미하지 않는 이유는 무엇입니까?
