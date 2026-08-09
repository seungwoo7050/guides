# Control flow, definite assignment와 effect

Tree 구조만 보면 statement의 중첩은 알 수 있지만 실제로 어떤 경로가 다음 문장에 도달하는지는 명확하지 않습니다. Return, loop, short-circuit, break와 예외를 다루려면 control-flow graph와 경로별 fact가 필요합니다.

## 학습 목표

- AST에서 basic block과 control-flow edge를 구성합니다.
- reachability, all-path return과 definite assignment를 data-flow 문제로 표현합니다.
- short-circuit와 loop의 평가 순서를 graph에 보존합니다.
- 순수 계산과 외부 effect를 optimization·tooling 경계에서 구분합니다.

## Tree에서 graph로 이동합니다

다음 함수를 생각합니다.

```text
fn choose(flag: Bool) -> Int {
    if flag {
        return 1;
    }
    return 2;
}
```

CFG:

```text
entry
  ├─true→ then(return 1) → exit
  └─false→ after_if(return 2) → exit
```

Basic block은 중간 분기 없이 순차 실행되는 instruction/statement 묶음이고 마지막에는 terminator가 있습니다.

```text
jump
conditional branch
return
unreachable/trap
```

Block에 terminator가 없거나 terminator 뒤 instruction이 있으면 verifier가 거부합니다.

## Reachability

`return` 뒤 statement는 실행되지 않습니다.

```text
return 1;
print_int(2);   // unreachable
```

정책 선택:

- error로 거부
- warning만 출력
- 허용하되 IR에서는 제거

무엇을 선택하든 parser가 아니라 flow phase가 판정합니다. Constant condition을 고려할지 범위도 정합니다.

```text
if false { ... }
```

Constant propagation 전에는 두 edge를 모두 reachable로 볼 수 있고, 간단한 constant evaluator 뒤 하나를 제거할 수 있습니다.

## 모든 경로에서 return

Return type이 `Unit`이 아닌 함수는 모든 reachable path가 값을 반환해야 합니다.

```text
fn f(flag: Bool) -> Int {
    if flag { return 1; }
    // false path는 함수 끝에 도달
}
```

함수 exit block으로 normal edge가 들어오면 missing return입니다. Syntax tree의 마지막 statement만 확인하면 nested branch와 loop에서 틀릴 수 있습니다.

무한 loop를 “절대 끝나지 않음”으로 인정할지는 언어 규칙과 분석 능력에 달려 있습니다. `while true`라도 body에 break가 있거나 runtime condition이 바뀔 수 있습니다. 증명하지 못하면 보수적으로 exit 가능성을 유지합니다.

## Definite assignment

초기화되지 않은 local 읽기를 금지하는 언어를 생각합니다.

```text
var x: Int;
if flag { x = 1; }
print_int(x);  // flag=false 경로에서는 미할당
```

Forward data-flow fact:

```text
IN(block)  = predecessor OUT의 교집합
OUT(block) = transfer(block, IN(block))
```

“모든 경로에서 할당됨”은 meet가 intersection입니다. 하나의 predecessor라도 할당하지 않으면 definitely assigned가 아닙니다.

Mica core는 `var`에도 initializer를 요구해 필수 경로에서는 이 분석을 단순화합니다. Exercise에서는 initializer 없는 확장을 사용해 data-flow를 구현합니다.

## Loop와 fixed point

Loop back-edge 때문에 block fact가 한 번에 정해지지 않습니다.

```text
entry → header → body ─┐
          └→ exit      │
               header ←┘
```

Worklist algorithm으로 fact가 더 이상 변하지 않을 때까지 반복합니다. Lattice 높이와 monotone transfer가 종료 근거입니다. 단순히 block을 source 순서로 한 번 방문하면 loop-carried fact를 놓칩니다.

[`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms)가 graph와 fixed-point 자체를 소유합니다. 여기서는 compiler fact의 의미와 보수성을 적용합니다.

## Short-circuit

```text
left && right
```

`left`가 false면 `right`를 평가하지 않습니다. AST lowering은 이를 단순 `AND` instruction으로 바꾸기 전에 effect를 확인해야 합니다.

```text
left
  ├─false→ result_false
  └─true→ evaluate_right
```

`right`에 함수 호출이나 assignment가 있으면 eager evaluation으로 바꾸면 의미가 달라집니다.

## Effect

Expression이 할 수 있는 일을 분류하면 optimization과 tooling이 안전해집니다.

예:

- pure: 같은 입력에서 값만 계산
- may trap: division, checked overflow
- reads state: variable, memory, clock
- writes state: assignment, I/O
- calls unknown: 외부 함수
- diverges: 종료하지 않을 수 있음

`1 / x`는 값을 사용하지 않아도 `x == 0`일 때 trap합니다. Dead code elimination이 결과가 unused라는 이유만으로 제거하면 runtime semantics가 바뀝니다.

Effect system 전체를 구현하지 않더라도 IR instruction에 `has_side_effect`, `may_trap` 같은 property를 명시할 수 있습니다.

## Exception과 cleanup

Exception을 지원하면 CFG에 normal edge와 exceptional edge가 생깁니다. `finally`, defer, destructor와 resource cleanup이 있으면 return·break·error마다 cleanup block을 지나야 합니다.

```text
open resource
try body
  ├─normal→ cleanup→next
  └─throw → cleanup→handler
```

Mica core는 exception을 지원하지 않으며 runtime error는 프로그램 실행을 중단합니다. C++/LLVM 확장에서는 unwind와 cleanup pad를 별도로 공부합니다.

## Pattern exhaustiveness

Sum type과 pattern match가 있는 언어에서는 모든 variant를 처리하는지 분석합니다. 단순 enum은 set subtraction으로 가능하지만 nested pattern과 guard는 matrix 기반 분석이 필요할 수 있습니다. 이 가이드의 확장 주제입니다.

## 대표 실패

- AST 마지막 node만 보고 all-path return을 판정합니다.
- loop를 한 번만 순회해 definite assignment fact를 놓칩니다.
- `&&`를 eager binary operation으로 낮춰 오른쪽 effect를 항상 실행합니다.
- may-trap instruction을 pure로 표시해 제거합니다.
- unreachable diagnostic이 error recovery node 뒤에서 폭발적으로 늘어납니다.
- exceptional edge를 빼고 resource cleanup이 누락됩니다.

## 실습 연결

[Resolution·type·flow exercise](../../exercises/03-resolution-types-and-flow/README.md)와 `examples/dataflow-fixed-point`에서 definite assignment를 worklist로 계산합니다. [IR exercise](../../exercises/05-ir-analysis-and-passes/README.md)에서는 같은 CFG를 lowering과 optimization의 입력으로 사용합니다.

## 점검 질문

1. all-path return을 함수 마지막 statement만으로 판단할 수 없는 이유는 무엇입니까?
2. definite assignment의 merge가 합집합이 아니라 교집합인 이유는 무엇입니까?
3. short-circuit를 CFG에서 어떻게 표현합니까?
4. 사용되지 않는 `1 / x`를 제거해도 되는 조건은 무엇입니까?
5. loop data-flow가 종료한다는 근거는 무엇입니까?
