# 누적 실습: 시스템 조사

## 목표

- 아홉 증상을 상태, 소유권, 경계와 관찰 근거로 분류합니다.
- 읽기 전용 관찰 뒤 최소 수정과 회귀 검사를 설계합니다.

이 실습은 Unix 사용자 공간에서 발생하는 아홉 가지 문제를 재현합니다. 목표는 특정 명령을 외우는 것이 아니라 다음 질문에 근거로 답하는 것입니다.

```text
어느 계층이 실패했습니까?
실제 상태는 무엇입니까?
가설을 반증할 관찰은 무엇입니까?
가장 작은 안전한 수정은 무엇입니까?
수정 뒤 무엇을 다시 검사해야 합니까?
```

모든 사례는 현재 사용자 권한, loopback과 임시 디렉터리만 사용합니다. 외부 네트워크, 관리자 권한과 외부 Python 패키지가 필요하지 않습니다.

## 구성

```text
system-investigation/
├── README.md
├── create-workspace.sh
├── check.sh
├── check_answers.py
├── lab.py
├── skeleton/
│   └── diagnoses.json
├── reference/
│   └── diagnoses.json
└── tests/
    └── broken-diagnoses.json
```

- `lab.py`: 사례를 만들고 증상을 재현하며 정리합니다.
- `skeleton/diagnoses.json`: 학습자가 작성할 시작점입니다.
- `reference/diagnoses.json`: 전체 조사가 끝난 뒤 비교할 기준 답안입니다.
- `check_answers.py`: 구조화된 진단 계약을 검사합니다.
- `check.sh`: 시작점, 기준 답안, 오답 거부 능력과 모든 사례 자체 검사를 실행합니다.

이 실습은 실행 코드를 구현하는 project가 아니라 관찰 결과를 구조화하는 analysis/evidence exercise입니다. 따라서 JSON 기준 답안에 Implementation 번호를 강제하지 않고 아래 증거 작성 순서가 학습 지향 construction walkthrough 역할을 대신합니다. `lab.py`, checker와 scenario 코드는 답안 구현이 아니라 재현·검증 infrastructure입니다.

<!-- guide-contract:implementation-annotation
{"artifact":"exercises/system-investigation/reference/diagnoses.json","mode":"expected-evidence","scope":"exercises/system-investigation/reference","walkthrough":"evidence-construction"}
-->

<!-- guide-contract:evidence-construction:start -->
| 순서 | 작성 필드 | 책임 | 검증 |
|---:|---|---|---|
| 1 | `observation_commands` | 실제 상태를 바꾸지 않고 가설을 판별할 관찰을 고릅니다. | 허용된 읽기 전용 명령 형태와 사례별 필요한 상태 질문 |
| 2 | `expected_evidence`, `evidence_facts` | 명령 출력에서 확인할 사실과 반증 조건을 기록합니다. | 구체적 근거 문장과 관찰 가능한 사실 enum |
| 3 | `layer`, `primary_cause` | 증상을 실패 계층과 하나의 주 원인으로 좁힙니다. | 공개 vocabulary와 사례의 관찰 계약 |
| 4 | `safe_fix` | 증거를 가장 적게 지우는 최소 복구를 고릅니다. | 공개 vocabulary와 사례의 안전 경계 |
| 5 | `regression_checks`, `regression_targets` | 정상·실패·수명 조건을 다시 확인할 절차와 보장 결과를 적습니다. | 두 개 이상의 구체적 검사와 회귀 목표 enum |
<!-- guide-contract:evidence-construction:end -->

## 시작

저장소 루트에서 준비를 마칩니다.

```sh
./prepare.sh
```

작업 공간을 만듭니다.

```sh
cd exercises/system-investigation
./create-workspace.sh
```

기존 `workspace/`는 덮어쓰지 않습니다.

기존 schema 1 답안도 자동 변경하지 않습니다. `schema_version` 오류가 나오면 파일을
먼저 백업하고, 아래 계약 조회 결과를 보며 `evidence_facts`와
`regression_targets`를 사례별로 추가해 schema 2로 옮깁니다.

사례 목록:

```sh
python3 lab.py list
```

## 사례별 반복

사례 하나를 만듭니다.

```sh
python3 lab.py create 01-command-resolution workspace/case-01
```

증상을 재현합니다.

```sh
python3 lab.py symptom workspace/case-01
```

현재 사례의 안전한 시작 정보만 확인합니다.

```sh
python3 lab.py status workspace/case-01
```

관찰 명령은 생성한 사례 디렉터리에서 실행하고, `PID`, `PORT` 같은 placeholder는 `status`가 보여 준 해당 사례의 실제 값으로 바꿉니다. 사례 01의 `PATH`는 persistent shell을 바꾸지 않고 생성된 `scenario.env`를 눈으로 확인한 뒤 사례 디렉터리에서 시작한 제한된 subshell에만 직접 구성합니다. 생성 파일을 shell source로 실행하지 않습니다.

```sh
cd workspace/case-01
cat scenario.env
(
  PATH="$PWD/stale-bin:$PWD/trusted-bin:/usr/bin:/bin"
  export PATH
  command -v unix-guide-tool
  type -a unix-guide-tool
  printenv PATH
)
cd ../..
```

조사가 끝나면 남은 프로세스와 임시 자원을 정리합니다.

```sh
python3 lab.py destroy workspace/case-01
```

`destroy`는 사례 파일에 기록된 PID가 실제로 해당 사례 디렉터리의 프로그램인지 확인한 뒤에만 종료를 시도합니다.

## 사례

| ID | 증상 | 중심 질문 |
|---|---|---|
| `01-command-resolution` | 같은 명령 이름이 exit 42로 실패 | 실제로 어떤 실행 파일이 선택됐습니까? |
| `02-dangling-symlink` | `current/config.ini`를 읽지 못함 | 링크 자체와 대상 중 무엇이 없습니까? |
| `03-waiting-for-input` | 프로세스는 존재하지만 출력이 없음 | 어떤 입력 자원을 기다립니까? |
| `04-deleted-open-file` | 로그 경로는 없지만 writer가 계속 실행 | 어떤 FD가 삭제된 객체를 유지합니까? |
| `05-working-directory` | 대화형 위치에서는 되지만 다른 cwd에서는 실패 | 상대 경로의 기준은 어디입니까? |
| `06-address-family-mismatch` | IPv6 loopback 연결만 거부 | listener와 client의 address family가 같습니까? |
| `07-running-not-ready` | 프로세스와 listener는 있으나 health 503 | running과 ready를 무엇으로 구분합니까? |
| `08-signal-not-forwarded` | wrapper 종료 뒤 worker가 남음 | 종료 책임과 시그널 전달은 누구에게 있습니까? |
| `09-reserved-not-resident` | virtual size는 크지만 RSS는 상대적으로 작음 | 예약과 실제 상주량을 구분했습니까? |

## 조사 기록

`workspace/diagnoses.json`의 각 사례에 다음을 기록합니다.

```json
{
  "layer": "실패 계층 enum",
  "primary_cause": "주 원인 enum",
  "observation_commands": [
    "상태를 바꾸지 않는 명령 1",
    "상태를 바꾸지 않는 명령 2"
  ],
  "expected_evidence": "각 명령에서 어떤 사실이 보여야 가설이 지지되는지",
  "evidence_facts": [
    "관찰로 확정한 사실 enum"
  ],
  "safe_fix": "가장 작은 수정 enum",
  "regression_checks": [
    "정상 조건",
    "실패 또는 수명 조건"
  ],
  "regression_targets": [
    "회귀 검사로 보장할 결과 enum"
  ]
}
```

`layer`, `primary_cause`, `safe_fix`, `evidence_facts`, `regression_targets`는 자동 검사 가능한 계약입니다. 검사기는 안전을 위해 학습자가 쓴 명령을 실행하지 않고 읽기 전용 명령 형태와 필요한 관찰 종류만 검사합니다. `expected_evidence`와 `regression_checks` 문장의 인과 관계는 실제 출력 및 조사가 끝난 뒤의 기준 답안과 직접 대조합니다. 명령과 설명은 그대로 복사하기보다 실제로 관찰한 경로·PID·port를 반영합니다.

작성 형식, 허용 vocabulary와 읽기 전용 명령 정책은 답안 source를 열지 않고 조회할 수 있습니다. 이 명령은 선택한 사례의 정답 원인·수정·근거 enum을 공개하지 않습니다.

```sh
python3 check_answers.py --show-contract 01-command-resolution
```

작업 답안 검사:

```sh
./check.sh workspace
```

성공 출력의 `STRUCTURE PASS`는 구조화된 계약만 통과했다는 뜻입니다.
`SEMANTIC REVIEW REQUIRED`에 따라 실제 출력과 기준 답안을 대조해야 완료입니다.

기준 답안은 조사가 끝난 뒤 `reference/diagnoses.json`을 열어 learner 기록과 사례별로 수동 비교합니다. 다음 명령은 그 기준 답안 파일 자체가 repository contract를 만족하는지 검사할 뿐 learner/reference 비교를 수행하지 않습니다.

```sh
./check.sh reference
```

## 권장 관찰 방식

### 명령 정체성

```sh
command -v unix-guide-tool
type -a unix-guide-tool
printenv PATH
```

### 경로와 링크

```sh
ls -ld path
readlink path
file path
```

### 프로세스와 열린 자원

```sh
ps -p PID -o pid=,ppid=,state=,etime=,command=
lsof -p PID
```

Linux에서는 필요하면 다음을 보조적으로 사용합니다.

```sh
ls -l /proc/PID/fd
cat /proc/PID/status
```

### Listener와 연결

```sh
# Linux
ss -lnt

# macOS
lsof -nP -iTCP -sTCP:LISTEN
```

### 메모리

```sh
ps -p PID -o pid=,vsz=,rss=,etime=,command=
```

도구가 출력하지 않는다고 상태가 없다고 단정하지 않습니다. 권한, 플랫폼과 순간 상태를 고려하고 다른 독립 근거로 확인합니다.

## 안전 규칙

- 사례 디렉터리 밖의 파일을 수정하지 않습니다.
- `sudo`를 사용하지 않습니다.
- 외부 주소를 scan하지 않습니다.
- 강제 종료 전 기록된 PID와 command를 확인합니다.
- `workspace/`를 자동 삭제하지 않습니다.
- 실제 운영 service에 실습 명령을 적용하지 않습니다.
- 로그나 답안에 비밀 환경 변수를 기록하지 않습니다.

## 전체 검증

먼저 learner 답안을 검사하고 실제 출력과 의미를 수동 검토합니다.

```sh
./check.sh workspace
```

그 뒤 `reference/diagnoses.json`을 learner 기록과 수동 비교하고 repository-owned 실습 자체의 완전성을 검사합니다. `./check.sh reference`는 기준 답안 파일 자체만 검사합니다.

```sh
./check.sh reference
./check.sh all
```

이 명령은 다음을 확인합니다.

- 기준 답안이 계약을 만족함
- skeleton이 미완성 상태로 확실히 거부됨
- 알려진 잘못된 답안이 거부됨
- 아홉 사례가 의도한 증상을 실제로 재현함
- 각 사례의 최소 수정이 증상을 해결함
- 생성한 child process와 임시 파일이 정리됨

scenario selftest는 핵심 증상, 대표 최소 복구와 자원 정리를 검사합니다. 학습자가 제안한 모든 `regression_checks`와 `regression_targets`를 대신 실행하지는 않으므로 그 내용과 실제 관찰의 인과 관계는 semantic review에서 별도로 확인합니다.

## 완료 기준

- 아홉 사례마다 원인 계층과 반증 가능한 관찰 근거를 기록합니다.
- 상태를 크게 바꾸지 않는 최소 수정과 두 개 이상의 회귀 검사를 제안합니다.
- 모든 사례 종료 뒤 실습 프로세스와 listener가 남지 않음을 확인합니다.

## 자기 설명

- 프로세스가 실행 중이라는 사실만으로 서비스 준비 상태를 증명할 수 없는 이유는 무엇입니까?
- 증상과 원인을 혼동하지 않기 위해 어떤 두 독립 근거를 수집해야 합니까?

## 검증

```sh
./check.sh workspace
./check.sh reference
./check.sh all
../../verify.sh
```

`./check.sh all`과 `../../verify.sh`는 learner workspace를 읽지 않습니다. 따라서 `workspace` 검사와 실제 사례 출력에 대한 semantic review를 생략할 수 없습니다.
