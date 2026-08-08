# CLI 검사기 설계

## 학습 목표

- 이 문서의 핵심 모델과 경계를 자신의 말로 설명할 수 있습니다.
- 제시된 절차를 실행하기 전에 결과와 실패 조건을 예측할 수 있습니다.

## 선행 개념

- 파일·JSON·subprocess·concurrency·testing 계약과 의도된 실패 구분

## 문제 경계

함수를 직접 호출하는 단위 테스트만으로는 명령줄 프로그램의 실제 계약을 모두 확인할 수 없습니다.

```text
인자 경계
현재 작업 디렉터리
환경 변수
stdin
stdout
stderr
종료 상태
제한 시간
자식 프로세스 수명
보고서 저장
```

누적 실습 [`command-checker`](../../exercises/command-checker/README.md)는 이 경계를 단계별로 구현합니다.

## 최종 인터페이스

```text
command-checker --cases CASES [--jobs N]
                [--json-report PATH]
                [--junit-report PATH]
                -- COMMAND [ARG ...]
```

사례 파일:

```json
[
  {
    "name": "ascending",
    "args": [],
    "stdin": "3 1 2\n",
    "stdout": "1\n2\n3\n",
    "stderr": "",
    "returncode": 0,
    "timeout": 2.0,
    "output_limit": 1048576
  }
]
```

## 상태와 실패 분류

### 시작 전 계약 오류

- JSON 형식 오류
- 필드 타입 오류
- 중복 이름
- 없는 작업 디렉터리
- 잘못된 환경 변수 이름
- 실행 파일을 찾지 못함
- 보고서 경로 오류

종료 상태 2를 사용합니다.

### 실행 뒤 결과 불일치

- returncode 불일치
- stdout 불일치
- stderr 불일치
- timeout
- 출력 상한 초과

`Result(passed=False)`로 기록하고 전체 종료 상태 1을 사용합니다.

### 성공

모든 사례가 일치하면 0입니다.

이 분류를 유지하면 사용자는 명세를 고쳐야 하는지, 검사 대상 프로그램을 고쳐야 하는지 구분할 수 있습니다.

## 모듈 책임

| 모듈 | 책임 |
|---|---|
| `model.py` | 불변 `Case`, `Result`와 경계 예외 |
| `comparison.py` | 실제 세 채널과 기대값의 순수 비교 |
| `specification.py` | JSON을 검증된 `Case`로 변환 |
| `process.py` | 프로세스·파이프·deadline·신호 수명 |
| `reports.py` | JSON/JUnit 직렬화와 원자적 교체 |
| `runner.py` | 사례 순서, 병렬 실행과 최종 정책 |
| `cli.py` | argparse, 사용자 진단과 종료 상태 |

의존 방향:

```text
model ← comparison
model ← specification
model ← process
model ← reports
cli → specification, runner, reports
runner → process
```

`process.py`가 터미널 문구를 결정하거나 `reports.py`가 명령을 실행하면 책임이 다시 섞인 것입니다.

## 단계별 성장

### 1단계: 패키지와 진입점

`python -m command_checker`가 실행되고, 도움말은 stdout/0, 사용법 오류는 stderr/2를 사용합니다.

### 2단계: 데이터 모델

공유 데이터는 불변 타입으로 만들고 가변 dict 대신 정렬된 튜플 쌍을 사용합니다.

### 3단계: 비교

returncode, stdout과 stderr를 별도로 비교하는 순수 함수를 만듭니다. 공백과 줄바꿈도 계약에 포함합니다.

### 4단계: 명세

JSON의 외형뿐 아니라 필드, 범위, 경로와 운영체제 문자열 제약을 검사합니다.

### 5단계: 한 건 실행

인자 목록, stdin, cwd와 환경을 전달하고 실제 세 결과 채널을 수집합니다.

### 6단계: 전체 집계

한 사례가 실패해도 나머지를 실행하고 입력 순서로 결과를 표시합니다.

### 7단계: 수명 제한

POSIX 프로세스 그룹, non-blocking 파이프, deadline과 스트림별 출력 상한을 추가합니다.

### 8단계: 병렬성과 보고서

동시 실행 수를 제한하고 결과 순서를 보존합니다. 같은 `Result` 목록에서 JSON과 JUnit을 만들고 원자적으로 교체합니다.

## 검증 전략

각 단계는 이전 단계를 포함합니다.

```sh
make stage-01 EXERCISE_IMPL=workspace
make stage-02 EXERCISE_IMPL=workspace
...
make stage-08 EXERCISE_IMPL=workspace
```

전체 reference와 저장소 계약:

```sh
./verify.sh
```

검사는 다음을 포함합니다.

- package import와 `-m` 실행
- 불변 데이터 모델
- 정확한 출력 비교
- 잘못된 JSON과 필드
- cwd·env·인자 경계
- 실패 뒤 다음 사례 실행
- timeout 뒤 자식 프로세스 제거
- stdout/stderr 출력 초과
- 병렬 완료 순서 역전
- JSON/JUnit 일관성
- 기존 보고서 보존과 임시 파일 정리
- skeleton의 의도된 첫 실패

## 한계

- Windows 네이티브 프로세스 트리 종료는 구현하지 않습니다.
- shell pipeline 문법을 해석하지 않습니다. 명령은 이미 나뉜 인자 목록으로 받습니다.
- binary stdout/stderr의 원문 보존이 아니라 UTF-8 텍스트 검사를 목표로 합니다. 디코딩할 수 없는 바이트는 대체 문자로 표현합니다.
- remote 실행, container orchestration과 분산 test scheduling은 범위 밖입니다.

## 연결 실습

- [command-checker 전체 실습](../../exercises/command-checker/README.md)을 stage 01~08 순서로 완성하고 JSON/JUnit까지 검증합니다.

## 완료 기준

- 명세 오류와 결과 불일치를 구분합니다.
- 실행과 비교가 독립적으로 검사됩니다.
- 프로세스와 모든 파이프의 소유자가 명확합니다.
- timeout·출력 초과 뒤 자식이 남지 않습니다.
- 병렬 실행이 결과 순서를 흔들지 않습니다.
- 보고서는 완성된 뒤에만 최종 경로를 바꿉니다.
- `./verify.sh` 하나로 저장소 전체를 확인할 수 있습니다.
