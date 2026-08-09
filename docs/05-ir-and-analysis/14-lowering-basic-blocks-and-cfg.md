# Lowering, basic block과 CFG

AST는 source 구조를 보존하지만 실행 순서와 branch target을 암묵적으로 담습니다. Intermediate representation(IR)은 다음 분석과 backend가 필요한 사실을 더 명시적으로 만들기 위해 추상화 수준을 낮춥니다.

## 학습 목표

- desugaring, lowering과 code generation을 구분합니다.
- basic block, instruction과 terminator invariant를 설계합니다.
- if, while, short-circuit와 return을 CFG로 낮춥니다.
- source origin과 symbol/type 정보를 IR에 필요한 만큼 보존합니다.

## IR의 목적을 먼저 정합니다

“IR을 만든다”는 말만으로는 부족합니다. 같은 compiler에도 여러 IR이 있을 수 있습니다.

### HIR

Source-level type과 declaration 구조를 많이 보존합니다.

- generic·method·pattern 같은 고수준 의미
- 좋은 source diagnostic
- language-specific optimization

### MIR

Control flow, temporary와 evaluation order를 명시합니다.

- basic block
- explicit branch
- local/temporary
- data-flow 분석

### LIR / target IR

Machine operation과 representation에 가까워집니다.

- pointer와 memory access
- concrete integer width
- calling convention
- target instruction 또는 LLVM IR

하나의 IR로 모든 목적을 해결하려 하면 source tool에는 너무 낮고 backend에는 너무 높은 표현이 될 수 있습니다.

## Basic block invariant

```text
BasicBlock
  parameters/phi 선택
  instructions[]
  terminator
```

Invariant:

- block 안 instruction은 순차 실행됩니다.
- 중간 instruction은 다른 block으로 직접 branch하지 않습니다.
- 마지막에 terminator가 정확히 하나 있습니다.
- terminator 뒤 instruction은 없습니다.
- 모든 target은 같은 function 안의 유효 block입니다.

Entry block은 predecessor가 없고 function parameter/local initialization을 시작합니다. Exit block을 하나로 합칠지 여러 return을 허용할지는 IR 설계 선택입니다.

## Temporary와 value identity

Three-address 형태:

```text
v1 = const 2
v2 = const 3
v3 = mul v1, v2
v4 = add v0, v3
```

각 instruction result는 `ValueId`를 가집니다. 이름은 debug display일 뿐 identity는 stable id입니다. Type checker 결과를 IR value type으로 낮추되 source alias와 high-level nominal identity를 얼마나 보존할지 정합니다.

## If lowering

Source:

```text
if condition {
    then_body
} else {
    else_body
}
after
```

CFG:

```text
current:
  c = lower(condition)
  branch c, then_block, else_block

then_block:
  lower(then_body)
  jump merge

else_block:
  lower(else_body)
  jump merge

merge:
  lower(after)
```

Branch body가 return하면 merge jump를 추가하지 않습니다. Lowering helper는 current block이 이미 terminated됐는지 확인합니다.

## While lowering

```text
preheader → header(condition)
               ├─true→ body ─→ latch ─┐
               └─false→ exit          │
                         header ←─────┘
```

Break와 continue를 지원하면 lowering context에 target stack을 둡니다.

```text
LoopContext(break_target=exit, continue_target=header/latch)
```

Nested loop에서 가장 가까운 target을 사용합니다. Labelled break를 지원하면 label resolution 결과를 사용합니다.

## Short-circuit lowering

`a && b`를 eager `and` instruction으로 바꾸지 않습니다.

Boolean value가 필요한 expression context에서는 merge value가 필요합니다.

```text
entry:
  a_value = lower(a)
  branch a_value, rhs, false_block
rhs:
  b_value = lower(b)
  jump merge(b_value)
false_block:
  jump merge(false)
merge(result):
  ...
```

Block parameter 또는 phi를 지원하지 않으면 temporary local에 저장하는 형태로 낮출 수 있습니다.

## Statement와 expression result

AST expression이 value를 만들지만 statement position에서는 결과를 버립니다. Effect와 may-trap을 보존해야 합니다.

```text
call();      result unused but call remains
1 + 2;       pure result can later be removed
1 / x;       may trap, removal policy depends on language semantics
```

IR instruction property가 optimization 판단에 사용됩니다.

## Place와 value

Mutable assignment를 지원하려면 read value와 write location을 구분하는 것이 유용합니다.

```text
lower_value(expr) -> ValueId
lower_place(expr) -> Place(local slot, field, index, pointer...)
```

Mica core assignment target은 local symbol뿐이라 `StoreLocal`로 충분합니다. Field, array와 pointer가 추가되면 place abstraction이 중요해집니다.

## Source origin

각 instruction에 원래 AST node의 span을 붙일 수 있지만 다음 문제가 있습니다.

- 하나의 expression이 여러 instruction으로 낮아집니다.
- synthetic branch와 merge는 직접 source가 없습니다.
- 여러 source operation이 optimization으로 합쳐집니다.

```text
Origin
  Direct(span)
  Derived(parent_origin, reason)
  Merged(origins)
  None
```

Diagnostic에 사용할 primary origin과 debug step에 사용할 location은 요구가 다를 수 있습니다.

## IR builder와 well-formedness

Builder API가 invalid state를 줄입니다.

```text
block = builder.create_block()
builder.position_at(block)
value = builder.emit(...)
builder.terminate(...)
```

`emit`은 terminated block에서 실패하고 `terminate`는 두 번 호출할 수 없습니다. 그래도 외부 변환과 deserialization을 위해 독립 verifier를 둡니다.

## Lowering test

- AST input과 expected CFG shape
- block·edge·terminator invariant
- evaluation order가 있는 call fixture
- nested if/while의 edge
- return body 뒤 불필요한 jump가 없음
- source origin이 핵심 instruction에 남음
- interpreter와 unoptimized IR execution의 differential result

Exact block 번호 snapshot만 사용하면 harmless order 변경에 취약합니다. Graph invariant와 normalized dump를 함께 사용합니다.

## 대표 실패

- terminated block에 instruction을 추가합니다.
- if 한 branch가 return했는데 merge predecessor로 계속 포함합니다.
- short-circuit 오른쪽을 entry block에서 먼저 계산합니다.
- hash map iteration이 block order와 dump를 바꿉니다.
- mutable target을 value로만 낮춰 store 위치를 잃습니다.
- source origin을 모든 synthetic instruction에 같은 큰 span으로 붙입니다.

## 실습 연결

[IR와 pass exercise](../../exercises/05-ir-analysis-and-passes/README.md)에서 Mica AST 일부를 three-address CFG로 낮추고 verifier를 작성합니다. VM 경로만 선택한 학습자도 CFG dump와 all-path return 분석을 완료합니다.

## 점검 질문

1. AST와 CFG가 각각 잘 표현하는 정보는 무엇입니까?
2. basic block의 terminator invariant를 builder와 verifier에서 어떻게 나눕니까?
3. short-circuit expression의 결과 value를 merge에서 어떻게 만듭니까?
4. place와 value를 구분하지 않으면 assignment 확장에서 어떤 문제가 생깁니까?
5. exact text snapshot 외에 CFG를 어떤 invariant로 검사합니까?
