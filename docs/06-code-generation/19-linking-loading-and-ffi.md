# Linking, loading과 FFI

Compiler가 object를 만들거나 JIT code를 생성해도 외부 symbol, runtime library와 process address space에 연결되어야 실행됩니다. Linking·loading·FFI는 source type과 machine ABI 사이의 신뢰 경계입니다.

## 학습 목표

- declaration, definition, linkage와 visibility를 구분합니다.
- static link, dynamic link와 runtime symbol lookup의 차이를 설명합니다.
- FFI signature뿐 아니라 ownership·lifetime·error·thread 계약을 설계합니다.
- initialization order, callback과 re-entry의 실패를 다룹니다.

## Symbol

Source function 이름과 object symbol 이름은 다를 수 있습니다.

```text
source name
→ resolved SymbolId
→ mangled/linker name
```

Overload, namespace, generic specialization과 private symbol을 구분하려면 name mangling이 필요할 수 있습니다. Public C ABI를 제공하려면 stable unmangled wrapper를 사용할 수 있습니다.

Symbol property:

- declaration vs definition
- local/internal vs external linkage
- weak/strong 선택
- visibility
- version
- section과 address

같은 name의 여러 definition을 어떻게 처리하는지는 object format과 linker 규칙에 달려 있습니다.

## Static linking

여러 object와 archive에서 필요한 symbol을 선택하고 relocation을 적용해 executable 또는 library를 만듭니다.

Archive는 object 묶음이며 일반적으로 참조되는 member를 선택합니다. Link order가 unresolved symbol 결과에 영향을 주는 환경도 있으므로 build command를 재현 가능하게 기록합니다.

장점:

- 배포 dependency 감소
- runtime lookup 단순

비용:

- artifact 크기
- library update 시 재link
- 중복 code/data 가능

## Dynamic linking

Shared library는 load time 또는 runtime에 배치되고 symbol이 resolve됩니다.

고려:

- SONAME/install name와 search path
- symbol visibility와 interposition
- lazy/eager binding
- relocation과 position independence
- library version compatibility
- unload 가능 여부와 live pointer

“library 파일이 존재함”과 “process가 기대한 ABI version을 load함”은 다릅니다. 실제 loaded module과 symbol을 관찰합니다.

## Loader와 process state

OS loader는 executable·shared object를 address space에 map하고 relocation, TLS, initialization과 entry point를 준비합니다. 상세 policy는 `operating-systems`와 platform ABI 영역입니다.

Compiler/runtime 관점에서 확인할 것:

- entry function signature
- runtime startup 이전 global state
- module initializer 순서
- thread-local state
- exit handler와 cleanup

## Initialization order

여러 module의 global initializer가 서로 참조하면 order bug가 생깁니다.

선택:

- dependency graph 위상 순서
- lazy initialization과 once guard
- 명시적 runtime init function
- cycle 금지와 diagnostic

File/link order에 우연히 의존하지 않습니다. Initialization failure가 partial state를 남길 때 재시도·cleanup 정책을 정합니다.

## FFI contract

함수 signature만 같아서는 충분하지 않습니다.

```text
name/calling convention
argument와 return representation
ownership와 lifetime
nullability
alignment
string encoding
error channel
thread/re-entry 규칙
resource cleanup function
```

예:

```text
mica_string_from_utf8(ptr, len) -> Handle
```

질문:

- input bytes를 복사합니까, borrow합니까?
- invalid UTF-8은 어떻게 보고합니까?
- returned handle은 누가 언제 release합니까?
- GC가 object를 이동할 수 있습니까?
- function이 callback을 호출할 수 있습니까?

## String과 aggregate

C string은 NUL 종료이고 embedded NUL을 표현하기 어렵습니다. Source language string이 length를 갖는다면 pointer+length를 전달하거나 runtime handle을 사용합니다.

Struct layout은 field order, padding, alignment와 ABI classification에 의존합니다. Source struct를 host struct와 직접 공유하려면 `repr(C)` 같은 명시적 layout contract가 필요합니다.

## Error channel

FFI 실패 표현:

- sentinel return + last error
- status code + out parameter
- tagged result struct
- exception/unwind
- callback

Target exception을 C ABI 밖으로 그대로 던지지 않습니다. 언어 runtime과 native library가 같은 unwind model을 지원한다고 증명하지 못하면 boundary에서 catch/translate합니다.

## Callback과 re-entry

Native code가 target function callback을 보존해 나중에 호출할 수 있습니다.

필요한 상태:

- callback closure lifetime
- thread attach/runtime lock
- JIT code/resource lifetime
- exception translation
- callback 중 VM 재진입 가능 여부
- shutdown 뒤 호출 방지

Callback handle을 release했는데 native side가 계속 호출하면 use-after-free입니다.

## Thread safety

FFI function이 어떤 thread에서 호출될 수 있는지 정합니다. Runtime이 single-threaded라면 foreign callback을 queue로 전달하거나 global lock을 요구할 수 있습니다.

Native function이 blocking하면 GC safepoint, scheduler와 cancellation에 영향을 줍니다. `blocking` annotation이나 worker thread 정책을 둘 수 있습니다.

## Dynamic lookup

`dlopen`/`dlsym`류 API나 JIT symbol lookup은 문자열 symbol을 runtime에 resolve합니다. 실패를 구체적으로 구분합니다.

- module load 실패
- symbol 없음
- version mismatch
- signature mismatch는 lookup에서 감지되지 않을 수 있음
- unload 뒤 stale function pointer

Type checker가 문자열로 lookup한 native symbol의 실제 ABI를 증명하지 못하므로 manifest/binding generation과 runtime check를 사용합니다.

## Security 경계

FFI는 memory·filesystem·network 권한을 가진 native code로 이동합니다.

- allowlist된 library와 symbol
- path search 제한
- signed/pinned artifact
- sandbox process
- input length와 pointer validation
- capability handle

언어가 memory-safe하더라도 FFI가 전체 보장을 깨뜨릴 수 있습니다. 보안 설계는 [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)와 연결합니다.

## 대표 실패

- source string을 NUL-terminated C string으로 전달해 embedded NUL 뒤가 잘립니다.
- caller/callee가 ownership을 모두 가진다고 생각해 double free가 발생합니다.
- exception이 다른 unwind ABI 경계를 넘어갑니다.
- shared library unload 뒤 function pointer를 호출합니다.
- global initializer가 link order에 의존합니다.
- callback이 runtime 종료 뒤 closure를 사용합니다.
- symbol 이름이 같다는 이유로 signature도 같다고 가정합니다.

## 실습 연결

[Backend 경계 exercise](../../exercises/06-backend-boundaries/README.md)에서 C ABI builtin 하나의 manifest를 작성합니다. Pointer, length, ownership, error와 cleanup을 포함해야 합니다. 실제 native library 연결은 선택입니다.

## 점검 질문

1. source function name과 linker symbol name이 다른 이유는 무엇입니까?
2. FFI signature 외에 반드시 문서화할 lifetime 정보는 무엇입니까?
3. shared library unload가 live function/handle에 미치는 영향은 무엇입니까?
4. exception을 FFI boundary에서 번역해야 하는 이유는 무엇입니까?
5. memory-safe source language가 FFI 뒤에도 같은 안전성을 보장하지 못하는 이유는 무엇입니까?
