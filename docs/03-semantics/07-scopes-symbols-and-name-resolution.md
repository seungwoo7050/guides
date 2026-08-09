# Scope, symbol과 name resolution

Identifier text가 같다고 같은 대상을 뜻하지 않습니다. Name resolution은 source의 문자열 이름을 선언 identity에 연결하고, shadowing·visibility·module 경계를 결정합니다. 이 결과가 type checking, rename, closure capture와 code generation의 기반입니다.

## 학습 목표

- scope, declaration, symbol과 reference를 구분합니다.
- lexical scope와 declaration order를 명시적으로 모델링합니다.
- shadowing, duplicate와 unknown name을 서로 다른 오류로 처리합니다.
- module graph와 cycle이 single-file resolution을 어떻게 확장하는지 설명합니다.

## 문자열 이름과 symbol identity

```text
let x: Int = 1;
{
    let x: Int = 2;
    print_int(x);
}
```

두 `x` declaration은 text가 같지만 다른 symbol입니다.

```text
SymbolId(17): outer x
SymbolId(23): inner x
```

Reference는 name string이 아니라 `SymbolId`를 가리켜야 합니다. Rename은 같은 text 전체를 바꾸는 것이 아니라 해당 symbol의 declaration과 resolved reference만 수정합니다.

## Scope는 visible binding 집합입니다

Lexical block language의 scope chain:

```text
module scope
  └─ function scope
       └─ block scope
            └─ nested block scope
```

Lookup:

1. 현재 scope에서 이름을 찾습니다.
2. 없으면 parent scope로 이동합니다.
3. root까지 없으면 unknown name입니다.

같은 scope의 중복과 child scope의 shadowing은 다른 규칙입니다.

```text
let x = 1;
let x = 2;       같은 scope 중복: 보통 오류

let x = 1;
{ let x = 2; }   child shadowing: 정책에 따라 허용
```

Shadowing을 허용해도 warning을 제공할 수 있습니다. 경고는 의미 규칙과 분리합니다.

## Declaration order

언어마다 이름이 언제 visible한지 다릅니다.

```text
let x = x + 1;
```

가능한 정책:

- initializer에서는 새 `x`가 보이지 않아 outer `x`를 찾음
- declaration 시작부터 보이지만 초기화 전 사용 오류
- 자기 참조를 무조건 금지

Function forward reference도 정해야 합니다.

```text
fn first() -> Int { return second(); }
fn second() -> Int { return 2; }
```

Mica는 모든 top-level function signature를 먼저 수집해 순서와 무관하게 서로 호출할 수 있게 합니다. Local variable은 declaration statement가 끝난 뒤 visible합니다.

## 두 단계 resolution

Top-level function을 지원하는 단순 구조:

### Pass 1: declaration collection

- 모든 function 이름과 signature syntax를 module scope에 등록
- 중복 이름 진단
- stable SymbolId 할당

### Pass 2: body resolution

- parameter와 local scope 생성
- NameExpr와 CallExpr reference 연결
- unknown name과 duplicate local 진단
- closure를 지원하면 capture 기록

한 pass에서 function body를 바로 읽으면 뒤에 선언된 함수 호출을 지원하기 어렵습니다.

## Namespace

일부 언어는 type, value, label, module 이름을 다른 namespace로 둡니다.

```text
struct User { ... }
fn User() { ... }
```

허용 여부는 namespace 정책에 달려 있습니다. 모든 symbol을 하나의 map에 넣으면 언어가 의도하지 않은 충돌을 만들 수 있습니다.

Mica core는 type name이 고정 builtin이고 사용자 declaration은 value/function namespace 하나를 공유합니다. 확장 언어에서 user type을 추가할 때 namespace를 다시 설계합니다.

## Symbol data

```text
Symbol
  id
  name
  kind: function | parameter | local | builtin
  declaration_span
  owner_scope
  visibility
  mutable
  declared_type_syntax
```

Type checker가 만든 `TypeId`를 symbol에 직접 저장할 수도 있지만 phase invalidation을 고려합니다. Declaration syntax와 resolved type을 분리하면 cycle과 오류를 다루기 쉽습니다.

## Error symbol

Unknown name마다 `None`을 반환하면 후속 code가 반복해서 분기합니다. `ErrorSymbol`을 사용할 수 있습니다.

```text
resolve("missing")
→ diagnostic E2001
→ ErrorSymbol(origin=diagnostic_id)
```

Type checker는 ErrorSymbol reference를 ErrorType으로 바꾸고 같은 원인의 추가 오류를 억제합니다. ErrorSymbol을 global table에 정상 declaration처럼 등록하지 않습니다.

## Closure capture

Nested function이 outer local을 사용하면 lexical reference가 frame lifetime을 넘어갈 수 있습니다.

```text
fn make_counter() -> Fn {
    var count: Int = 0;
    fn next() -> Int {
        count = count + 1;
        return count;
    }
    return next;
}
```

Resolution은 `count`가 local이 아니라 captured symbol임을 표시합니다. Runtime은 stack slot을 그대로 가리킬 수 없으며 cell/upvalue/environment object로 승격해야 할 수 있습니다.

Capture mode도 정합니다.

- by value
- by reference/cell
- mutable capture
- move capture

Mica core는 nested function과 closure를 필수 문법에 포함하지 않지만 [함수와 closure 문서](../04-execution/11-functions-closures-and-runtime-errors.md)에서 선택 확장으로 구현합니다.

## Module graph

여러 파일을 지원하면 resolution은 graph 문제가 됩니다.

```text
parse all module headers
→ module/import graph
→ export table
→ cycle policy
→ body resolution
```

Cycle을 무조건 금지할 수도 있고 signature cycle은 허용하되 initialization cycle만 금지할 수도 있습니다. File traversal order에 따라 결과가 달라지지 않게 deterministic symbol ordering을 둡니다.

Import alias, wildcard import와 re-export는 name ambiguity를 만들 수 있습니다. 어떤 declaration이 선택되었는지 secondary diagnostic에 후보를 제시합니다.

## Rename과 reference index

LSP rename을 위해 resolution 결과에서 다음을 유지합니다.

```text
SymbolId → declaration span
SymbolId → reference span 목록
```

새 이름이 각 reference 위치의 scope에서 다른 symbol과 충돌하는지 미리 검사합니다. 문자열 치환은 comment·string·다른 scope의 동명 symbol까지 바꾸므로 사용하지 않습니다.

## 대표 실패

- symbol table key만 저장하고 declaration identity를 잃습니다.
- scope exit에서 binding을 제거하지 않아 sibling block에서 이름이 보입니다.
- initializer에 local을 너무 일찍 등록해 자기 참조 정책이 우연히 정해집니다.
- hash map 순서에 따라 duplicate diagnostic 순서가 바뀝니다.
- unresolved name을 runtime global lookup으로 미뤄 static language contract가 약해집니다.
- closure가 stack frame 종료 뒤 dangling slot을 가리킵니다.

## 실습 연결

[Resolution·type·flow exercise](../../exercises/03-resolution-types-and-flow/README.md)에서 scope stack, two-pass function collection과 symbol reference dump를 구현합니다. 같은 이름의 shadowing fixture가 서로 다른 SymbolId를 가리키는지 검사합니다.

## 점검 질문

1. declaration text와 SymbolId를 분리해야 하는 이유는 무엇입니까?
2. local 이름은 initializer의 어느 시점부터 visible합니까?
3. top-level forward call을 지원하려면 몇 단계가 필요합니까?
4. ErrorSymbol은 어디에 저장하고 언제 버립니까?
5. rename이 안전한지 어떤 scope 충돌을 검사합니까?
