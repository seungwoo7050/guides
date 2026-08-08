# Python 언어, 자동화와 검증 가이드

Python을 처음 사용하는 개발자가 언어의 실행 모델을 이해하고, 파일·프로세스·구조화된 데이터를 다루는 자동화 도구를 만들며, 그 동작을 재현 가능한 검사로 고정하는 과정입니다.

이 저장소는 Python 문법 사전이 아닙니다. 작은 프로그램을 직접 실행하고 실패 경계를 확인한 뒤, 누적 실습 `command-checker`에 같은 원리를 적용합니다. Python으로 웹 애플리케이션이나 데이터 분석을 만드는 과정은 범위에 포함하지 않으며, 알고리즘 이론과 문제 해결은 별도의 알고리즘 가이드가 소유합니다.

## 지원 환경

- Python 3.12 이상
- 일반 문서와 1~6단계 실습: Python을 실행할 수 있는 환경
- 프로세스 그룹·신호를 사용하는 7~8단계: macOS 또는 Linux
- 제3자 Python 패키지: 없음

## 적용과 전체 검증

Overlay ZIP을 저장소 루트에 압축 해제한 뒤 다음 두 명령을 순서대로 실행합니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 source tree나 Git index를 변경하지 않고 `.guide/python/venv`와 fingerprint marker를 준비합니다. 학습자의 `workspace/`는 삭제하거나 덮어쓰지 않습니다. `verify.sh`는 격리 복제본에서 저장소 전체를 검사하며, 알려진 결함을 주입해 공개 테스트가 실제로 거부하는지도 확인합니다.

## 읽기 순서

전체 경로, 선행지식과 종료 능력은 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 있습니다.

### 1. 언어와 실행 모델

1. [실행 환경과 모듈](docs/01-language-and-runtime/01-runtime-and-environment.md)
2. [객체와 컬렉션](docs/01-language-and-runtime/02-objects-and-collections.md)
3. [함수, 예외와 타입 경계](docs/01-language-and-runtime/03-functions-errors-and-types.md)
4. [반복자, 생성기와 컨텍스트 관리자](docs/01-language-and-runtime/04-iterators-generators-and-context-managers.md)

### 2. 자동화와 프로세스

1. [파일, 구조화된 데이터와 CLI](docs/02-automation/01-files-structured-data-and-cli.md)
2. [외부 프로세스와 수명 관리](docs/02-automation/02-subprocess-and-process-lifecycle.md)
3. [동시성, 취소와 자원 한계](docs/02-automation/03-concurrency-and-cancellation.md)

### 3. 품질과 검증

1. [재현 가능한 테스트](docs/03-quality/01-testing.md)
2. [프로젝트 구조, 패키징과 타입 검사](docs/03-quality/02-project-structure-packaging-and-typing.md)
3. [CLI 검사기 설계](docs/03-quality/03-cli-test-runner.md)

## 누적 실습

[`exercises/command-checker`](exercises/command-checker/README.md)는 JSON에 기록한 사례로 외부 CLI를 실행하고 `returncode`, `stdout`, `stderr`를 검사합니다. 마지막 단계에서는 제한 시간, 출력 상한, 자식 프로세스 정리, 병렬 실행과 원자적 JSON·JUnit 보고서까지 다룹니다.

| 단계 | 핵심 책임 | 검사 명령 |
|---:|---|---|
| 1 | 패키지 실행과 CLI 진입점 | `make stage-01 EXERCISE_IMPL=workspace` |
| 2 | 불변 데이터 모델과 컬렉션 계약 | `make stage-02 EXERCISE_IMPL=workspace` |
| 3 | 순수 비교 함수와 오류 표현 | `make stage-03 EXERCISE_IMPL=workspace` |
| 4 | JSON 명세와 실행 시 검증 | `make stage-04 EXERCISE_IMPL=workspace` |
| 5 | 외부 프로세스 한 건 실행 | `make stage-05 EXERCISE_IMPL=workspace` |
| 6 | 전체 사례 집계와 종료 정책 | `make stage-06 EXERCISE_IMPL=workspace` |
| 7 | timeout·출력 상한·프로세스 그룹 | `make stage-07 EXERCISE_IMPL=workspace` |
| 8 | 병렬 실행과 원자적 보고서 | `make stage-08 EXERCISE_IMPL=workspace` |

작업 공간은 다음처럼 만듭니다.

```sh
scripts/new-workspace.sh exercises/command-checker
```

이 스크립트는 기존 `workspace/`를 절대 덮어쓰지 않습니다.
