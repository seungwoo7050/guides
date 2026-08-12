# 시스템 문제 진단

좋은 문제 해결은 여러 설정을 한 번에 바꿔 우연히 동작하게 만드는 일이 아닙니다. 현재 증상을 보존하고, 실패 계층을 선택하고, 가설 하나와 반증 조건 하나를 세운 뒤, 가장 작은 읽기 전용 검사로 불확실성을 줄이는 과정입니다.

## 학습 목표

- 재현 조건과 기준 시각을 고정합니다.
- 예상 상태와 실제 상태를 구분합니다.
- 실패 계층을 선택하고 가설·반증 조건을 작성합니다.
- 읽기 전용 검사와 상태 변경을 분리합니다.
- 변경 하나의 효과를 정상·실패·회귀 조건으로 검증합니다.
- 되돌리기와 증거 보존을 복구 절차에 포함합니다.
- 다른 사람이 반복할 수 있는 runbook과 사건 기록을 작성합니다.

## 선행 개념

- 앞선 실행 문맥·path·FD·process·memory·network·service 모델과 반증 조건 기록

## 기본 절차

```text
1. 증상과 영향 범위를 고정합니다.
2. 절대 시각과 실행 범위를 기록합니다.
3. 정확한 명령·입력·stdout·stderr·종료 상태를 보존합니다.
4. 예상 상태와 실제 상태를 나눠 적습니다.
5. 최근 변경과 마지막 성공 시점을 기록합니다.
6. 실패 가능 계층 하나를 선택합니다.
7. 가설 하나와 반증 조건 하나를 적습니다.
8. 가장 작은 읽기 전용 검사를 실행합니다.
9. 근거에 맞는 변경 하나만 적용합니다.
10. 정상·실패·회귀 조건을 모두 재검증합니다.
11. 결과가 맞지 않으면 되돌리고 다음 가설로 이동합니다.
12. 원인, 수정, 검증과 남은 한계를 기록합니다.
```

나쁜 반복:

```text
오류
→ 검색 결과 첫 명령 실행
→ sudo 추가
→ 설정 여러 개 변경
→ 모든 process 재시작
→ 우연히 동작
```

이유와 부작용을 설명할 수 없다면 복구가 아니라 상태를 모르게 만든 것입니다.

## 증상 기록

나쁜 기록:

```text
서버가 안 됩니다.
```

더 나은 기록:

```text
2026-08-08 19:20:13 +0900
host 범위의 일반 사용자 shell에서
python client가 [::1]:43127에 TCP connect했을 때
ConnectionRefusedError, process exit 1.
같은 port의 127.0.0.1 연결은 성공.
server PID 9123은 127.0.0.1:43127에 LISTEN.
```

최소 항목:

- 절대 timestamp와 timezone
- host/container/VM 범위
- 사용자와 현재 디렉터리
- 정확한 실행 파일과 인자
- 입력·fixture·request identifier
- stdout, stderr와 종료 상태
- 예상 결과와 실제 결과
- 마지막 성공 시점
- 최근 변경
- 영향받는 사용자·기능·데이터 범위

비밀값은 가리되 오류 의미를 지우지 않습니다.

## 실패 계층 지도

```text
1. 입력·셸 해석·명령 탐색
2. 실행 파일·runtime·architecture
3. 경로·link·mount·filesystem
4. 사용자·그룹·권한·환경
5. process·child·signal·job control
6. FD·stream·file·resource limit
7. memory mapping·resident set·pressure
8. name·address·route·listener·connection
9. service·readiness·dependency·log
10. container·proxy·external system·application protocol
```

증상 예:

| 증상 | 먼저 확인할 계층 |
|---|---|
| 명령이 없음 | 1 |
| 같은 명령인데 다른 동작 | 1, 4 |
| `No such file or directory` | 2, 3, 4 |
| `Permission denied` | 3, 4 |
| 출력 없이 끝나지 않음 | 5, 6 |
| disk가 차는데 파일이 안 보임 | 3, 6 |
| memory 숫자가 큼 | 7 |
| connection refused | 8, 9 |
| process는 있는데 health 실패 | 9 |
| restart 뒤에도 child/listener 남음 | 5, 6, 9 |

오류 문장 하나가 정확한 계층을 보장하지 않습니다. 예를 들어 실행 파일의 interpreter가 없을 때도 shell은 경로가 없는 것처럼 보이는 오류를 낼 수 있습니다.

## 가설과 반증 조건

나쁜 가설:

```text
네트워크 문제입니다.
```

검사 가능한 가설:

```text
가설:
client는 localhost를 IPv6 ::1로 해석하지만 server는 IPv4 127.0.0.1에만 listen한다.

예상 근거:
IPv4 connect는 성공하고 IPv6 connect는 refused다.
listener 목록에는 IPv4 endpoint만 있다.

반증 조건:
server가 [::1]:PORT에도 listen하거나 IPv6 connect가 성공한다.
```

반증 조건을 먼저 적으면 보고 싶은 증거만 선택하는 오류를 줄일 수 있습니다.

## 읽기 전용 검사

변경 전에 현재 상태를 보존합니다.

### 공통 실행 문맥

```sh
date '+%Y-%m-%d %H:%M:%S %z'
pwd
id
```

### 명령 정체성

```sh
command -v command-name
type command-name
```

### 결과 통로

```sh
command >stdout.log 2>stderr.log
status=$?
printf 'status=%s\n' "$status"
```

### 파일과 경로

```sh
ls -ld path
file path
readlink path 2>/dev/null || true
df -h path
```

### 프로세스

```sh
ps -eo pid=,ppid=,user=,state=,etime=,command=
```

### 열린 자원

```sh
lsof -p PID
```

### 메모리

```sh
ps -p PID -o pid=,vsz=,rss=,etime=,command=
```

### 네트워크 listener

```sh
# Linux
ss -lnt 2>/dev/null || true

# macOS
lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null || true
```

모든 명령을 한 번에 실행하지 않습니다. 선택한 가설을 가장 싸고 안전하게 반증할 검사부터 수행합니다.

## 상태 변경 전 질문

```text
무엇을 바꿉니까?
어떤 가설 때문에 바꿉니까?
어떤 성공 조건을 기대합니까?
어떤 실패 조건도 보존해야 합니까?
되돌리는 방법은 무엇입니까?
데이터와 다른 사용자에게 어떤 영향이 있습니까?
```

예:

```text
PATH 전체를 다시 작성
보다
현재 shell에서 신뢰한 directory를 앞에 두고 command -v로 확인
```

```text
모든 service 재시작
보다
문제 process 하나의 readiness dependency 수정 후 제한된 restart
```

## 변경 후 검증

정상 조건만 확인하지 않습니다.

```text
정상 조건
→ 의도한 입력이 성공

실패 조건
→ 잘못된 입력·권한·dependency가 여전히 안전하게 실패

회귀 조건
→ 기존 다른 command·client·service가 영향을 받지 않음

수명 조건
→ child, FD, listener, temporary file이 남지 않음

관찰 조건
→ log와 상태가 새 결과를 설명함
```

수정 직후 한 번 성공했다고 장기 문제가 해결됐다고 단정하지 않습니다. 반복 workload와 시간 구간이 필요한 경우 기준과 같은 조건으로 다시 측정합니다.

## 되돌리기

되돌리기는 “원래 파일을 기억해서 다시 편집”하는 일이 아닙니다. 변경 전 상태를 식별할 수 있어야 합니다.

- versioned configuration
- previous symlink target
- previous executable path 또는 artifact digest
- DB·data 변경과 분리된 application rollback
- supervisor 상태와 process ownership

되돌린 뒤에도 같은 성공·실패 조건을 다시 확인합니다. rollback 자체도 실패할 수 있습니다.

## Runbook 형식

```text
제목
대상 범위와 영향
증상과 trigger
필수 권한과 안전 경계
첫 읽기 전용 검사
분기 조건
완화 방법
근본 수정
되돌리기
복구 검증
수집할 근거
남은 한계와 escalation 조건
```

명령을 복사해 실행하는 목록보다 각 명령이 어떤 질문에 답하는지 적습니다.

## 실습 수행법

[시스템 조사 실습](../../exercises/system-investigation/README.md)은 가이드 전체를 통합합니다.

각 사례에서 다음 답을 구조화해 기록합니다.

```text
layer
primary_cause
observation_commands
expected_evidence
evidence_facts
safe_fix
regression_checks
regression_targets
```

자동 검사에서 정답 문자열을 맞히는 것으로 끝내지 않습니다. 실제 scenario를 생성하고 관찰 명령이 예상한 상태를 보여 주는지 확인합니다.

## 연결 실습

- [아홉 사례 전체](../../exercises/system-investigation/README.md)의 계층·원인·읽기 전용 명령·근거·회귀 검사를 `workspace/diagnoses.json`에서 통합 검토합니다.
- `exercises/system-investigation`에서 `./check.sh workspace`의 구조 검사를 통과한 뒤 실제 출력과 설명의 인과 관계를 수동 검토하고, 그 다음에만 `reference/diagnoses.json`과 비교합니다.

## 완료 기준

- 아홉 증상을 실패 계층과 소유권 경계로 분류할 수 있습니다.
- 상태 변경 전에 두 개 이상의 독립 관찰 근거를 제시할 수 있습니다.
- 최소 수정 뒤 process, listener와 기능 회귀를 함께 확인할 수 있습니다.

다음 상황에서 첫 변경을 하기 전에 세 개 이상의 읽기 전용 근거와 하나의 반증 조건을 제시할 수 있어야 합니다.

1. 예상한 도구 대신 오래된 실행 파일이 실행됩니다.
2. `current` 심볼릭 링크가 있지만 설정 파일을 읽지 못합니다.
3. 프로세스는 출력 없이 계속 존재합니다.
4. 로그 경로를 삭제했지만 디스크 공간이 회수되지 않습니다.
5. 대화형 셸에서는 되지만 service supervisor에서는 실패합니다.
6. server process가 있는데 IPv6 loopback 연결만 거부됩니다.
7. listener는 있지만 health가 503입니다.
8. wrapper를 종료했는데 child가 남습니다.
9. virtual size는 크지만 RSS는 작습니다.

이 기준을 만족하면 Unix 사용자 공간의 문제를 “명령 모음”이 아니라 **상태·소유권·경계·근거**로 다룰 준비가 된 것입니다.
