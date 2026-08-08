# 누적 실습: `command-checker`

## 목표

- 외부 명령의 입력, 출력, 오류, 종료 상태와 수명을 명시적인 계약으로 구현합니다.
- 단계별 실패를 이용해 데이터 모델에서 병렬 보고서까지 누적 완성합니다.

`command-checker`는 JSON에 기록한 사례로 외부 명령줄 프로그램을 실행하고 `returncode`, `stdout`, `stderr`를 비교합니다. 한 사례의 실패가 뒤 사례를 막지 않아야 하며, 제한 시간을 넘기거나 출력을 끝없이 만드는 프로세스는 자식까지 정리합니다.

최종 구현은 Python 3.12 이상과 macOS·Linux의 POSIX 프로세스 그룹을 사용합니다. Windows 네이티브 프로세스 트리 종료는 지원 범위에 포함하지 않습니다.

## 작업 원칙

```text
현재 단계 문서를 읽는다
→ skeleton을 복사한 workspace에서 한 책임만 구현한다
→ 현재 단계 검사
→ 이전 단계 회귀 검사
→ 실패 원인을 설명한다
→ 수정한다
→ 마지막에 reference와 비교한다
```

처음부터 reference를 복사하면 순수 비교에서 프로세스 수명 제어로 성장하는 판단 과정을 잃습니다.

## 구성

```text
command-checker/
├── README.md
├── fixtures/
├── skeleton/command_checker/
├── reference/command_checker/
└── tests/
```

최종 모듈 책임:

| 모듈 | 책임 |
|---|---|
| `model.py` | 불변 `Case`, `Result`와 경계 예외 |
| `comparison.py` | 실제 관찰과 기대값의 순수 비교 |
| `specification.py` | JSON·필드·경로·환경 값 검증 |
| `process.py` | 프로세스·파이프·deadline·신호 수명 |
| `reports.py` | JSON·JUnit과 원자적 파일 교체 |
| `runner.py` | 순차·병렬 실행, 결과 순서와 종료 정책 |
| `cli.py` | argparse, 사용자 진단과 최종 조립 |

## 작업 공간

저장소 루트에서 실행합니다.

```sh
scripts/new-workspace.sh exercises/command-checker
```

기존 `workspace/`가 있으면 실패하며 덮어쓰지 않습니다.

## 최종 인터페이스

```text
command-checker --cases CASES [--jobs N]
                [--json-report PATH]
                [--junit-report PATH]
                -- COMMAND [ARG ...]
```

가장 작은 사례:

```json
[
  {
    "name": "ascending",
    "stdin": "3 1 2\n",
    "stdout": "1\n2\n3\n",
    "stderr": "",
    "returncode": 0
  }
]
```

지원 필드:

| 필드 | 타입 | 기본값 |
|---|---|---|
| `name` | 비어 있지 않은 문자열 | 필수 |
| `args` | 문자열 배열 | `[]` |
| `stdin` | 문자열 | `""` |
| `stdout` | 문자열 | `""` |
| `stderr` | 문자열 | `""` |
| `returncode` | 정수 | `0` |
| `timeout` | 유한한 양수 | `2.0` |
| `output_limit` | 양의 정수 바이트 수 | `1048576` |
| `cwd` | 사례 파일 기준 상대 경로 | `null` |
| `env` | 문자열 키·값 객체 | `{}` |

## 1단계: 패키지와 진입점

관련 문서: [실행 환경과 모듈](../../docs/01-language-and-runtime/01-runtime-and-environment.md)

구현:

- `python -m command_checker` 진입점
- `build_parser()`와 `main(argv)`
- 도움말은 stdout과 종료 상태 0
- 사용법 오류는 stderr와 종료 상태 2
- import만 했을 때 부작용 없음

```sh
make stage-01 EXERCISE_IMPL=workspace
```

## 2단계: 데이터 모델

관련 문서: [객체와 컬렉션](../../docs/01-language-and-runtime/02-objects-and-collections.md)

구현:

- `Case`, `Result`
- `frozen=True`, `slots=True`
- 가변 `dict` 대신 정렬된 환경 변수 튜플
- `SpecificationError`, `ExecutionError`

```sh
make stage-02 EXERCISE_IMPL=workspace
```

## 3단계: 비교와 실패 표현

관련 문서: [함수, 예외와 타입 경계](../../docs/01-language-and-runtime/03-functions-errors-and-types.md)

구현:

- returncode, stdout, stderr의 정확 비교
- 공백과 줄바꿈도 계약에 포함
- timeout과 출력 초과를 별도 실패로 표현
- 파일·프로세스에 의존하지 않는 순수 함수

```sh
make stage-03 EXERCISE_IMPL=workspace
```

## 4단계: JSON 명세와 실행 시 검증

관련 문서: [파일, 구조화된 데이터와 CLI](../../docs/02-automation/01-files-structured-data-and-cli.md)

구현:

- 비어 있지 않은 JSON 배열
- 허용 필드와 실제 타입
- 중복 이름
- 유한한 양수 timeout
- 양의 output limit
- 사례 파일 기준 `cwd`
- NUL과 `=`을 거부하는 환경 변수 키

```sh
make stage-04 EXERCISE_IMPL=workspace
```

## 5단계: 외부 프로세스 한 건 실행

관련 문서: [외부 프로세스와 수명 관리](../../docs/02-automation/02-subprocess-and-process-lifecycle.md)

먼저 사례 한 건을 실행합니다.

- 명령과 `args`의 인자 경계 보존
- stdin 전달
- stdout·stderr·returncode 수집
- cwd와 환경 override
- 실행 파일 오류는 `ExecutionError`

```sh
make stage-05 EXERCISE_IMPL=workspace
```

## 6단계: 전체 사례와 종료 정책

구현:

- 한 사례가 실패해도 다음 사례 실행
- 입력 순서로 결과 반환
- 통과는 stdout, 실패 세부는 stderr
- 모든 사례 일치 0, 불일치 1, 시작 불가 2

```sh
make stage-06 EXERCISE_IMPL=workspace
```

## 7단계: 프로세스 수명과 출력 상한

구현:

- `start_new_session=True`
- non-blocking stdin·stdout·stderr
- timeout 시 프로세스 그룹에 SIGTERM, 유예 뒤 SIGKILL
- 부모가 먼저 끝나도 파이프를 보유한 자식 추적
- stdout·stderr 각각 `output_limit` 적용

```sh
make stage-07 EXERCISE_IMPL=workspace
```

## 8단계: 병렬 실행과 원자적 보고서

관련 문서: [동시성, 취소와 자원 한계](../../docs/02-automation/03-concurrency-and-cancellation.md)

구현:

- `ThreadPoolExecutor`의 제한된 worker 수
- 완료 순서와 무관하게 입력 순서 보존
- 같은 `Result`에서 JSON·JUnit 생성
- 같은 디렉터리의 임시 파일을 완성한 뒤 `os.replace`
- XML 1.0에서 허용하지 않는 문자를 대체

```sh
make stage-08 EXERCISE_IMPL=workspace
```

## 전체 검사

workspace 전체:

```sh
make exercise-check EXERCISE_IMPL=workspace
```

저장소의 reference, skeleton, 문서와 스크립트까지:

```sh
./verify.sh
```

전체 검증은 정상 구현만 통과시키는 데서 끝나지 않습니다. 결과 채널 비교 누락, 숫자형 검증 오류, 출력 상한 제거, 병렬 결과 순서 역전과 XML 제어 문자 누락을 주입하고 공개 테스트가 각각 거부하는지 확인합니다.

## 완료 기준

- import와 실행 진입점이 분리되어 있습니다.
- 공유 데이터 모델이 불변입니다.
- 명세 오류와 결과 불일치를 구분합니다.
- 세 결과 채널을 정확히 비교합니다.
- 모든 사례를 실행하고 순서를 결정적으로 유지합니다.
- timeout과 출력 초과 뒤 자식 프로세스가 남지 않습니다.
- 병렬 worker가 보고서 파일을 직접 수정하지 않습니다.
- 기존 보고서는 완성된 새 파일이 있을 때만 교체됩니다.

## 자기 설명

- timeout과 출력 상한은 왜 단순한 결과 불일치가 아니라 프로세스 수명 계약입니까?
- 병렬 완료 순서와 사용자에게 보여 줄 결과 순서를 어떻게 분리합니까?

## 검증

```sh
make stage-01 EXERCISE_IMPL=workspace
make exercise-check EXERCISE_IMPL=workspace
./verify.sh
```
