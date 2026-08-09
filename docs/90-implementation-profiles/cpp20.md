# C++20 구현 프로필

C++20 프로필은 object lifetime, explicit ownership, sum type와 build boundary를 언어 구현에 적용합니다. C++ 문법과 RAII 자체는 [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp)가 소유합니다.

## 권장 toolchain

- C++20 compiler
- CMake target 기반 build
- warning을 project code에 적용
- ASan/UBSan 선택, VM/parallel code에는 TSan 선택
- test framework는 project 정책에 맞춤

LLVM profile을 사용하지 않는 core 구현은 외부 package 없이 만들 수 있습니다.

## Source lifetime

`std::string_view` lexeme는 source buffer보다 오래 살 수 없습니다.

```text
SourceManager owns std::string/byte buffer
Token stores SourceId + offsets
lexeme is computed as view when needed
```

Token이 temporary input string의 view를 보관하지 않게 합니다. Incremental snapshot을 사용하면 version별 buffer owner가 node보다 오래 살아야 합니다.

## AST 표현

선택 1: `std::variant`

```cpp
using Expr = std::variant<IntExpr, NameExpr, BinaryExpr, CallExpr, ErrorExpr>;
```

- exhaustive visitor helper 필요
- recursive type는 `unique_ptr`, arena handle 또는 index 사용

선택 2: class hierarchy

- virtual dispatch/visitor
- allocation과 ownership 명확화

Arena + NodeId를 사용하면 tree move와 side table key를 안정화할 수 있습니다. Raw pointer를 소유권 표기로 사용하지 않습니다.

## Symbol과 type interning

```text
SymbolId = integer index into SymbolArena
TypeId   = integer index into TypeInterner
```

Interned structural type은 equality를 빠르게 하지만 interner lifetime과 thread safety를 명시합니다. Source-level alias와 canonical type identity를 분리합니다.

## 오류 전달

사용자 diagnostic은 collection에 추가하고 정상 control flow로 반환합니다. I/O/build 실패에는 `std::expected` 사용 가능 여부에 따라 project result type 또는 variant를 사용합니다. Exception policy를 문서화합니다.

- parser recovery를 exception unwinding 전체에 맡기지 않음
- internal invariant는 assertion 또는 typed internal error
- FFI/LLVM exception boundary를 명시

## Memory

- AST/IR: arena 또는 `unique_ptr`
- runtime object: 별도 heap/GC/RC 정책
- `shared_ptr`를 기본 해결책으로 사용하지 않음
- closure cycle과 ownership graph 문서화

Polymorphic allocator/PMR는 측정 후 도입합니다.

## Visitor와 phase 분리

AST node에 `typecheck()`, `emit()`, `format()`을 모두 넣으면 phase dependency가 커집니다. 별도 visitor/service와 side table을 권장합니다.

```text
SyntaxArena
Resolver
TypeChecker
Interpreter
Lowering
Formatter
```

## VM

- `std::variant` 또는 tagged union Value
- opcode decode 범위 검사
- `std::vector<Value>` operand/local stack
- frame base를 index로 저장해 vector reallocation pointer invalidation 방지
- checked integer helper
- instruction budget

## Build target

```text
mica_core      source/diagnostic/syntax/semantic
mica_runtime   interpreter/VM
mica_cli
mica_tests
```

LLVM adapter는 별도 target과 option으로 분리해 core build의 필수 dependency가 되지 않게 합니다.

## Sanitizer와 warning

- source span overflow/underflow
- dangling `string_view`
- arena lifetime
- VM stack out-of-bounds
- signed overflow에 host UB 사용
- use-after-free closure

C++ signed overflow는 target Mica의 checked runtime error로 자동 대응하지 않습니다. 연산 전에 안전한 check 또는 wider/unsigned 계산을 사용합니다.

## Determinism

`unordered_map` iteration을 diagnostic/symbol/IR output 순서로 사용하지 않습니다. Stable vector index와 정렬된 view를 둡니다.

## 완료 근거

- Debug/Release 모두 같은 conformance result
- sanitizer가 지원되는 환경에서 core fixture 통과
- compiler 선택 차이에서 public output 안정
- source snapshot 파괴 뒤 token/AST가 dangling view를 갖지 않음
- known-bad VM offset이 verifier에 거부됨
