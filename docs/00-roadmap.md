# Python 가이드 로드맵

## 학습 목표

이 가이드는 Python 문법을 한 번 훑는 데서 끝나지 않습니다. 독자가 다음 반복을 스스로 돌릴 수 있게 하는 것이 목표입니다.

```text
작은 계약을 정한다
→ Python 코드로 구현한다
→ 파일·프로세스·시간 같은 외부 경계를 분리한다
→ 실패와 경계 조건을 자동 검사한다
→ 결과를 재현 가능한 형태로 남긴다
```

Python은 이 저장소에서 두 역할을 가집니다.

1. 반복 작업과 검증 절차를 구현하는 자동화 언어
2. 운영체제·네트워크·컴퓨터 구조·알고리즘 가이드의 작은 상태 모델을 작성하는 공통 실습 언어

## 대상 독자

Python 경험은 필요하지 않습니다. 변수, 조건, 반복과 함수라는 일반적인 프로그래밍 개념이 완전히 처음이어도 1부에서 필요한 만큼 다룹니다. 다만 터미널에서 현재 디렉터리를 확인하고 파일을 편집할 수 있어야 합니다.

이 가이드를 시작하기 위해 C나 Java를 먼저 배울 필요는 없습니다.

## 선행 개념

- 터미널에서 현재 디렉터리를 확인하고 UTF-8 텍스트 파일을 편집할 수 있으면 시작할 수 있습니다.
- 변수·조건·반복·함수는 1부에서 다루므로 다른 프로그래밍 언어 경험은 요구하지 않습니다.

## 지원 환경

- Python 3.12 이상
- UTF-8 텍스트 환경
- 일반 문서와 1~6단계: Python이 실행되는 환경
- 프로세스 그룹과 POSIX 신호를 사용하는 7~8단계: macOS 또는 Linux
- 제3자 Python 패키지: 없음

저장소 전체 준비와 검증은 루트에서 실행합니다.

```sh
./prepare.sh
./verify.sh
```

## 종료 능력

모든 필수 경로를 완료하면 다음을 할 수 있어야 합니다.

- 스크립트 실행과 모듈 실행을 구분하고 올바른 진입점을 만든다.
- Python의 이름·객체·가변성·컬렉션 비용을 설명한다.
- 함수 계약, 예외 경계와 타입 힌트의 역할을 구분한다.
- 반복자·생성기·컨텍스트 관리자로 데이터와 자원 수명을 표현한다.
- `pathlib`, JSON, CSV와 임시 파일을 사용해 안전한 CLI를 만든다.
- 외부 명령을 인자 경계를 보존한 채 실행하고 결과 채널을 검사한다.
- timeout, 출력 상한, 취소와 자식 프로세스 정리를 설계한다.
- 단위·통합·종단 간 검사를 분리하고 결정적인 실패 사례를 만든다.
- 작은 Python 프로젝트의 모듈, 타입, 설정과 검증 진입점을 구성한다.

## 범위

### 이 저장소가 소유하는 내용

- Python 실행 모델과 표준 라이브러리 중심 자동화
- 파일·구조화된 데이터·CLI 계약
- 외부 프로세스와 자원 수명
- Python 코드의 테스트·타입·프로젝트 구조
- CS 실습용 결정적 상태 모델을 작성하는 데 필요한 Python 기반

### 다른 가이드가 소유하는 내용

- 알고리즘의 정확성·복잡도·설계 기법: `guide-algorithms`
- 셸 확장·따옴표·파이프라인 언어: `guide-shell-scripting`
- 프로세스·파일 디스크립터의 운영체제 의미: `guide-unix-systems`, `guide-operating-systems`
- Python 웹 프레임워크, 데이터 과학과 머신러닝: 이 과정의 범위 밖

알고리즘에서 자주 쓰는 Python 도구는 알고리즘 가이드의 Python 구현 프로필에서 다룹니다. 이 저장소는 `heapq`나 `bisect`를 알고리즘 이론 대신 다시 가르치지 않습니다.

## 필수 학습 지도

### 1부: 언어와 실행 모델

| 순서 | 문서 | 연결 실습 |
|---:|---|---:|
| 1 | [실행 환경과 모듈](01-language-and-runtime/01-runtime-and-environment.md) | 1단계 |
| 2 | [객체와 컬렉션](01-language-and-runtime/02-objects-and-collections.md) | 2단계 |
| 3 | [함수, 예외와 타입 경계](01-language-and-runtime/03-functions-errors-and-types.md) | 3단계 |
| 4 | [반복자, 생성기와 컨텍스트 관리자](01-language-and-runtime/04-iterators-generators-and-context-managers.md) | 3~4단계 |

### 2부: 자동화와 프로세스

| 순서 | 문서 | 연결 실습 |
|---:|---|---:|
| 5 | [파일, 구조화된 데이터와 CLI](02-automation/01-files-structured-data-and-cli.md) | 4단계 |
| 6 | [외부 프로세스와 수명 관리](02-automation/02-subprocess-and-process-lifecycle.md) | 5·7단계 |
| 7 | [동시성, 취소와 자원 한계](02-automation/03-concurrency-and-cancellation.md) | 7·8단계 |

### 3부: 품질과 검증

| 순서 | 문서 | 연결 실습 |
|---:|---|---:|
| 8 | [재현 가능한 테스트](03-quality/01-testing.md) | 전 단계 |
| 9 | [프로젝트 구조, 패키징과 타입 검사](03-quality/02-project-structure-packaging-and-typing.md) | 1·8단계 |
| 10 | [CLI 검사기 설계](03-quality/03-cli-test-runner.md) | 전체 |

누적 실습의 전체 계약은 [`command-checker`](../exercises/command-checker/README.md)에서 확인합니다.

## 선택 학습 지도

### CS 상태 모델을 빨리 작성하려는 경우

다음 순서만 먼저 완료해도 됩니다.

```text
실행 환경과 모듈
→ 객체와 컬렉션
→ 함수, 예외와 타입 경계
→ 반복자와 생성기
→ 재현 가능한 테스트
```

이후 다른 CS 가이드의 Python 모델을 진행하다가 파일·프로세스가 필요해질 때 2부로 돌아옵니다.

### 자동화 도구를 만들려는 경우

모든 문서를 순서대로 읽고 `command-checker`를 1단계부터 진행합니다. 7단계 이전에는 병렬성이나 복잡한 프로세스 수명 제어를 먼저 넣지 않습니다.

## 범위 밖

- 웹 프레임워크, 데이터 과학, 머신러닝과 제3자 package 생태계는 이 가이드의 필수 범위가 아닙니다.
- 알고리즘 이론, 셸 언어와 운영체제 내부 의미는 각 소유 가이드에서 다룹니다.
- 이 저장소의 `## 범위` 절은 소유권 경계를 더 자세히 설명합니다.

## 학습 방법

각 단계에서 다음 순서를 유지합니다.

```text
문서의 계약을 읽는다
→ skeleton을 workspace로 복사한다
→ 현재 단계만 구현한다
→ 현재 단계까지의 누적 검사를 실행한다
→ 실패 원인을 설명한 뒤 수정한다
→ 마지막에 reference와 비교한다
```

작업 공간 생성:

```sh
scripts/new-workspace.sh exercises/command-checker
```

기존 `workspace/`는 자동으로 덮어쓰지 않습니다.

## 자동화의 한계

- 자동 검사는 POSIX process group을 사용하는 macOS·Linux reference와 결정적 fixture를 검증합니다.
- 모든 운영체제의 scheduler timing, Windows native process tree와 외부 executable의 동작을 증명하지 않습니다.
- reference 통과는 학습자의 설계 설명과 단계별 실패 분석을 대신하지 않습니다.
