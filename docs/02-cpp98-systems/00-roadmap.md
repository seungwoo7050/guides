# C++98 시스템 프로그래밍 트랙

## 이 트랙의 목적

이 트랙은 C++98 제약 아래 객체 수명과 STL을 익히고, POSIX 비차단 서버까지 확장합니다. Modern C++의 편의 기능을 흉내 내는 것이 아니라 사용할 수 없는 기능이 무엇인지 알고, 그 제약 안에서 소유권과 실패 경계를 명시적으로 설계합니다.

문서와 exercise의 정본은 모두 `02-cpp98-systems` 아래에 있습니다. 이동 전 평면 경로를 별도 복사본으로 유지하지 않습니다.

## 시작하기 전에

- C 또는 다른 언어로 여러 파일 프로그램을 작성해 봤습니다.
- 포인터, 동적 메모리와 기본 자료구조를 알고 있습니다.
- Unix 계열 터미널과 Makefile을 사용할 수 있습니다.
- `-std=c++98`과 POSIX 환경이라는 제약을 의도적으로 받아들입니다.

새 checkout이나 overlay 적용 뒤에는 저장소 루트에서 준비합니다.

```sh
./prepare.sh
```

## 안전한 학습 작업 공간

정본 skeleton은 repository baseline 검증의 입력이므로 직접 수정하지 않습니다. 저장소 루트에서 다음 명령으로 non-overwriting 학습 공간을 만든 뒤 `.workspace/02-cpp98-systems` 안의 `skeleton/`만 수정합니다.

```sh
make workspace TRACK=cpp98
```

각 단계의 learner 검증은 다음 형식을 사용합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=<track-relative-leaf>
```

`make observe`가 있는 단계에서는 이를 선택적 black-box oracle로만 사용합니다. 결과를 먼저 예상하고 reference source는 열지 않은 채 실행 결과만 관찰합니다. learner 검증을 통과한 뒤에만 reference source의 책임 배치와 실패 뒤 상태를 비교합니다.

## Part 1. 객체 모델과 책임

하나의 명령 처리기를 다음 다섯 물리 단계로 확장합니다.

1. [프로그램과 타입 모델](01-program-and-type-model.md) → [`01-procedural`](../../exercises/02-cpp98-systems/object-model/command-service/01-procedural/README.md)
2. [수명·값·소유권](02-lifetime-value-and-ownership.md) → [`02-value-ownership`](../../exercises/02-cpp98-systems/object-model/command-service/02-value-ownership/README.md)
3. [객체 책임 배치](03-assigning-object-responsibilities.md) → [`03-responsibilities`](../../exercises/02-cpp98-systems/object-model/command-service/03-responsibilities/README.md)
4. [상속과 다형성](04-inheritance-and-polymorphism.md) → [`04-polymorphism`](../../exercises/02-cpp98-systems/object-model/command-service/04-polymorphism/README.md)
5. [오류·검증·캐스트](05-errors-validation-and-casts.md) → [`05-errors`](../../exercises/02-cpp98-systems/object-model/command-service/05-errors/README.md)

## Part 2. 제네릭 프로그래밍과 STL

6. [템플릿·반복자·STL](06-templates-iterators-and-stl.md)
7. [STL로 문제 해결](07-solving-problems-with-stl.md)

연결 실습은 [template-array](../../exercises/02-cpp98-systems/generic-programming/template-array/README.md)와 [STL 세 문제](../../exercises/02-cpp98-systems/generic-programming/stl-problems/README.md)입니다. [mini-vector](../../exercises/02-cpp98-systems/generic-programming/mini-vector/README.md)는 [STL 내부 구조 appendix](../90-appendix/04-stl-internals.md)와 연결된 **선택 심화**입니다. 표준 컨테이너를 다시 만드는 것이 일반 애플리케이션의 권장 설계라는 뜻이 아니라 복사 실패, 부분 생성, 강한 예외 보장과 iterator 계약을 직접 관찰하기 위한 제한된 학습 장치입니다.

## Part 3. 네트워크와 HTTP

8. [POSIX socket과 event loop](08-posix-sockets-and-event-loop.md)
9. [객체지향 HTTP 서버](09-object-oriented-http-server.md)

연결 실습은 [line-server](../../exercises/02-cpp98-systems/networking/line-server/README.md)와 [5단계 HTTP 서버](../../exercises/02-cpp98-systems/networking/http-server/README.md)입니다. HTTP 실습은 `01-parser` → `02-config-router` → `03-nonblocking-server` → `04-cgi-process` → `05-integrated-server`의 실제 디렉터리 순서를 따릅니다.

이 과정은 단일 `recv`가 하나의 메시지를 돌려준다고 가정하지 않습니다. 읽기 가능·쓰기 가능 이벤트, 부분 I/O, 연결별 버퍼, close 순서와 timeout을 상태 전이로 관리합니다.

## 문서와 실습의 ordered mapping

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---|---|---|---|---|---|---|
| 1 | 01 프로그램·타입 | 선택 black-box oracle | `01-procedural` | `.workspace/02-cpp98-systems/object-model/command-service/01-procedural/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/01-procedural` | `reference/` → 2 |
| 2 | 02 수명·소유권 | 선택 black-box oracle | `02-value-ownership` | `.workspace/02-cpp98-systems/object-model/command-service/02-value-ownership/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/02-value-ownership` | `reference/` → 3 |
| 3 | 03 책임 | legacy 시작점 | `03-responsibilities` | `.workspace/02-cpp98-systems/object-model/command-service/03-responsibilities/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/03-responsibilities` | `reference/` → 4 |
| 4 | 04 다형성 | 선택 black-box oracle | `04-polymorphism` | `.workspace/02-cpp98-systems/object-model/command-service/04-polymorphism/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/04-polymorphism` | `reference/` → 5 |
| 5 | 05 오류 | 선택 black-box oracle | `05-errors` | `.workspace/02-cpp98-systems/object-model/command-service/05-errors/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/05-errors` | `reference/` → 6 |
| 6 | 06 템플릿·반복자·STL | template-array demo | template-array; mini-vector는 선택 심화 | `.workspace/02-cpp98-systems/generic-programming/<exercise>/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=generic-programming/<exercise>` | 각 `reference/` → 7 |
| 7 | 07 STL 문제 해결 | 세 선택 black-box oracle | date-lookup → rpn → sorter | `.workspace/02-cpp98-systems/generic-programming/stl-problems/<problem>/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=generic-programming/stl-problems/<problem>` | 각 `reference/` → 8 |
| 8 | 08 POSIX socket·event loop | 선택 black-box line server | line-server | `.workspace/02-cpp98-systems/networking/line-server/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=networking/line-server` | `reference/` → 9 |
| 9 | 09 객체지향 HTTP 서버 | parser/router demo와 나머지 선택 black-box oracle | HTTP 01 → 02 → 03 → 04 → 05 | `.workspace/02-cpp98-systems/networking/http-server/<stage>/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=networking/http-server/<stage>` | 각 `reference/`, 05 뒤 C++98 종료 |

## Modern C++ 트랙과의 관계

Modern C++을 먼저 배웠다면 [Modern C++ → C++98 대응표](../90-appendix/01-modern-to-cpp98-crosswalk.md)를 사용합니다.

| Modern C++ 기본 | C++98 트랙의 대응 |
|---|---|
| `unique_ptr` | 복사 금지 + 명시적 소멸자 + 소유자 문서화 |
| 이동 의미론 | 복사를 금지하거나 깊은 복사를 구현 |
| `override` | 정확한 시그니처와 테스트로 검증 |
| `enum class` | 이름 충돌과 암묵 변환을 별도 규칙으로 통제 |
| lambda | 함수 객체·함수 포인터·멤버 함수 포인터 |
| range-for | 명시적 iterator loop |
| `optional`, `variant` | 상태 + 출력 매개변수 또는 별도 결과 타입 |
| `jthread`, stop token | POSIX 또는 프로젝트별 종료 플래그와 명시적 join |

Modern 기능을 사용할 수 없는 것이 수명과 실패 계약을 생략할 이유는 아닙니다.

## 검증

최종 저장소 전체는 루트에서 한 번에 검사합니다.

```sh
./verify.sh
```

C++98 트랙에는 다음이 포함됩니다.

- 모든 skeleton의 공개 build graph
- object model과 STL reference 계약
- allocation·copy·commit 실패 주입
- compile-fail과 non-virtual destruction 검사
- 분할 프레임, 부분 I/O와 peer close
- 느린 독자에 대한 backpressure
- 반복 연결의 파일 디스크립터 정리
- line server 동시 연결 부하
- HTTP parser·router·CGI·통합 서버의 정상·실패 경로
- 지원 환경의 ASan·UBSan

수정 중인 영역만 빠르게 확인할 때는 다음을 사용할 수 있습니다.

```sh
make skeleton-build
make test
make failure-check
make sanitize
make cpp98-verify
```

개별 target은 개발 피드백용이며 최종 완료 판정은 `./verify.sh`가 담당합니다.

## 완료 기준

- 객체 복사·대입·소멸 계약을 설명합니다.
- 공개 API에서 소유자와 비소유자를 구분합니다.
- 컨테이너 선택을 접근 패턴, 복잡도와 iterator 무효화로 정당화합니다.
- socket과 event registration의 소유자가 누구인지 명시합니다.
- 부분 읽기·쓰기, peer close, timeout과 protocol 오류를 서로 다른 상태로 처리합니다.
- 서버 종료 뒤 열린 파일 디스크립터와 남은 child process가 없습니다.
- 실패 주입이 reference의 보장을 실제로 구분하는 이유를 설명합니다.
