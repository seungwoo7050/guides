# 데이터패스와 제어

ISA가 명령어의 의미를 정하면 마이크로아키텍처는 레지스터, ALU, 메모리 인터페이스와 멀티플렉서를 연결해 그 의미를 구현합니다. 데이터가 이동하고 계산되는 경로를 데이터패스라고 하며, 어느 경로를 선택하고 어느 저장소에 쓸지는 제어 신호가 결정합니다.

## 학습 목표

- 명령별 데이터 흐름과 architectural state write를 제어표로 표현합니다.
- 예외가 발생할 때 부분 상태 변경을 막는 신호를 찾습니다.

## 선행 개념

Tiny-RISC 명령 의미와 조합 논리·상태 저장 요소의 차이를 알아야 합니다.

## 한 명령어를 상태 전이로 봅니다

processor의 architectural state를 단순화하면 다음과 같습니다.

```text
PC
integer registers
memory
```

instruction 실행은 이 state 가운데 일부를 읽고 다음 state를 만듭니다.

```text
fetch instruction at PC
→ decode operands
→ compute result/address/condition
→ access memory if needed
→ write register if needed
→ choose next PC
```

단일 사이클 구현은 이 전체를 한 clock period 안에 완료하려고 합니다. multi-cycle과 pipeline 구현은 중간 register를 두고 여러 cycle 또는 여러 instruction에 나눕니다.

## 기본 구성 요소

### PC 레지스터

현재 명령 주소를 보관합니다. 순차 실행, 분기 목적지, 점프 목적지와 예외 벡터 가운데 다음 값을 선택합니다.

### 명령어 메모리 또는 명령어 캐시

PC를 address로 instruction bits를 제공합니다. 실제 processor에서는 cache miss와 translation이 있을 수 있지만 첫 datapath 그림에서는 한 번에 읽힌다고 단순화합니다.

### 레지스터 파일

여러 소스 레지스터를 읽고 목적지 레지스터 하나를 쓰는 포트를 가질 수 있습니다. 쓰기와 읽기가 같은 사이클에 일어날 때 어느 시점의 값이 보이는지는 실행 시점과 전달 경로 설계에 영향을 줍니다.

### 즉시값 생성기

instruction format에 흩어진 immediate field를 조립하고 sign 또는 zero extension합니다.

### ALU

덧셈, 뺄셈, 논리 연산, 비교와 address 계산을 수행합니다. “ALU가 있습니다”만으로 충분하지 않고 어떤 operation을 어떤 control code로 고르는지 정해야 합니다.

### 데이터 메모리 또는 데이터 캐시 인터페이스

load는 address에서 값을 읽고, store는 address와 write data를 전달합니다. byte enable, alignment와 exception도 필요합니다.

### 멀티플렉서

여러 후보 중 control signal에 따라 하나를 선택합니다. ALU의 두 번째 operand가 register인지 immediate인지, write-back 값이 ALU인지 memory인지 같은 경계에 놓입니다.

## `add`의 데이터 흐름

```text
register[rs1] ─┐
                ├─ ALU(add) ─→ register[rd]
register[rs2] ─┘
PC ─→ PC + instruction size
```

필요한 control은 다음과 같습니다.

- register write 활성화
- ALU operand B를 register로 선택
- ALU operation을 add로 선택
- write-back source를 ALU로 선택
- memory read/write 비활성화
- next PC를 순차 address로 선택

## `addi`는 즉시값 경로를 고릅니다

```text
register[rs1] ─┐
                ├─ ALU(add) ─→ register[rd]
sign-extended immediate ─┘
```

`add`와 ALU operation은 같지만 operand B multiplexor가 다릅니다. ISA의 instruction 종류를 datapath 부품 수와 일대일로 만들 필요는 없습니다. 공통 hardware를 control로 재사용합니다.

## `lw`는 주소 계산과 메모리 읽기를 연결합니다

```text
base register + sign-extended offset
→ effective address
→ data memory read
→ register write-back
```

`lw`의 critical path에는 instruction fetch, register read, ALU, data memory와 register write가 모두 포함될 수 있습니다. 단일 사이클 clock period를 가장 느린 instruction에 맞추면 단순 `add`도 같은 긴 period를 기다립니다.

```sh
python3 exercises/processor-model/reference/processor-model.py control lw
```

결과에서 `mem_read=1`, `reg_write=1`, `writeback=memory`를 확인하세요.

## `sw`는 레지스터 결과를 쓰지 않습니다

```text
base + offset → address
소스 레지스터 → 메모리에 쓸 데이터
```

store에는 address 계산용 source와 저장할 data source가 모두 필요합니다. destination register가 없으므로 `reg_write`를 켜면 잘못된 architectural state가 생깁니다.

load와 store가 같은 address 계산 ALU를 공유한다는 점은 같지만 write-back 경로는 다릅니다.

## 분기는 조건에 따라 다음 PC를 정합니다

`beq`를 단순화하면 두 레지스터가 같은지 비교하고 목적지 또는 순차 PC를 선택합니다.

```text
register[rs1] - register[rs2] → zero?
PC + 분기 오프셋 → 목적지
zero && branch_control → 목적지 선택
```

분기 목적지 덧셈기와 ALU를 하나만 두면 같은 사이클에 두 덧셈이 필요할 때 구조적 충돌이 생길 수 있습니다. 별도 덧셈기를 두면 하드웨어는 늘지만 임계 경로와 파이프라인 구성이 단순해질 수 있습니다.

## 제어표는 빠진 쓰기 동작을 찾는 도구입니다

Tiny-RISC의 단순 control signal 일부를 비교하면 다음과 같습니다.

| opcode | reg_write | ALU B | mem_read | mem_write | writeback | branch |
|---|---:|---|---:|---:|---|---|
| `add` | 1 | register | 0 | 0 | ALU | none |
| `addi` | 1 | immediate | 0 | 0 | ALU | none |
| `lw` | 1 | immediate | 1 | 0 | memory | none |
| `sw` | 0 | immediate | 0 | 1 | none | none |
| `beq` | 0 | register | 0 | 0 | none | equal |

새 instruction을 추가할 때는 mnemonic 설명보다 이 표에서 어느 resource를 읽고 쓰는지 먼저 채우세요. `reg_write`나 `mem_write`가 잘못 켜진 bug는 정상 계산 뒤 다른 state를 조용히 손상시킵니다.

## 조합 논리와 상태 요소를 구분합니다

ALU와 multiplexor는 현재 input에 따라 output을 만드는 combinational logic입니다. PC와 register file의 저장 부분은 clock edge 사이에 값을 유지하는 state element입니다.

clocked design을 이해할 때 다음 질문을 분리합니다.

1. 한 cycle 동안 어떤 combinational path로 값이 전파됩니까?
2. clock edge에서 어느 state element가 값을 받아들입니까?
3. write enable이 꺼져 있으면 이전 state가 유지됩니까?
4. setup/hold timing을 만족할 만큼 clock period가 깁니까?

software의 순차 문장처럼 위에서 아래로 즉시 갱신된다고 생각하면 같은 cycle의 read/write 의미를 잘못 해석할 수 있습니다.

## 임계 경로가 클록 주기의 하한을 만듭니다

단일 사이클 processor의 clock period는 가장 긴 활성 경로보다 짧을 수 없습니다.

```text
clock period ≥ state output delay
             + combinational critical path
             + state setup time
```

`lw`가 가장 긴 경로라면 모든 instruction이 그 period를 사용합니다. 단일 사이클 설계가 instruction당 CPI 1이어도 높은 frequency를 보장하지 않습니다.

성능은 다음 둘을 함께 봐야 합니다.

```text
CPU time = instruction count × CPI × clock period
```

CPI만 줄이거나 frequency만 높이면 된다는 결론을 피해야 합니다.

## 다중 사이클 구조는 자원과 긴 경로를 시간으로 나눕니다

한 instruction을 여러 cycle로 나누면 ALU 하나를 PC 증가, address 계산과 arithmetic에 재사용할 수 있습니다.

```text
cycle 1: fetch
cycle 2: decode/register read
cycle 3: execute/address
cycle 4: memory
cycle 5: write-back
```

모든 instruction이 모든 cycle을 사용할 필요는 없습니다. `add`는 memory cycle 없이 끝날 수 있습니다. 대신 intermediate result를 저장할 internal register와 control state machine이 필요합니다.

multi-cycle design은 pipeline과 같지 않습니다.

- multi-cycle은 한 instruction의 단계를 시간으로 나눕니다.
- pipeline은 서로 다른 instruction의 단계를 겹칩니다.

같은 stage 이름을 사용해도 throughput 목표와 hazard가 다릅니다.

## 하드와이어드 제어와 마이크로코드

control signal을 instruction field의 combinational decode로 직접 만들 수 있습니다. 이를 hardwired control이라고 부릅니다.

복잡한 instruction을 작은 내부 operation sequence로 해석하는 control store를 사용할 수도 있습니다. 이를 microcode라고 부릅니다.

두 방식은 절대적인 RISC/CISC 구분선이 아닙니다. modern processor는 단순 instruction과 복잡한 instruction을 서로 다른 방식으로 처리할 수 있습니다. software에 보이는 ISA instruction과 내부 micro-operation 수를 동일시하면 안 됩니다.

## 예외가 발생하면 부분 쓰기를 막아야 합니다

load address가 잘못되었는데 destination register를 먼저 갱신하면 architectural state가 절반만 반영됩니다. control은 exception이 확정될 때 다음 write를 억제해야 합니다.

- register write
- memory write
- PC의 정상 흐름 갱신

pipeline과 out-of-order에서는 여러 instruction이 동시에 진행하므로 precise exception을 만들기 위한 추가 구조가 필요합니다. [out-of-order 문서](../04-parallel-execution/08-superscalar-out-of-order-and-speculation.md)에서 retirement 경계로 다시 다룹니다.

## datapath 그림을 읽는 순서

복잡한 그림을 선 전체로 보지 말고 instruction 하나를 선택해 다음 순서로 표시하세요.

1. 소스 상태를 색칠합니다.
2. 사용하지 않는 multiplexor input은 지웁니다.
3. ALU operation과 memory 방향을 적습니다.
4. 최종 destination state를 표시합니다.
5. next PC 경로를 표시합니다.
6. 잘못된 address나 opcode에서 어떤 write enable을 끄는지 확인합니다.
7. 가장 긴 combinational path를 찾습니다.

## 직접 구현할 순서

[`processor-model`](../exercises/processor-model/README.md)의 `control.py`를 먼저 완성한 뒤 `isa.py`의 state transition을 구현하세요.

```sh
cd exercises/processor-model
EXERCISE_IMPL=skeleton python3 -m unittest \
  tests.test_processor_model.ControlTests \
  tests.test_processor_model.IsaTests -v
```

control table과 interpreter가 같은 instruction 의미를 가져야 합니다. 한쪽에서 `sw`가 register를 쓰거나 `lw`가 memory 대신 ALU 결과를 write-back하면 테스트와 표가 어긋납니다.

## 직접 확인할 문제

1. `lw`와 `sw`가 공유할 수 있는 datapath와 공유할 수 없는 write 경로를 구분해 보세요.
2. 단일 사이클 processor에서 CPI가 1이어도 multi-cycle보다 느릴 수 있는 조건을 식으로 설명해 보세요.
3. 분기 목적지 덧셈기를 별도로 둘 때 얻는 이점과 하드웨어 비용을 설명해 보세요.
4. 잘못된 load address가 발생했을 때 어떤 state write를 막아야 하는지 적어 보세요.
5. control table에 새 `xor immediate` instruction을 추가하려면 어떤 field와 signal이 필요한지 설계해 보세요.

## 연결 실습

[`processor-model` stage-04](../../exercises/processor-model/README.md)에서 opcode별 제어 신호를 구현합니다.

## 완료 기준

- `lw`, `sw`, ALU와 branch의 write path를 제어표에서 구분할 수 있습니다.
- 잘못된 주소에서 차단해야 하는 상태 write를 열거할 수 있습니다.
- `make stage-04 EXERCISE_IMPL=workspace`가 통과합니다.
