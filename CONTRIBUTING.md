# 기여 안내

설명과 프로그램은 같은 계약을 가리켜야 합니다. 문서에 적은 명령을 깨끗한 검증 환경에서 실행하고, 정상 입력뿐 아니라 오류·경계 입력에서도 설명한 상태와 종료 결과가 관찰되는지 확인합니다.

## 트랙 경계

- `docs/01-modern-cpp/`와 `exercises/01-modern-cpp/`는 C++20 일반 과정입니다.
- `docs/02-cpp98-systems/`와 `exercises/02-cpp98-systems/`는 C++98 시스템 과정입니다.
- `docs/90-appendix/`는 두 트랙의 비교, 플랫폼 차이와 제한된 보충 설명을 담당합니다.
- Modern C++의 기본 도구와 C++98 호환 패턴을 한 문서에서 대안 없이 섞지 않습니다.
- 두 트랙이 공유하는 원리는 roadmap 또는 appendix로 연결하고 같은 정본을 복제하지 않습니다.

## 글을 고칠 때

- 설명은 자연스러운 한국어 경어체로 작성합니다.
- 명령, API, 타입과 식별자는 원래 표기를 유지하고 백틱으로 구분합니다.
- 영문 용어는 표준 문서 검색에 도움이 될 때 첫 등장에 함께 적습니다.
- 개념의 정의보다 상태, 소유권, 실패 조건과 검증 방법을 먼저 명확히 합니다.
- 다른 문서에서 충분히 설명한 내용은 짧게 연결하고 같은 설명을 복사하지 않습니다.
- 지원하지 않는 범위와 환경 제약을 숨기지 않습니다.
- 테스트로 확인하지 않은 성능·안전성·이식성을 단정하지 않습니다.

Modern C++ 문서는 최소한 다음 절을 가집니다.

```text
목표
시작하기 전에
연결 실습
완료 기준
```

나머지 절은 주제에 맞게 구성합니다. 모든 문서에 동일한 목차를 기계적으로 복제하지 않습니다.

## 코드를 고칠 때

- 구현 문제는 `skeleton`, `reference`, 공통 `tests`를 함께 둡니다.
- skeleton은 공개 API와 build graph를 유지한 채 학습할 계약을 `TODO:`로 드러냅니다.
- reference와 공통 tests에는 `TODO:`나 임시 반환값을 남기지 않습니다.
- 같은 테스트 소스를 skeleton과 reference에 연결해 답안의 소스 모양이 아니라 동작 계약을 검사합니다.
- skeleton의 초기 실패는 공통 테스트의 assertion 실패여야 합니다. crash, loader 오류, sanitizer abort 또는 timeout을 예상된 실패로 인정하지 않습니다.
- 정상 결과뿐 아니라 invalid input, 자원 실패, 부분 성공, 종료와 반복 호출을 확인합니다.
- 동시성 테스트는 임의 `sleep`으로 순서를 추측하지 않고 promise, predicate와 barrier 같은 사건을 사용합니다.
- 임시 파일은 고유한 디렉터리에 만들고 종료 경로마다 정리합니다.
- 비밀번호, 인증서, build 결과와 실행 중 생성된 보고서는 추적하지 않습니다.

## 변경 전 준비

새 checkout 또는 구조 변경 뒤 저장소 루트에서 실행합니다.

```sh
./prepare.sh
```

`prepare.sh`는 이동 전 경로, 일회성 마이그레이션 파일, 이전 build 부산물과 실행 조건을 정리합니다. 테스트를 실행하거나 source 구현을 자동 수정하지 않습니다. 이동 전·후 경로에 서로 다른 사용자 변경이 있으면 삭제하지 않고 실패해야 합니다.

운영체제 수준 도구는 자동 설치하지 않습니다. compiler, Make, CMake 또는 Python이 없다면 출력된 설치 예시를 검토한 뒤 사용자가 설치합니다.

## 변경 확인

수정 중에는 필요한 target만 사용할 수 있습니다.

```sh
make check
make modern-start-state
make modern-test
make modern-release
make modern-sanitize
make modern-thread-sanitize
make cpp98-verify
```

최종 확인은 저장소 루트의 정본 진입점 하나로 수행합니다.

```sh
./verify.sh
```

`verify.sh`는 임시 복사본에서 문서, 두 트랙, 실패 주입, 지원되는 sanitizer와 compiler matrix를 검사합니다. 성공·실패·중단 뒤 원본 저장소의 build/cache 부산물을 제거하고 검증 전후 Git 상태가 같은지 확인합니다.

환경에서 sanitizer를 반드시 요구하려면 다음처럼 실행합니다.

```sh
VERIFY_SANITIZERS=required VERIFY_TSAN=required VERIFY_STRICT=1 ./verify.sh
```

커밋 전에는 추적 범위와 공백 오류를 다시 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

## 검증기를 고칠 때

검증기가 정상 reference를 통과시키는 것만으로 충분하지 않습니다.

- Modern skeleton 네 개가 exit code `1`과 공통 test failure 요약으로 실패하는지 확인합니다.
- C++98의 allocation failure, non-virtual destruction, commit failure, compile-fail, 반복 연결과 네트워크 부하 계약을 유지합니다.
- 알려진 잘못된 구현이 통과하면 테스트 또는 검증기 결함으로 취급합니다.
- compiler나 sanitizer가 지원되지 않는 상황과 실제 코드 실패를 구분합니다.
- cleanup은 이름 목록만 믿지 않고 build 디렉터리, object/archive와 실행 바이너리 형식까지 검사합니다.
- 검증 스크립트가 원본 source, learner workspace 또는 추적 fixture를 수정·삭제하지 않는지 확인합니다.

## 커밋

제목은 Conventional Commits 형식을 사용하고, 본문은 변경 이유나 검증 한계를 더 설명할 때 작성합니다.

```text
docs(modern-cpp): 이동 뒤 상태 계약 보완
test(cpp98): 부분 쓰기 경계값 검사 추가
fix(cmake): 공개 표준 요구사항을 caller에 전파
```

문서와 해당 계약을 검증하는 코드는 같은 커밋에 넣을 수 있습니다. 서로 독립적인 기능과 수정은 나누어 기록합니다.
