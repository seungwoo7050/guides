# Tiny-RISC 실습 ISA 명세

`Tiny-RISC`는 데이터패스와 파이프라인 실습을 위해 만든 작은 명령 집합입니다. 실제 RISC-V나 MIPS의 연산 코드 인코딩, ABI, 예외 모델 또는 바이너리 형식과 호환되지 않습니다. 명령 하나가 읽고 쓰는 상태를 명시하고 그 계약을 데이터패스와 위험 판정으로 연결하는 데 목적이 있습니다.

## 구조적 상태

실행기가 외부에 보이는 상태는 다음과 같습니다.

```text
PC                 다음에 실행할 명령의 index
r0..r7             32-bit integer register 8개
memory             little-endian byte-addressed memory
halted             halt 실행 여부
```

모든 산술 결과는 하위 32비트만 남기고 2의 보수 signed 값으로 표시합니다. bitwise 연산은 같은 32비트 pattern에 적용합니다.

### `r0`의 계약

`r0`은 항상 0입니다.

- `r0`을 source로 읽으면 0입니다.
- `r0`을 destination으로 쓰는 결과는 버립니다.
- 각 명령이 끝난 뒤에도 `r0 == 0`이어야 합니다.

이 불변식은 실제 RISC ISA에서 흔히 볼 수 있는 zero register를 단순화한 것입니다. register renaming이나 dependency 제거를 완전히 모델링하는 것은 아닙니다.

### PC의 단위

PC는 byte address가 아니라 **명령 index**입니다.

```text
PC=0 → 첫 번째 명령
PC=1 → 두 번째 명령
```

분기 label도 명령 index로 해석합니다. 따라서 실제 ISA의 instruction alignment와 PC-relative byte offset 계산은 이 도구에 포함되지 않습니다.

## 소스 형식

한 줄에 명령 하나를 작성하며 `#` 뒤는 comment입니다.

```asm
start:
    li   r1, 4        # 반복 횟수
    li   r2, 0
loop:
    add  r2, r2, r1
    addi r1, r1, -1
    bne  r1, r0, loop
    halt
```

label은 영문자 또는 `_`로 시작하고 이후에는 영문자, 숫자와 `_`를 사용할 수 있습니다. 같은 label을 두 번 정의하거나 존재하지 않는 label을 참조하면 parsing 단계에서 실패합니다.

integer literal은 Python의 `int(text, 0)` 규칙을 사용합니다.

```text
42       decimal
-7       negative decimal
0xff     hexadecimal
0b1010   binary
0o17     octal
```

## 명령어 요약

| 명령 | 형식 | 읽는 상태 | 쓰는 상태 |
|---|---|---|---|
| `li` | `li rd, imm` | immediate | `rd` |
| `add` | `add rd, rs1, rs2` | `rs1`, `rs2` | `rd` |
| `addi` | `addi rd, rs1, imm` | `rs1`, immediate | `rd` |
| `sub` | `sub rd, rs1, rs2` | `rs1`, `rs2` | `rd` |
| `and` | `and rd, rs1, rs2` | `rs1`, `rs2` | `rd` |
| `or` | `or rd, rs1, rs2` | `rs1`, `rs2` | `rd` |
| `xor` | `xor rd, rs1, rs2` | `rs1`, `rs2` | `rd` |
| `lw` | `lw rd, offset(base)` | `base`, memory word | `rd` |
| `sw` | `sw rs, offset(base)` | `rs`, `base` | memory word |
| `beq` | `beq rs1, rs2, label` | `rs1`, `rs2` | PC |
| `bne` | `bne rs1, rs2, label` | `rs1`, `rs2` | PC |
| `j` | `j label` | label | PC |
| `halt` | `halt` | 없음 | `halted` |

## 산술·논리 명령어

### `li rd, imm`

immediate를 32비트로 자른 뒤 `rd`에 씁니다.

```text
R[rd] ← wrap32(imm)
PC ← PC + 1
```

`li`는 실제 RISC-V의 단일 base instruction과 같지 않습니다. 큰 constant를 여러 instruction으로 만드는 과정을 생략하기 위한 pseudo instruction입니다.

### `add rd, rs1, rs2`

```text
R[rd] ← wrap32(R[rs1] + R[rs2])
PC ← PC + 1
```

signed overflow trap은 발생하지 않습니다. 하위 32비트가 남습니다.

### `addi rd, rs1, imm`

```text
R[rd] ← wrap32(R[rs1] + imm)
PC ← PC + 1
```

immediate field 폭은 제한하지 않습니다. 실제 encoding의 immediate 폭과 sign extension을 연습하려면 별도 encoding 실습이 필요합니다.

### `sub rd, rs1, rs2`

```text
R[rd] ← wrap32(R[rs1] - R[rs2])
PC ← PC + 1
```

### `and`, `or`, `xor`

두 소스 레지스터의 하위 32비트 패턴에 비트 단위 연산을 적용하고 결과를 `rd`에 씁니다.

```text
R[rd] ← wrap32(R[rs1] OP R[rs2])
PC ← PC + 1
```

## 메모리 명령어

memory는 byte address를 사용하고 word는 4바이트입니다. word는 little-endian으로 저장합니다.

```text
address 0: least significant byte
address 1: 다음 byte
address 2: 다음 byte
address 3: most significant byte
```

유효한 word access는 다음 두 조건을 만족해야 합니다.

```text
address % 4 == 0
0 <= address && address + 4 <= memory_size
```

조건을 어기면 실행기는 `RuntimeError`를 발생시키고 프로그램을 중단합니다. 실제 processor의 precise exception state, trap vector와 recovery는 모델링하지 않습니다.

### 유효 주소

`offset(base)`의 주소는 다음과 같습니다.

```text
effective_address = R[base] + offset
```

주소 계산 결과에는 32비트 wrapping을 적용하지 않습니다. 음수 주소와 memory 범위 밖 주소를 명시적으로 거부합니다.

### `lw rd, offset(base)`

```text
address ← R[base] + offset
R[rd] ← signed32(memory[address .. address+3], little-endian)
PC ← PC + 1
```

### `sw rs, offset(base)`

```text
address ← R[base] + offset
memory[address .. address+3] ← low32(R[rs]), little-endian
PC ← PC + 1
```

`sw`의 첫 번째 register는 **저장할 값**입니다. destination register는 없습니다.

## 제어 흐름 명령어

### `beq rs1, rs2, label`

```text
if R[rs1] == R[rs2]:
    PC ← labels[label]
else:
    PC ← PC + 1
```

### `bne rs1, rs2, label`

```text
if R[rs1] != R[rs2]:
    PC ← labels[label]
else:
    PC ← PC + 1
```

### `j label`

```text
PC ← labels[label]
```

link register, return address와 call convention은 제공하지 않습니다.

### `halt`

```text
halted ← true
PC ← PC + 1
```

실행 결과의 PC는 `halt` 다음 명령 index를 가리킵니다.

## 실행 종료와 실패

정상 종료는 반드시 `halt`를 실행해야 합니다. 다음 조건은 실패입니다.

- PC가 프로그램 범위를 벗어납니다.
- `max_steps`를 넘습니다.
- 정렬되지 않은 word address를 사용합니다.
- memory 범위를 벗어납니다.
- parsing 단계에서 opcode, register, operand 또는 label이 잘못됐습니다.

무한 loop를 방치하지 않도록 기본 `max_steps`는 100,000입니다.

## 단일 사이클 제어 모델

`processor-model control`은 다음 제어 신호를 반환합니다.

| 신호 | 의미 |
|---|---|
| `reg_write` | register file write 여부 |
| `alu_src` | 두 번째 ALU operand의 출처 |
| `alu_op` | ALU가 수행할 연산 |
| `mem_read` | data memory read 여부 |
| `mem_write` | data memory write 여부 |
| `writeback` | register에 쓸 값의 출처 |
| `branch` | 분기 조건 종류 |
| `jump` | unconditional jump 여부 |

예를 들어 `lw`의 경로는 다음과 같습니다.

```text
register file base read
→ immediate offset 선택
→ ALU add로 effective address 계산
→ data memory read
→ memory data를 register file에 write back
```

```sh
python3 exercises/processor-model/reference/processor-model.py control lw
```

이 표는 제어 경로를 설명하기 위한 것입니다. 실제 단일 사이클 implementation의 exact wire width, mux encoding과 timing은 고정하지 않습니다.

## 5단계 파이프라인 추적 형식

pipeline 실습은 register 값까지 실행하지 않고 정적 명령열, label과 branch 결과 annotation을 입력합니다.

```text
IF → ID → EX → MEM → WB
```

분기를 실행하는 경우 명령 뒤에 `@taken`을 붙이고 목적지 레이블을 실제로 정의해야 합니다.

```text
li r1, 1
beq r1, r1, target @taken
addi r4, r0, 99
addi r5, r0, 88
target:
addi r4, r0, 7
```

분기가 EX에서 해소되는 시점에 `addi ... 99`는 ID, `addi ... 88`은 IF에 있을 수 있습니다. 모의 실행기는 두 명령을 비우고 `target`의 명령 인덱스부터 다시 가져옵니다. 실행 기록의 `ID*`와 `IF*`는 잘못된 경로에서 버려졌음을 뜻합니다.

`@taken`은 해당 정적 branch가 실행될 때마다 taken이라고 가정합니다. backward branch에 붙이면 반복 실행될 수 있으므로 `max_cycles`가 실행을 제한합니다. branch condition을 실제 register 값으로 계산하려면 ISA interpreter를 사용해야 합니다.

### 전달 방식

`--forwarding full`은 다음을 가정합니다.

- 일반 ALU 결과는 다음 instruction이 EX에서 사용할 수 있습니다.
- load data는 MEM이 끝나야 생기므로 바로 뒤의 consumer에는 1-cycle load-use stall이 필요합니다.

`--forwarding none`은 ID의 source가 EX 또는 MEM의 destination과 겹치면 stall합니다. register file의 write-first/read-later timing은 단순화되어 WB와 ID 충돌은 별도 stall로 세지 않습니다.

### 분기 모델

- branch는 EX에서 해소됩니다.
- 기본 예측은 not-taken입니다.
- taken이면 IF와 ID의 younger instruction을 flush합니다.
- `branch_penalty`만큼 추가 fetch를 막습니다.

실제 프로세서는 분기 목적지 버퍼, 방향 예측기, 추측 실행과 복구를 더 복잡하게 구현할 수 있습니다. 이 모델의 사이클 수를 특정 CPU의 사이클 수로 해석하면 안 됩니다.

## 직접 검증할 프로그램

다음 프로그램의 최종 `r2`와 실행 단계 수를 손으로 계산한 뒤 실행하세요.

```asm
li r1, 4
li r2, 0
loop:
    add r2, r2, r1
    addi r1, r1, -1
    bne r1, r0, loop
halt
```

```sh
python3 exercises/processor-model/reference/processor-model.py isa \
  exercises/processor-model/fixtures/programs/sum.asm
```

확인할 불변식은 다음과 같습니다.

```text
반복 시작 시 r2에는 이미 더한 4부터 r1+1까지의 합이 있습니다.
r1은 이번 반복에서 더할 값입니다.
r0은 모든 단계에서 0입니다.
```
