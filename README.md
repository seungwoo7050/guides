# Python 언어, 자동화와 검증 가이드

Python을 처음 사용하는 개발자가 언어의 실행 모델을 이해하고, 파일·프로세스·구조화된 데이터를 다루는 자동화 도구를 만들며, 그 동작을 재현 가능한 검사로 고정하는 과정입니다.

이 저장소는 Python 문법 사전이 아닙니다. 작은 프로그램을 직접 실행하고 실패 경계를 확인한 뒤, 누적 실습 `command-checker`에 같은 원리를 적용합니다. Python으로 웹 애플리케이션이나 데이터 분석을 만드는 과정은 범위에 포함하지 않으며, 알고리즘 이론과 문제 해결은 별도의 알고리즘 가이드가 소유합니다.

## 지원 환경

- Python 3.12 이상
- 학습 문서와 1~6단계의 Python 개념: Python 3.12가 실행되는 환경
- 공식 `prepare`·workspace·`make`·`verify` 흐름: macOS 또는 Linux
- 7~8단계의 프로세스 수명 구현: POSIX 프로세스 그룹과 non-blocking descriptor를 지원하는 macOS 또는 Linux
- Windows native workflow와 process-tree 종료: 지원 범위 밖
- 제3자 Python 패키지: 없음

## 적용과 전체 검증

Overlay ZIP을 저장소 루트에 압축 해제한 뒤 다음 두 명령을 순서대로 실행합니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 source tree나 Git index를 변경하지 않고 `.guide/python/venv`와 fingerprint marker를 준비합니다. 학습자의 `workspace/`는 삭제하거나 덮어쓰지 않습니다. `make clean`도 workspace 전체를 보존하고 source cache와 `.guide/`만 정리합니다. `verify.sh`는 격리 복제본에서 저장소 전체를 검사하며, 알려진 결함을 주입해 공개 테스트가 실제로 거부하는지도 확인합니다.

## 누적 학습 순서

전체 선행지식과 종료 능력은 [`docs/00-roadmap.md`](docs/00-roadmap.md), 세부 구현 계약은 [`exercises/command-checker`](exercises/command-checker/README.md)에 있습니다. 문서를 전부 읽은 뒤 실습을 시작하지 않고, 아래처럼 관련 문서와 단계를 교차해 진행합니다. `examples/`는 의도적으로 없으며 문서의 inline snippet은 독립 실행 예제가 아닙니다. `fixtures/`는 검사 입력과 프로세스 재현 도구이지 예제나 답안이 아닙니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 0 | [로드맵](docs/00-roadmap.md), [실습 계약](exercises/command-checker/README.md) | — | baseline을 확인하고 skeleton을 처음 한 번만 workspace로 복사 | 이후에는 `exercises/command-checker/workspace/`만 수정 | `./prepare.sh`<br>`./verify.sh`<br>`scripts/new-workspace.sh exercises/command-checker` | `reference/`는 열지 않고 1단계 |
| 1 | [실행 환경과 모듈](docs/01-language-and-runtime/01-runtime-and-environment.md) | — | parser와 module/console-script가 공유하는 CLI 계약 구현 | `workspace/command_checker/cli.py`<br>나머지 packaging 파일은 제공 scaffold | `make stage-01 EXERCISE_IMPL=workspace` | 누적 통과를 기록하고 2단계 |
| 2 | [객체와 컬렉션](docs/01-language-and-runtime/02-objects-and-collections.md) | — | 불변 `Case`·`Result`와 환경 표현 구현 | `workspace/command_checker/model.py` | `make stage-02 EXERCISE_IMPL=workspace` | 누적 통과를 기록하고 3단계 |
| 3 | [함수, 예외와 타입 경계](docs/01-language-and-runtime/03-functions-errors-and-types.md) | — | 세 결과 채널의 순수 비교와 실패 표현 구현 | `workspace/command_checker/comparison.py` | `make stage-03 EXERCISE_IMPL=workspace` | 타입 경계는 8단계에서 다시 보고 4단계 |
| 4 | [파일, 구조화된 데이터와 CLI](docs/02-automation/01-files-structured-data-and-cli.md)의 JSON·경로·CLI 부분 | — | JSON을 검증된 사례로 변환 | `workspace/command_checker/specification.py` | `make stage-04 EXERCISE_IMPL=workspace` | 원자적 저장 부분은 8단계에서 다시 보고 5단계 |
| 5 | [반복자, 생성기와 컨텍스트 관리자](docs/01-language-and-runtime/04-iterators-generators-and-context-managers.md), [외부 프로세스와 수명 관리](docs/02-automation/02-subprocess-and-process-lifecycle.md)의 실행 부분 | — | 외부 프로세스 한 건과 세 결과 채널 수집 | `workspace/command_checker/process.py`의 `run_case()` | `make stage-05 EXERCISE_IMPL=workspace` | 같은 reference 파일에 7단계 답도 있으므로 아직 비교하지 않고 6단계 |
| 6 | [실습 6단계](exercises/command-checker/README.md#6단계-전체-사례와-종료-정책) | — | 전체 사례 집계, 표시와 종료 정책 연결 | `workspace/command_checker/runner.py`, `cli.py` | `make stage-06 EXERCISE_IMPL=workspace` | 같은 reference 파일에 8단계 답도 있으므로 아직 비교하지 않고 7단계 |
| 7 | [외부 프로세스와 수명 관리](docs/02-automation/02-subprocess-and-process-lifecycle.md)의 timeout·파이프·프로세스 그룹 부분과 [자원 수명](docs/01-language-and-runtime/04-iterators-generators-and-context-managers.md) 재검토 | — | bounded I/O, timeout, 출력 상한과 프로세스 그룹 정리 | `workspace/command_checker/process.py` | `make stage-07 EXERCISE_IMPL=workspace` | 누적 통과를 기록하고 8단계 |
| 8 | [동시성, 취소와 자원 한계](docs/02-automation/03-concurrency-and-cancellation.md), [재현 가능한 테스트](docs/03-quality/01-testing.md), [프로젝트 구조·패키징·타입](docs/03-quality/02-project-structure-packaging-and-typing.md), [CLI 검사기 설계](docs/03-quality/03-cli-test-runner.md), 파일 문서의 원자적 저장 부분 | — | 제한된 병렬 실행, 보고서, 공개 타입과 설치 계약 완성 | `workspace/command_checker/runner.py`, `reports.py`, `cli.py`와 공개 API | `make stage-08 EXERCISE_IMPL=workspace` | reference를 보기 전에 전체 workspace 검사 |
| 9 | [완료 기준](exercises/command-checker/README.md#완료-기준) | — | 자기 설명과 통합 검사를 마침 | 실패가 드러난 workspace 파일만 수정 | `make exercise-check EXERCISE_IMPL=workspace` | 성공 뒤 처음으로 최종 `reference/`와 비교 → `make install-workspace` → `./verify.sh`; 여기서 종료 |

각 `stage-N`은 1단계부터 N단계까지 다시 검사합니다. `EXERCISE_IMPL`을 생략한 learner-facing `make` 명령도 `workspace`를 선택하며, 정답 검사는 `make reference-check`만 명시적으로 `reference`를 사용합니다. 단계별 expected evidence는 누적 검사 결과와 실패 원인 설명입니다. `reference/`는 단계별 snapshot이 아니라 최종 구현이므로 전체 workspace 검사가 성공한 뒤 비교합니다.
