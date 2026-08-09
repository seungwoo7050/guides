# Process runner와 terminal 계약

## 목표

코딩 에이전트가 build·test·lint·formatter·개발 서버를 실행할 수 있게 하되, command 문자열을 곧바로 shell에 넘기지 않고 cwd·환경·시간·출력·자식 수명·network를 통제합니다.

## command는 구조화한다

기본 요청:

```text
command_id 또는 executable
argv[]
cwd
env additions/removals
stdin mode
timeout profile
output limit
network profile
workspace mutation expectation
PTY requirement
```

가능하면 `shell=False`와 argv 실행을 사용합니다. pipe, redirection, glob, `&&`가 필요하면 shell script 자체를 검토 가능한 artifact로 만들거나 제한된 shell profile을 별도로 둡니다.

## command source

command는 다음 출처 중 하나여야 합니다.

- repository manifest·script·CI에서 발견한 명령
- tool catalog에 사전 등록한 check
- 사용자가 명시한 명령
- 모델이 제안하고 policy/approval을 통과한 구조화된 명령

모델이 “일반적으로 이 프로젝트는…”이라는 추측으로 destructive command를 실행하지 않습니다.

### 이 가이드의 필수 reference profile

필수 구현에서는 위 설계 공간을 더 좁힙니다. 모델에 공개되는 `run_check` action은
`check_id`만 선택하며, command catalog가 다음 값을 모두 review 시점에 고정합니다.

- exact argv와 canonical cwd
- 환경 변수의 key와 value
- executable digest와, 직접 실행하는 script가 있으면 script digest
- timeout과 stdout·stderr 합산 byte 상한
- network profile

실행 직전에 catalog와 executable·script digest를 다시 비교합니다. model action은 이 값을
덮어쓸 수 없고, catalog가 runner 생성 뒤 바뀌어도 실행을 거절합니다. 범용 shell은 공개
check runner에 등록하지 않으며 Git effect는 전용 adapter만 사용합니다. 사용자가 제안한
임의 명령이나 제한된 shell profile은 별도 승인·격리를 설계하는 선택 확장이지, 필수
Capstone의 성공 경로가 아닙니다.

## working directory

`cwd`는 command 의미의 일부입니다. canonical workspace root와 허용 subtree 안인지 확인합니다. command가 `cd`를 내부적으로 수행하는지 script source도 고려합니다.

결과에 실제 cwd를 기록하고 resume 시 같은 위치가 존재하는지 확인합니다.

## 환경 변수

기본적으로 clean environment를 구성합니다.

- 최소 PATH
- locale과 timezone
- deterministic test seed
- proxy·credential 제거
- package cache 경로 분리
- 필요한 env만 allowlist
- secret은 모델·stdout에 노출하지 않는 broker 방식 고려

사용자 shell 전체 환경을 상속하면 token, agent socket, cloud credential과 개인 설정이 노출될 수 있습니다.

## process tree와 signal

부모 process timeout만 종료하면 child server가 남을 수 있습니다.

```text
spawn process group 또는 job object
→ stdout/stderr 비동기 수집
→ cancel/timeout 시 graceful signal
→ grace period
→ 강제 종료
→ descendant 확인
→ resource cleanup
```

Unix와 Windows의 process group·job control 차이는 adapter가 처리합니다.

## stdout와 stderr

- 두 stream을 구분합니다.
- byte 상한과 line 상한을 둡니다.
- head·tail 또는 artifact spill 정책을 둡니다.
- binary output을 text로 오해하지 않습니다.
- truncation 사실을 result에 표시합니다.
- ANSI escape와 terminal control을 sanitize해 UI를 보호합니다.
- secret redaction은 원문 artifact와 모델 context에 각각 적용합니다.

“마지막 20줄”만 남기면 최초 causal error를 잃을 수 있으므로 structured diagnostic extractor와 full artifact reference를 함께 사용합니다.

## timeout과 deadline

다음을 분리합니다.

```text
queue timeout
startup timeout
idle timeout
command timeout
session deadline
user cancel
```

command timeout은 test 실패가 아니라 `TIMEOUT`입니다. timeout 뒤 workspace가 바뀌었을 수 있으므로 mutation check와 cleanup을 수행합니다.

## interactive command와 PTY

일부 test runner, debugger, REPL, package manager는 TTY 동작이 다릅니다.

기본 Capstone은 non-interactive command를 우선합니다. PTY가 필요한 경우:

- 화면 escape와 window size
- stdin ownership
- prompt 감지
- password 입력 금지
- detach·background process
- transcript와 raw terminal artifact

를 별도 contract로 둡니다.

## network와 dependency effect

command runner가 network policy를 직접 우회하지 못하게 sandbox에서 강제합니다. `curl`, package manager, test의 외부 API 호출을 command name만으로 판정하지 않습니다.

- default deny 또는 task profile별 allow
- domain/IP/port 제한
- DNS와 connection audit
- loopback과 외부 network 구분
- package registry와 arbitrary web 구분

제공되는 로컬 reference는 exact catalog와 clean environment를 application 수준에서
검사하며 receipt에 `CATALOG_POLICY_ONLY` 또는 주입된 wrapper의 `OS_WRAPPER`를 기록합니다.
wrapper가 없는 실행은 packet-level egress 차단이 아닙니다. 임의 native binary, `setsid()`로
이탈하는 자식, filesystem TOCTOU까지 적대적으로 격리하려면 container·namespace·OS
sandbox를 추가하고 그 적용 증거를 별도로 검증해야 합니다.

## CommandResult

```text
command_run_id
argv_digest
cwd
sanitized_env_manifest
started_at·ended_at
exit_kind: code | signal | timeout | cancelled | spawn_error
exit_code_or_signal
stdout_artifact·stderr_artifact
truncation
workspace_before·after
process_cleanup_status
network_receipt
resource_usage
```

## 실패 조건

- `shell=True` 하나로 모든 command를 실행합니다.
- timeout 후 child process와 port가 남습니다.
- command 실패와 parser 실패를 같은 exit code로 만듭니다.
- stdout 상한 초과로 deadlock됩니다.
- 사용자 환경과 credential을 그대로 상속합니다.
- cancel을 model turn 사이에서만 확인합니다.
- dependency install이 lockfile과 workspace를 바꿨지만 기록하지 않습니다.

## 완료 조건

- 정상 종료, nonzero, signal, timeout, output overflow, cancel과 spawn failure를 구분합니다.
- process tree가 모든 종료 경로에서 정리됩니다.
- command가 실행한 실제 argv·cwd·환경·network profile을 receipt로 남깁니다.
- command 전후 workspace mutation을 감지하고 예상 범위와 비교합니다.
