# 기여 안내

문서, 공개 계약, 기준 구현과 검사는 같은 동작을 설명해야 합니다. 변경 전에는 관련 문서와 연습문제를 함께 읽고, 변경 후에는 정상 사례뿐 아니라 경계값·실패·정리 경로까지 다시 확인합니다.

## 구조 원칙

- 필수 학습 내용은 `docs/`와 `exercises/` 안에서 완결합니다.
- `docs/00-roadmap.md`의 학습 순서와 실제 디렉터리 구조를 일치시킵니다.
- 완성 동작을 관찰하는 작은 프로그램은 `examples/`에 두되, exercise 답안을 반복하지 않는 좁은 실험으로 제한합니다.
- 학습자가 구현해야 하는 문제는 `exercises/`에 둡니다.
- 연습문제는 `README.md`, `skeleton/`, `reference/README.md`, `reference/`, `tests/`, `Makefile`을 기본 구성으로 제공합니다.
- `skeleton/`은 변경하지 않는 canonical 초기 상태로, 경고 없이 컴파일되어야 하지만 초기 동작 검사에는 실패해야 합니다.
- 학습자는 `scripts/new-workspace.sh exercises/<part>/<exercise>`로 만든 Git 비추적 `workspace/`만 수정합니다. 생성기는 기존 경로나 symlink를 덮어쓰지 않아야 합니다.
- `reference/`는 유일한 정답이 아니라 공개 계약을 만족하는 비교 구현이며, 학습자가 workspace 검증을 끝낸 뒤에만 봅니다.
- 필수 파일을 다른 디렉터리의 숨은 자료나 작업용 스크립트에 의존시키지 않습니다.

## 글을 고칠 때

- 설명은 자연스러운 한국어 경어체로 작성합니다.
- 명령, API, 타입과 식별자는 원래 표기를 유지하고 백틱으로 구분합니다.
- 새 개념은 앞 장에서 이미 배운 개념만 사용하거나 필요한 선행지식을 명시합니다.
- 정상 경로만 설명하지 말고 소유권, 부분 성공, 실패 뒤 상태와 비보장 범위를 함께 적습니다.
- 다른 문서에서 충분히 설명한 내용은 짧게 연결하고 같은 설명을 복사하지 않습니다.
- 테스트하지 않은 성능, 이식성이나 안정성을 단정하지 않습니다.
- 문서 이동이나 이름 변경 뒤에는 roadmap, README와 상대 링크를 모두 갱신합니다.

## 코드를 고칠 때

- C99와 해당 문제에서 선언한 POSIX 기능 기준을 지킵니다.
- 기본 빌드는 `-Wall -Wextra -Wpedantic -Werror`를 통과해야 합니다.
- 공개 헤더는 필요한 표준 헤더를 직접 포함하고 C++과의 연결이 필요하면 경계를 명시합니다.
- 출력 매개변수는 성공한 뒤에만 변경하는 계약을 우선합니다.
- 크기 계산은 할당이나 덧셈 전에 overflow를 검사합니다.
- 소유 자원은 모든 반환 경로에서 한 번만 정리합니다.
- 프로세스·시그널·스레드 검사는 작은 입력만으로 숨는 교착과 경쟁을 재현할 수 있어야 합니다.
- 검사기는 기준 구현의 문구나 소스 구조가 아니라 관찰 가능한 계약을 확인해야 합니다.

## 구현 순서 annotation을 고칠 때

- `Implementation N` 표식은 Git 이력이나 runtime 순서가 아니라 독립 example/reference 전체의 학습용 권장 구현 순서입니다.
- 번호는 파일마다 다시 시작하지 않고 하나의 project scope에서 `1`부터 연속시킵니다. 하위 단계 `N-M`을 쓰면 부모와 하위 번호도 연속이어야 합니다.
- C 브랜치에는 project generator나 dependency bootstrap이 없으므로 현재 `Implementation 0` scope는 없습니다. `cc`, `ar`, `make`, sanitizer와 Readline probe는 build·검증 절차입니다.
- 표식은 완성 example source와 exercise `reference/` source에만 둡니다. skeleton, 공개 test/helper, fixture, validator와 generated artifact에는 두지 않습니다. `examples/text-checks/tests/check.sh`는 검사 구현 자체가 학습 대상인 명시적 예외입니다.
- 각 scope의 `README.md` 또는 `reference/README.md`에 `## 구현 순서` index를 두고 source 표식과 정확히 일치시킵니다.
- 책임, 상태·자원 소유자, 불변식, 실패 상태와 다음 단계만 설명하고 문법을 줄마다 번역하지 않습니다.

## 연습문제를 추가할 때

최소한 다음 target을 제공합니다.

```sh
make exercise-build
make exercise-test
make reference-test
make exercise-sanitize
make reference-sanitize
make sanitize
make clean
```

동시성 문제는 지원 가능한 경우 다음도 제공합니다.

```sh
make thread-sanitize
```

초기 skeleton의 계약은 두 단계로 확인합니다.

1. `make exercise-build EXERCISE_IMPL=skeleton`이 성공해야 합니다.
2. 완성되지 않은 상태이므로 `make exercise-test EXERCISE_IMPL=skeleton`은 실패해야 합니다.

컴파일 오류를 “초기 skeleton 실패”로 인정하지 않습니다. skeleton은 학습자가 구현을 시작할 수 있는 유효한 프로그램이어야 합니다.

학습자 명령의 기본 구현은 `workspace`입니다. `make exercise-test`와 `make sanitize`가 reference를 검사해 미완성 workspace에 false green을 만들지 않도록 하고, 저장소 전체 검증은 `reference-test`와 `reference-sanitize`를 명시합니다.

검사는 다음 범주를 가능한 범위에서 포함합니다.

- 대표적인 정상 입력
- 빈 값, 0과 경계값
- 잘못된 입력과 출력 매개변수 보존
- 할당·시스템 호출의 중간 실패
- 반복 호출과 정리의 멱등성
- timeout이 필요한 교착·종료 조건
- sanitizer가 확인할 메모리·정의되지 않은 동작·data race

## 전체 변경 확인

최종 저장소 상태를 준비하고 전체 검증을 실행합니다.

```sh
./prepare.sh
./verify.sh
```

선택 기능이 없는 환경에서의 skip도 실패로 취급하려면 다음을 사용합니다.

```sh
VERIFY_REQUIRE_OPTIONAL=1 ./verify.sh
```

작업 중 좁은 검사를 반복할 때는 다음 target을 사용할 수 있습니다.

```sh
make check
make quality-check
make sanitize
make thread-sanitize
make clean
```

마지막으로 추적 범위와 공백 오류를 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

검증 로그는 `verify.sh`가 출력하는 저장소 밖 `VERIFY LOG` 경로에서 확인합니다. `make-out.txt`, `tree.txt`, 빌드 산출물과 일회성 작업 로그는 커밋하지 않습니다.

## 커밋

제목은 Conventional Commits 형식을 사용하고, 본문은 변경 이유와 검증 근거가 더 필요할 때 작성합니다.

```text
docs(foundations): 입력 오류 분류 보완
test(process): 큰 파이프 전송 검사 추가
fix(exercise): 할당 실패 뒤 벡터 상태 보존
```

문서와 그 계약을 검증하는 코드는 같은 커밋에 포함할 수 있습니다. 서로 독립적인 학습 단계와 수정은 나누어 기록합니다.
