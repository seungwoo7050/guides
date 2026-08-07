# 디버거 실전 참조: 가설을 실행 상태로 확인하기

GDB와 LLDB는 프로그램을 대신 이해해 주는 도구가 아닙니다. 소스에서 세운 가설을 실제 호출 스택, 변수, 메모리와 thread 상태로 확인하는 관찰 도구입니다. 무작정 한 줄씩 실행하기보다 **재현 입력 → 멈출 조건 → 확인할 불변식**을 먼저 정합니다.

## 조사 가능한 빌드를 만듭니다

```sh
cc -std=c99 -Wall -Wextra -Wpedantic \
    -g -O0 source.c -o program
```

- `-g`: source line, 변수와 type 같은 debug 정보를 넣습니다.
- `-O0`: 첫 조사에서 source와 실행 흐름의 차이를 줄입니다.
- warning은 디버거로 들어가기 전에 해결합니다.

최적화된 빌드에서는 변수가 제거되거나 register에만 남고, 함수가 inline되며, source 문장 순서와 실제 명령 순서가 달라 보일 수 있습니다. 결함이 `-O2`에서만 나타나면 실제 최적화 option으로도 다시 조사합니다. `-O0`에서 재현되지 않는다고 문제가 사라진 것은 아닙니다.

AddressSanitizer와 함께 debug 정보를 유지할 수도 있습니다.

```sh
cc -g -O1 -fsanitize=address,undefined \
    -fno-omit-frame-pointer source.c -o program
```

sanitizer가 잘못된 접근에 더 가까운 지점에서 중단하고, debugger가 해당 stack과 값을 보여 주는 역할을 합니다.

## 시작 명령

```sh
# GDB
gdb ./program

# LLDB
lldb ./program
```

명령행 인자를 넣어 실행합니다.

```text
GDB:  run input.txt 42
LLDB: run input.txt 42
```

shell redirection이 필요하면 debugger가 지원하는 실행 설정을 사용하거나 작은 fixture file을 argv로 넘기도록 프로그램을 설계합니다. 복잡한 quoting 때문에 재현 명령이 달라지지 않게 실제 사용한 명령을 기록합니다.

## 주요 명령 대응표

| 목적 | GDB | LLDB |
|---|---|---|
| 함수 breakpoint | `break main` | `breakpoint set -n main` |
| 파일·줄 breakpoint | `break file.c:42` | `breakpoint set -f file.c -l 42` |
| 실행 | `run a b` | `run a b` |
| 다시 시작 | `run` | `run` |
| 다음 source 줄 | `next` | `next` |
| 함수 안으로 | `step` | `step` |
| 현재 함수 끝까지 | `finish` | `finish` |
| 계속 실행 | `continue` | `continue` |
| 현재 위치 | `list` | `source list` |
| 변수 출력 | `print value` | `frame variable value` |
| 임의 식 평가 | `print *pointer` | `expression -- *pointer` |
| 호출 stack | `backtrace` | `bt` |
| 모든 thread stack | `thread apply all bt` | `thread backtrace all` |
| frame 선택 | `frame 2` | `frame select 2` |
| breakpoint 목록 | `info breakpoints` | `breakpoint list` |
| breakpoint 삭제 | `delete 1` | `breakpoint delete 1` |
| register | `info registers` | `register read` |
| 종료 | `quit` | `quit` |

명령 이름과 세부 출력은 버전에 따라 다를 수 있습니다. 설치된 debugger의 `help`가 기준입니다.

## breakpoint는 질문을 표현합니다

`main`에 무조건 멈춘 뒤 끝까지 step하면 잡음이 큽니다. 다음과 같은 질문을 breakpoint로 바꿉니다.

```text
이 함수가 잘못된 length를 받는 순간은 언제인가?
vector 불변식이 깨진 첫 호출은 무엇인가?
두 번째 fork 실패 정리 경로에 들어오는가?
오류 뒤 output parameter를 쓰는 문장이 실행되는가?
```

GDB:

```text
break vector_push
break parser.c:180
```

LLDB:

```text
breakpoint set -n vector_push
breakpoint set -f parser.c -l 180
```

breakpoint에 도달할 때마다 자동 명령을 실행하거나 특정 횟수는 무시할 수도 있지만, 처음에는 조건을 단순하게 유지합니다.

## 조건부 breakpoint

수천 번 반복 중 경계가 깨지는 순간에만 멈춥니다.

GDB:

```text
break vector.c:80 if index >= vector->length
break account.c:120 if source->balance < 0
```

LLDB:

```text
breakpoint set -f vector.c -l 80 -c 'index >= vector->length'
breakpoint set -f account.c -l 120 -c 'source->balance < 0'
```

조건식 자체가 잘못된 포인터를 역참조하면 debugger evaluation도 실패할 수 있습니다. 먼저 포인터와 객체 수명을 확인합니다.

## 호출 stack과 frame

crash 또는 breakpoint에서:

```text
GDB:  backtrace
LLDB: bt
```

stack의 각 frame은 “현재 함수가 누구에게 어떤 인자로 호출됐는가”를 보여 줍니다.

```text
frame 0  실제 fault가 발생한 함수
frame 1  잘못된 인자를 전달한 호출자일 수 있음
frame N  외부 API 진입점과 입력
```

크래시 위치가 원인 위치와 같다는 보장은 없습니다. 이전의 out-of-bounds write가 allocator metadata를 손상하고 나중 `free`에서 crash할 수 있습니다. stack을 위로 따라가며 값이 처음 계약을 벗어난 지점을 찾습니다.

## 변수와 불변식을 함께 봅니다

단일 변수만 출력하기보다 객체 불변식을 한 묶음으로 확인합니다.

```text
print vector->data
print vector->length
print vector->capacity
print vector->length <= vector->capacity
```

```text
print reader->pending
print reader->length
print reader->capacity
print reader->eof
print reader->failed
```

질문 예:

- 이 포인터는 NULL입니까?
- 그 객체의 수명은 아직 유효합니까?
- index가 length보다 작습니까?
- 출력 매개변수는 성공 전 변경됐습니까?
- FD 소유 상태와 실제 정수 값이 일치합니까?
- mutex를 보유해야 읽을 수 있는 값을 무잠금으로 보고 있습니까?

디버거로 값을 읽는다고 동시성 계약이 자동으로 안전해지는 것은 아닙니다. thread가 실행 중이면 snapshot이 바뀔 수 있으므로 process를 멈춘 상태와 lock 관계를 함께 봅니다.

## 포인터와 메모리 관찰

GDB:

```text
print pointer
print *pointer
x/16xb pointer
x/8wd values
x/s text
```

LLDB:

```text
frame variable pointer
expression -- *pointer
memory read --format x --size 1 --count 16 pointer
memory read --format d --size 4 --count 8 values
memory read --format c --size 1 text
```

메모리 출력 형식과 element size가 실제 type과 맞는지 확인합니다. 임의 주소를 읽는 명령도 유효하지 않은 메모리에 접근하면 실패합니다.

문자열을 `x/s`로 보는 것은 NUL 종료가 보장될 때만 의미가 있습니다. 포함된 NUL이 있는 buffer는 명시적 길이만큼 byte로 관찰합니다.

## segmentation fault 조사 순서

```sh
gdb ./program
(gdb) run failing-input
(gdb) backtrace
(gdb) frame 0
(gdb) print pointer
(gdb) print length
```

질문 순서:

1. 어떤 signal과 문장에서 멈췄습니까?
2. 해당 주소를 만든 함수는 어디입니까?
3. 포인터가 가리키던 객체의 수명은 아직 유효합니까?
4. index·length·capacity 계약은 무엇입니까?
5. 같은 포인터를 이전에 `free`한 경로가 있습니까?
6. 반환된 지역 변수 주소나 성장 전 내부 포인터를 보관했습니까?
7. 잘못된 write가 crash보다 앞서 발생했을 가능성이 있습니까?

AddressSanitizer가 제공한 allocation/free stack이 있다면 debugger stack과 함께 봅니다.

## watchpoint: 누가 값을 바꾸는가

GDB:

```text
watch vector->length
continue
```

LLDB:

```text
watchpoint set expression -- &vector->length
continue
```

watchpoint는 메모리 위치가 읽히거나 쓰일 때 멈추게 할 수 있습니다. hardware watchpoint 수는 제한되고, 동적 객체가 이동하거나 해제되면 감시 주소가 더 이상 같은 논리 객체를 뜻하지 않을 수 있습니다.

`realloc` 전후 내부 주소가 바뀌는 자료구조에서는 새 주소에 watchpoint를 다시 설정합니다.

## 함수 반환과 실패 경로

오류 처리 함수를 조사할 때 성공 경로만 step하지 않습니다.

```text
break allocator_fail_point
run failing-case
next
print object->length
print object->data
finish
print result
```

확인할 것:

- 실패 전 확보한 자원이 정리됩니까?
- 출력 매개변수는 commit 전 값입니까?
- 객체 불변식이 유지됩니까?
- terminal failed 상태가 설정됩니까?
- 호출자가 같은 객체를 destroy할 수 있습니까?

`finish`는 현재 함수 반환까지 실행하고 반환값을 보여 줄 수 있습니다. 최적화와 ABI에 따라 표시 방식이 달라질 수 있습니다.

## thread 조사

GDB:

```text
info threads
thread 3
thread apply all bt
```

LLDB:

```text
thread list
thread select 3
thread backtrace all
```

deadlock 조사:

1. 모든 thread stack을 출력합니다.
2. 각 thread가 어떤 mutex 또는 condition에서 기다리는지 봅니다.
3. 그 lock을 보유한 thread stack을 찾습니다.
4. lock 획득 순서가 전역 규칙과 같은지 확인합니다.
5. condition wait의 predicate를 다시 검사합니다.

모든 thread가 `pthread_mutex_lock` 안에 있다고 mutex 구현 내부를 분석하기 전에 프로그램의 lock order graph를 그립니다.

데이터 경쟁은 debugger single-step으로 사라질 수 있습니다. ThreadSanitizer와 barrier 기반 재현 테스트를 함께 사용합니다.

## thread별 breakpoint와 scheduler 영향

breakpoint가 process 전체를 멈출지 특정 thread만 멈출지는 debugger와 설정에 따라 다릅니다. 한 thread만 멈추고 다른 thread가 계속 실행하면 공유 상태가 변할 수 있습니다. 반대로 전체를 멈추면 실제 timing이 크게 달라집니다.

동시성 결함을 debugger에서 재현하지 못했다고 안전하다고 결론 내리지 않습니다. debugger는 특정 interleaving의 관찰 도구입니다.

## `fork`와 여러 process 조사

GDB 예:

```text
set follow-fork-mode child
set detach-on-fork off
```

- `follow-fork-mode parent|child`: 어느 process를 따라갈지 정합니다.
- `detach-on-fork off`: 다른 쪽을 즉시 분리하지 않게 할 수 있습니다.

LLDB의 fork·vfork 지원은 플랫폼별 차이가 큽니다. 다음 수단을 함께 사용합니다.

- child 전용 작은 helper
- stderr 또는 오류 pipe 진단
- PID와 FD를 포함한 구조화된 log
- `strace`, `ktrace`, `dtruss` 같은 OS별 syscall 도구
- 자동 timeout과 process group 정리

`fork` 뒤 child에서 breakpoint를 걸었을 때 parent가 wait 중인지, pipe를 누가 열고 있는지도 함께 봅니다.

## exec 뒤 breakpoint

`exec` 성공 뒤 프로그램 이미지가 바뀌므로 새 executable의 symbol을 debugger가 어떻게 따라가는지 확인합니다. 실행 대상 helper에 직접 debugger를 붙여 argv·상태 계약을 먼저 검증하는 편이 단순할 수 있습니다.

exec 실패 경로는 새 이미지로 바뀌지 않으므로 child의 `_exit(126/127)` 직전 breakpoint를 걸어 `errno`와 열린 FD를 확인합니다.

## signal 조사

GDB와 LLDB는 특정 signal을 debugger가 멈춰 잡을지 프로그램에 전달할지 설정할 수 있습니다.

GDB 예:

```text
handle SIGUSR1 nostop noprint pass
handle SIGTERM stop print pass
```

LLDB 예:

```text
process handle SIGUSR1 --stop false --notify false --pass true
```

debugger가 signal을 가로채면 프로그램 handler가 예상 시점에 실행되지 않을 수 있습니다. self-pipe 테스트를 조사할 때 debugger signal policy를 기록합니다.

handler 안에서 step하면 timing과 async context가 크게 변합니다. handler를 작게 유지하고 일반 event loop의 사건 처리 함수에 breakpoint를 거는 편이 좋습니다.

## core dump

운영체제 설정이 허용하면 비정상 종료 상태를 core file로 남길 수 있습니다.

```sh
ulimit -c unlimited
./program failing-input
```

GDB:

```sh
gdb ./program core
```

LLDB는 platform별 core 명령과 파일 형식이 다를 수 있습니다.

core dump에서 확인할 수 있는 것:

- 종료 signal
- 당시 thread stack
- register와 메모리
- 일부 전역·지역 변수

실행 중 외부 상태 변화와 모든 log가 포함되는 것은 아닙니다. 실행 파일과 debug symbol이 core 생성 시점의 build와 정확히 일치해야 합니다.

core file에는 비밀번호, token, 개인정보와 입력 데이터가 포함될 수 있으므로 보관·전송·삭제 정책이 필요합니다.

## shared library와 symbol

debugger가 함수 이름을 찾지 못하면 다음을 확인합니다.

- 실행 파일과 library에 debug 정보가 있습니까?
- symbol이 strip됐습니까?
- 실제 load된 library가 예상 버전입니까?
- source path가 build 환경과 달라졌습니까?
- 함수가 inline 또는 최적화로 제거됐습니까?

`info sharedlibrary` 또는 LLDB의 image list 계열 명령으로 load된 module을 확인할 수 있습니다.

## debugger가 코드를 바꿀 수 있다는 점

식 평가 명령은 단순 관찰만 하는 것이 아닐 수 있습니다.

```text
GDB:  call function()
LLDB: expression -- function()
```

이 명령은 실제 함수를 호출해 전역 상태, lock, I/O와 heap을 변경할 수 있습니다. 조사 대상 프로그램에 새로운 부수효과를 넣지 않도록 읽기 식 위주로 사용합니다.

변수 값을 강제로 바꾸는 기능도 가설 실험에는 유용하지만, 그렇게 통과한 실행은 원래 프로그램의 증거가 아닙니다.

## sanitizer와 debugger의 역할 분리

| 도구 | 강점 | 한계 |
|---|---|---|
| compiler warning | 정적 type·format·제어 흐름 진단 | 실행 상태를 모름 |
| ASan | 잘못된 heap/stack 접근과 use-after-free 관찰 | 실행한 경로만 봄 |
| UBSan | 일부 undefined behavior 관찰 | 모든 UB를 잡지 않음 |
| TSan | 실행한 경로의 data race 관찰 | 논리적 deadlock·불변식은 별도 |
| debugger | 특정 시점의 stack·값·메모리 확인 | timing을 바꾸고 자동 증명이 아님 |
| test | 공개 계약과 회귀 검증 | 작성한 사례에 한정 |

한 도구의 통과를 다른 도구의 역할로 확대 해석하지 않습니다.

## 조사 기록

다음 항목만 기록해도 재현성이 크게 좋아집니다.

```text
기준 commit과 compiler version
빌드 명령과 option
실행 명령, 환경과 입력
예상 결과와 실제 결과
멈춘 signal·위치·thread
관찰한 변수와 불변식
반증된 가설
수정 내용
수정 뒤 재실행한 test·sanitizer
```

재현 입력이 임시 파일이라면 가능한 범위에서 fixture로 보존합니다. 개인정보나 비밀값은 제거합니다.

## 권장 조사 순서

1. warning 없이 같은 build를 재현합니다.
2. 실패 입력과 종료 상태를 자동 test로 고정합니다.
3. sanitizer가 해당 결함에 적합하면 먼저 실행합니다.
4. crash 또는 불변식 위반 직전에 breakpoint를 둡니다.
5. stack을 확인하고 한 frame씩 입력의 출처를 추적합니다.
6. pointer·length·capacity·소유 상태를 함께 봅니다.
7. 수정 뒤 원래 실패 사례뿐 아니라 전체 회귀 test를 실행합니다.
8. 다른 compiler와 최적화 build에서도 확인합니다.

디버거 session에서 우연히 원인을 찾았더라도 최종 완료 조건은 재현 가능한 test가 같은 결함의 재발을 막는 것입니다.
