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

## Part 1. 객체 모델과 책임

1. [프로그램과 타입 모델](01-program-and-type-model.md)
2. [수명·값·소유권](02-lifetime-value-and-ownership.md)
3. [객체 책임 배치](03-assigning-object-responsibilities.md)
4. [상속과 다형성](04-inheritance-and-polymorphism.md)
5. [오류·검증·캐스트](05-errors-validation-and-casts.md)

연결 실습은 `exercises/02-cpp98-systems/object-model/command-service`입니다. 하나의 명령 처리기를 절차형 코드에서 값 소유권, 책임 분리, 다형성, 실패 안전성 단계로 확장합니다.

## Part 2. 제네릭 프로그래밍과 STL

6. [템플릿·반복자·STL](06-templates-iterators-and-stl.md)
7. [STL로 문제 해결](07-solving-problems-with-stl.md)

연결 실습은 다음입니다.

- `exercises/02-cpp98-systems/generic-programming/template-array`
- `exercises/02-cpp98-systems/generic-programming/mini-vector`
- `exercises/02-cpp98-systems/generic-programming/stl-problems`

`mini-vector`는 표준 컨테이너를 다시 만드는 것이 일반 애플리케이션의 권장 설계라는 뜻이 아닙니다. 복사 실패, 부분 생성, 강한 예외 보장과 iterator 계약을 직접 관찰하기 위한 제한된 학습 장치입니다.

## Part 3. 네트워크와 HTTP

8. [POSIX socket과 event loop](08-posix-sockets-and-event-loop.md)
9. [객체지향 HTTP 서버](09-object-oriented-http-server.md)

연결 실습은 다음입니다.

- `exercises/02-cpp98-systems/networking/line-server`
- `exercises/02-cpp98-systems/networking/http-server`

이 과정은 단일 `recv`가 하나의 메시지를 돌려준다고 가정하지 않습니다. 읽기 가능·쓰기 가능 이벤트, 부분 I/O, 연결별 버퍼, close 순서와 timeout을 상태 전이로 관리합니다.

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
