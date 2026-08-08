# 서비스 감독, 로그와 준비 상태

장기 실행 프로세스에는 시작, 준비, 요청 처리, 정상 종료와 복구라는 수명주기가 있습니다. supervisor나 container runtime이 프로세스를 실행해도 애플리케이션의 준비 상태와 업무 정상성을 대신 보증하지는 않습니다.

## 학습 목표

- 시작됨, 실행 중, 준비됨과 정상 상태를 구분합니다.
- foreground 프로세스와 supervisor의 책임을 설명합니다.
- 실행 파일, 설정, 비밀값, 영속 데이터, 런타임 상태와 로그를 구분합니다.
- 작업 디렉터리·환경·사용자·FD가 서비스 실행 문맥임을 확인합니다.
- 로그를 시간축 근거로 수집하고 민감 정보를 노출하지 않습니다.
- graceful shutdown과 강제 종료의 차이를 설명합니다.
- restart loop, stale wrapper와 readiness 실패를 별도 문제로 진단합니다.

## 선행 개념

- process·signal·endpoint 관찰과 running/listening/ready/healthy 구분

## 서비스 수명 모델

```text
서비스 정의
├─ executable와 arguments
├─ working directory
├─ user/group
├─ environment/configuration
├─ resource limits
├─ restart policy
└─ stop timeout
        │
        ▼
supervisor
├─ process start
├─ stdout/stderr collection
├─ signal delivery
├─ exit status observation
└─ optional restart
        │
        ▼
long-running process
├─ dependency initialization
├─ listener creation
├─ readiness transition
├─ request/event processing
└─ graceful shutdown
```

## 네 가지 상태

```text
started   프로세스 생성을 시도했거나 생성됨
running   프로세스가 아직 존재함
ready     새 작업을 처리할 준비가 됨
healthy   정의한 핵심 동작이 정상 범위에 있음
```

다음은 모두 가능합니다.

```text
running=true, ready=false
→ DB recovery, migration, dependency 연결, cache warmup 중

ready=true, healthy=false
→ 요청은 받지만 일부 핵심 기능 실패

process exited, supervisor says active/restarting
→ restart loop 또는 상태 표시 지연
```

상태 이름은 framework와 supervisor마다 다릅니다. 이름보다 실제 판정 조건을 읽습니다.

## Foreground 실행

현대적인 supervisor와 container 환경에서는 애플리케이션이 foreground에서 실행되는 편이 수명주기를 단순하게 만듭니다.

장점:

- supervisor가 실제 main process PID와 종료 상태를 관찰합니다.
- stdout/stderr를 직접 수집합니다.
- stop signal과 timeout이 올바른 대상에 적용됩니다.
- child가 무단으로 남는 문제를 줄입니다.

애플리케이션이 스스로 background로 사라지거나 wrapper가 child를 시작한 뒤 종료하면 supervisor가 실제 작업 프로세스를 잃을 수 있습니다.

## 실행 문맥

대화형 셸과 supervisor 실행이 다를 때 다음을 비교합니다.

```text
absolute executable path
arguments
working directory
user/group
umask
environment
open stdin/stdout/stderr
resource limits
network namespace와 mount view
```

### 상대 경로

서비스가 `./config.json`을 찾는다면 supervisor의 working directory가 계약되어야 합니다. 실행 파일이 `/opt/app/bin/server`에 있다고 `./config.json`이 `/opt/app/bin/config.json`을 뜻하지는 않습니다.

### stdin

장기 서비스가 의도하지 않게 stdin을 읽으면 supervisor 아래에서 EOF를 받거나 영원히 대기할 수 있습니다. 대화형 입력이 필요한 도구와 무인 서비스를 구분합니다.

### 환경

로그인 셸의 profile이 supervisor 환경에 적용된다고 가정하지 않습니다. 필요한 설정은 명시적으로 전달하고 startup 때 유효성을 검사합니다.

## 설정과 상태 분리

| 종류 | 예 | 수명과 관리 |
|---|---|---|
| 실행 산출물 | binary, library, image | 버전 고정, 교체 가능 |
| 설정 | port, feature flag | 검토 가능, startup validation |
| 비밀값 | password, key, token | 최소 노출, rotation |
| 영속 데이터 | DB, upload | process 수명보다 길며 backup 필요 |
| 런타임 상태 | PID, socket, lock | 재시작 시 재생성 가능 |
| 로그·metric | 사건과 관찰 | 시간축, 보존, 민감정보 제한 |

이 가이드는 container 배포와 volume 구성 자체를 다루지 않습니다. container의 writable layer, volume, image와 public deployment는 `guide-web-infrastructure`가 담당합니다.

## 로그를 근거로 사용하기

좋은 진단 로그의 최소 요소:

- 절대 시각과 timezone 또는 일관된 UTC
- event 이름
- 결과와 오류 분류
- process/version 정보
- 필요한 correlation identifier
- 원인을 좁힐 안전한 문맥

피할 것:

- password, private key, full token
- 전체 environment dump
- 불필요한 개인정보
- 무제한 request body
- 같은 오류를 제한 없이 반복하는 restart loop

### stdout와 stderr

supervisor가 수집하기 쉬운 기본 통로입니다. 로그를 파일로 직접 쓸 경우 ownership, rotation, disk full, reopen과 삭제됐지만 열린 FD를 관리해야 합니다.

### 시간축 맞추기

서로 다른 process의 로그를 비교할 때 timezone, clock skew와 buffering을 고려합니다. “마지막 줄”이 실제 마지막 사건과 정확히 같지 않을 수 있습니다.

## Readiness

readiness는 외부에서 검증 가능한 조건이어야 합니다.

나쁜 조건:

```text
process exists
startup 후 10초 지남
log에 단어 ready가 한 번 보임
```

더 나은 조건:

```text
listener 생성됨
필수 설정 검증됨
DB 또는 필수 dependency 연결 가능
필요한 migration 완료
새 요청을 처리할 내부 queue 여유 있음
```

readiness endpoint가 있다면 process 내부 상태만 반환하는지 실제 dependency까지 검사하는지 구분합니다. 지나치게 깊은 검사로 일시적 dependency 지연 때 모든 instance를 동시에 unready로 만들 수도 있습니다.

## Liveness와 health

liveness는 process가 복구 불가능하게 멈춰 재시작이 필요한지 판단하는 데 사용할 수 있습니다. 외부 dependency 장애만으로 liveness를 실패시키면 restart storm을 만들 수 있습니다.

```text
readiness failure
→ 새 traffic 제외 가능

liveness failure
→ process restart 가능
```

정책은 애플리케이션 수명과 dependency 실패 모델에 맞춰야 합니다.

## 정상 종료

```text
stop request 또는 SIGTERM
→ readiness false
→ 새 작업 수락 중단
→ 진행 중 작업 drain
→ child·socket·file 정리
→ log flush
→ exit status 반환
```

유예 시간은 무한하지 않아야 하며, 강제 종료 전에 어떤 데이터나 요청이 남을 수 있는지 정의합니다.

supervisor가 wrapper에만 시그널을 보내고 actual child를 추적하지 못하면 정상 종료가 작동하지 않습니다. [프로세스, 시그널과 작업 제어](../02-process-and-resource-observation/01-processes-signals-and-jobs.md)의 process group과 wrapper 계약을 적용합니다.

## Supervisor 관찰

### Linux systemd 예

```sh
systemctl status UNIT --no-pager
systemctl show UNIT \
  -p ActiveState -p SubState -p MainPID -p ExecMainStatus
journalctl -u UNIT --since '-10 min' --no-pager
```

`enabled`는 boot policy, `active`는 current supervisor state입니다. readiness를 따로 확인합니다.

### macOS launchd 예

```sh
launchctl print DOMAIN/LABEL
```

실제 label, domain, program path, last exit status와 stdout/stderr destination을 확인합니다. OS 버전과 domain에 따라 명령이 다를 수 있습니다.

## Restart loop

재시작은 transient crash 복구에 유용하지만 configuration error를 해결하지 않습니다.

관찰할 것:

```text
restart count
각 실행의 PID와 시작 시각
exit code 또는 signal
재시도 간격
첫 failure log
readiness 도달 여부
resource와 port가 이전 실행에서 남았는지
```

무제한 즉시 restart는 log, CPU와 dependency 요청을 폭증시킬 수 있습니다. backoff와 최대 시도 또는 failure window를 둡니다.

## Container를 관찰할 때

container를 별도 OS처럼 생각하면 host와 namespace 경계를 놓칠 수 있습니다.

```text
container running
≠ application ready

container localhost
≠ host localhost

container filesystem path
≠ host path unless mounted
```

진단 기록에는 host/container 어느 범위에서 명령을 실행했는지 적습니다. image, Compose, network, volume, deployment와 backup의 구체 설계는 `guide-web-infrastructure`가 담당합니다.

## 실습 연결

- `05-working-directory`: supervisor와 대화형 셸의 작업 디렉터리 차이를 조사합니다.
- `07-running-not-ready`: process와 listener는 존재하지만 health가 503인 상태를 조사합니다.
- `08-signal-not-forwarded`: wrapper가 종료 요청을 child에게 전달하지 않는 상태를 조사합니다.

[시스템 조사 실습](../../exercises/system-investigation/README.md)

## 연결 실습

- [사례 07과 08](../../exercises/system-investigation/README.md)에서 readiness dependency와 signal forwarding을 검증합니다.

## 완료 기준

- running, ready와 healthy를 구분할 수 있습니다.
- 대화형 셸에서만 서비스가 성공할 때 비교할 실행 문맥을 제시할 수 있습니다.
- restart가 설정 오류를 고치지 못하고 오히려 증상을 키울 수 있음을 설명할 수 있습니다.
- readiness와 liveness가 다른 복구 행동을 유발하는 이유를 설명할 수 있습니다.
- 정상 종료 뒤 child, listener와 열린 파일까지 확인해야 하는 이유를 설명할 수 있습니다.

다음 문서: [시스템 문제 진단](02-system-troubleshooting.md)
