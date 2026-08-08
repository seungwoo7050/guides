# 프로세스, 시그널과 작업 제어

프로세스가 존재한다는 사실만으로 유용한 일을 하고 있다고 말할 수 없습니다. 실행 가능, 잠든 상태, 입력 대기, 자식 대기, 중지, 좀비와 종료를 구분하고, 누가 시작했고 누가 종료·회수할 책임을 갖는지 추적해야 합니다.

## 학습 목표

- 프로그램, 프로세스와 스레드를 구분합니다.
- PID, PPID, 프로세스 그룹과 세션의 역할을 설명합니다.
- 실행·대기·중지·좀비 상태를 관찰하고 과도하게 해석하지 않습니다.
- 부모가 자식 종료 상태를 회수해야 하는 이유를 설명합니다.
- 터미널의 포그라운드 프로세스 그룹과 작업 제어를 설명합니다.
- 시그널 전송, disposition, masking과 정상 종료 흐름을 구분합니다.
- wrapper가 자식에게 종료를 전달하지 않는 문제를 진단합니다.

## 선행 개념

- parent/child·FD 수명과 PID identity 재사용 가능성

## 프로세스 수명 모델

```text
프로그램 파일
   │ exec
   ▼
프로세스
├─ PID / PPID
├─ credentials
├─ current working directory
├─ environment
├─ virtual address space
├─ file descriptor table
├─ signal state
└─ one or more threads
       ├─ register state
       ├─ stack
       └─ scheduling state
```

프로세스 생성과 종료의 단순 모델:

```text
부모
  │ create/fork
  ├────────────► 자식
  │                 │ exec 가능
  │                 │ 실행·대기
  │                 │ exit 또는 signal
  │                 ▼
  └──────────── wait / status collection
```

구체적인 `fork`, `exec`, `wait` 구현은 `guide-c`가 담당합니다. 여기서는 관찰 가능한 수명과 책임을 다룹니다.

## 프로세스 식별

이름만으로 프로세스를 선택하지 않습니다. 같은 프로그램 인스턴스가 여러 개일 수 있습니다.

```sh
ps -eo pid=,ppid=,user=,state=,etime=,command=
```

현재 셸:

```sh
printf 'shell_pid=%s\n' "$$"
ps -p $$ -o pid=,ppid=,pgid=,sid=,state=,etime=,command=
```

플랫폼에 따라 지원하는 `ps` 열 이름이 다를 수 있습니다. 최소한 다음을 함께 확인합니다.

- PID와 PPID
- 사용자
- 시작 후 경과 시간
- 상태
- 전체 명령 줄
- 가능하면 프로세스 그룹과 세션

PID는 재사용될 수 있습니다. 오래 저장한 PID만으로 나중 프로세스의 정체성을 보장하지 않습니다. 시작 시각, 명령 줄, 사용자나 PID file의 안전한 생성 계약을 함께 봅니다.

## 상태는 단서이지 결론이 아니다

`ps` 상태 문자는 플랫폼마다 다르지만 보통 다음 종류를 구분합니다.

| 상태 | 의미의 예 |
|---|---|
| running/runnable | CPU에서 실행 중이거나 실행 가능 |
| sleeping/waiting | 이벤트, I/O, timer, lock 등을 기다림 |
| stopped | 작업 제어나 debugger로 중지 |
| zombie | 실행은 끝났고 부모의 상태 회수 대기 |

sleeping 상태 하나만으로 무엇을 기다리는지 확정할 수 없습니다. 다음 근거를 조합합니다.

```text
CPU 사용량
열린 FD와 대상
로그의 마지막 사건
자식 프로세스 상태
소켓·파일·FIFO 상태
시그널과 supervisor 상태
```

### 출력 없음과 hang

출력이 없는 프로세스는 다음 중 하나일 수 있습니다.

```text
정상적인 장기 대기
stdin 또는 FIFO 입력 대기
socket read/accept 대기
timer 대기
lock 또는 condition 대기
자식 종료 대기
계산 중
deadlock 또는 livelock
```

“hang”이라는 단어를 쓰기 전에 어떤 진행 조건이 충족되지 않는지 적습니다.

## 부모, 자식과 종료 상태

자식이 종료하면 부모가 결과를 회수할 때까지 커널은 최소 상태를 보존할 수 있습니다.

### 좀비

좀비는 코드를 실행하는 프로세스가 아닙니다. 이미 종료했지만 부모가 종료 상태를 회수하지 않은 항목입니다. 좀비 PID에 시그널을 보내는 것으로 해결하지 않습니다. 부모가 자식을 wait하도록 수명주기를 고칩니다.

### 고아와 남은 자식

부모가 먼저 종료하면 자식이 다른 회수 주체에게 인계될 수 있습니다. 백그라운드 작업이 의도된 경우도 있지만, wrapper가 종료됐는데 실제 서비스가 남았다면 감독과 종료 계약이 깨졌을 가능성이 큽니다.

관찰:

```sh
ps -eo pid=,ppid=,state=,etime=,command=
```

Linux에서는 `pstree`가 설치되어 있다면 관계를 보조적으로 볼 수 있고, macOS에서는 `ps`와 `pgrep -P`를 조합할 수 있습니다. 하나의 도구 출력에만 의존하지 않습니다.

## 프로세스 그룹, 세션과 터미널

셸의 작업 제어는 개별 PID보다 프로세스 그룹을 중심으로 동작합니다.

```text
terminal session
└─ shell
   ├─ foreground process group
   │  ├─ pipeline process A
   │  └─ pipeline process B
   └─ background process groups
```

`Ctrl+C`는 일반적으로 터미널의 포그라운드 프로세스 그룹에 `SIGINT`를 전달합니다. 키 입력이 특정 PID 하나에 직접 전달되는 것이 아닙니다.

```sh
sleep 60
# Ctrl+C
```

백그라운드 작업:

```sh
sleep 60 &
jobs -l
```

셸을 닫거나 터미널 연결이 사라질 때 자식에게 전달되는 사건은 셸, session, pseudo-terminal과 프로그램의 처리 방식에 따라 달라질 수 있습니다. 중요한 서비스는 대화형 셸의 우연한 수명에 맡기지 않고 감독자 아래에서 실행합니다.

## 시그널 모델

시그널은 프로세스나 스레드에 비동기 사건을 알리는 메커니즘입니다.

```text
sender
  │ kill/system event/terminal
  ▼
pending signal
  │ mask와 disposition 확인
  ├─ ignore
  ├─ default action
  └─ user handler
```

구분할 것:

- 시그널을 보냈는가
- 대상 PID나 process group이 맞는가
- 대상이 아직 존재하는가
- 시그널이 차단되어 pending 상태인가
- handler가 어떤 상태만 바꾸는가
- default action이 종료·중지·계속 중 무엇인가

`kill` 명령 이름은 오해를 부르지만 특정 시그널을 보내는 도구입니다.

```sh
kill -TERM PID
```

성공 반환은 커널이 전송 요청을 받아들였다는 의미이며 애플리케이션이 즉시 종료했음을 보장하지 않습니다.

## 정상 종료

장기 실행 프로세스의 권장 흐름:

```text
SIGTERM 또는 중지 요청
→ 종료 의도 기록
→ 새 작업 수락 중단
→ 진행 중 작업에 제한된 유예 시간
→ buffer·log flush
→ child·FD·socket 정리
→ 최종 상태 기록
→ 종료
```

복잡한 정리를 signal handler 안에서 직접 수행하면 재진입과 안전성 문제가 생길 수 있습니다. handler는 가능한 작은 상태 전환만 수행하고 주 반복문이 안전한 지점에서 정리하도록 설계합니다.

## wrapper와 시그널 전달

wrapper가 실제 작업 프로세스를 시작한 뒤 자신도 계속 존재하면 supervisor는 wrapper만 추적할 수 있습니다.

```text
supervisor
  │ SIGTERM
  ▼
wrapper
  └─ child service
```

wrapper가 시그널을 전달하지 않거나 child를 wait하지 않으면 다음이 생깁니다.

- supervisor는 종료됐다고 생각하지만 child가 남음
- grace period와 강제 종료가 잘못된 PID에 적용됨
- 종료 상태가 유실됨
- container PID 1이 zombie를 회수하지 못함
- listener나 열린 파일이 계속 유지됨

wrapper가 별도 작업이 필요 없다면 child로 `exec`해 PID와 시그널 경로를 단순화합니다. 여러 자식을 관리해야 한다면 명시적으로 process group, signal forwarding, wait와 timeout을 구현합니다.

## 관찰 순서

```text
1. 정확한 PID와 시작 시각을 확인합니다.
2. PPID, process group과 session을 확인합니다.
3. 상태·CPU·경과 시간을 기록합니다.
4. 열린 FD와 child를 확인합니다.
5. 어떤 사건을 기다리는지 가설을 적습니다.
6. 시그널을 보낼 경우 대상과 기대 상태 전이를 먼저 적습니다.
7. 종료 뒤 child, socket, file과 supervisor 상태를 모두 재검증합니다.
```

강제 종료 `SIGKILL`은 handler와 정리 경로를 실행하지 못합니다. 데이터 보존과 증거 수집이 필요한 경우 마지막 수단으로 사용합니다.

## 실습 연결

- `03-waiting-for-input`: 출력이 없는 프로세스가 FIFO 입력을 기다리는 상태를 확인합니다.
- `08-signal-not-forwarded`: wrapper 종료 후 child가 남는 상태를 확인합니다.

[시스템 조사 실습](../../exercises/system-investigation/README.md)

## 연결 실습

- [사례 03과 08](../../exercises/system-investigation/README.md)에서 대기 process와 signal wrapper 소유권을 추적합니다.

## 완료 기준

- PID와 프로그램 이름만으로 프로세스 정체성을 확정하면 안 되는 이유를 설명할 수 있습니다.
- zombie와 실행 중인 프로세스를 구분하고 올바른 수정 주체를 찾을 수 있습니다.
- `Ctrl+C`와 process group의 관계를 설명할 수 있습니다.
- `kill -TERM` 성공이 종료 완료를 보장하지 않는 이유를 설명할 수 있습니다.
- wrapper가 child에 시그널을 전달하고 wait해야 하는 이유를 설명할 수 있습니다.

다음 문서: [프로세스 메모리 관찰](02-process-memory-observation.md)
