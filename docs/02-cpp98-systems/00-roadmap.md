# C++98 시스템 프로그래밍 트랙

## 트랙 목적

이 트랙에서는 C++98 제약 안에서 객체 수명과 STL을 익힌 뒤 POSIX 논블로킹 서버까지 확장합니다. Modern C++ 기능을 흉내 내는 것이 아니라 사용할 수 없는 기능을 분명히 파악하고, 그 제약 안에서 소유권과 실패 경계를 명시적으로 설계합니다.

문서와 실습의 기준 경로는 모두 `02-cpp98-systems` 아래에 있습니다. 이전의 평면 경로를 별도 복사본으로 유지하지 않습니다.

## 시작하기 전에

- C 또는 다른 언어로 여러 파일로 구성된 프로그램을 작성해 봤습니다.
- 포인터, 동적 메모리, 기본 자료구조를 이해합니다.
- Unix 계열 터미널과 Makefile을 사용할 수 있습니다.
- `-std=c++98`과 POSIX 환경 제약을 의도적으로 적용합니다.

새로 체크아웃했거나 오버레이를 적용했다면 저장소 루트에서 다음 명령을 실행합니다.

```sh
./prepare.sh
```

## 안전한 학습 작업 공간

배포된 `skeleton/`은 저장소 기준 상태를 검증할 때 사용하므로 직접 수정하지 않습니다. 저장소 루트에서 다음 명령으로 기존 파일을 덮어쓰지 않는 학습 공간을 만든 뒤 `.workspace/02-cpp98-systems` 안의 `skeleton/`만 수정합니다.

```sh
make workspace TRACK=cpp98
```

각 단계의 학습자 구현은 다음 형식으로 검사합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=<track-relative-leaf>
```

`make observe`가 제공되는 단계에서는 이를 선택적인 블랙박스 기준 프로그램으로만 사용합니다. 먼저 예상 결과를 적고 `reference/` 소스는 열지 않은 채 입출력만 관찰합니다. 학습자 구현 검증을 통과한 뒤에만 참조 구현의 책임 배치와 실패 후 상태를 비교합니다.

## Part 1. 객체 모델과 책임

하나의 명령 처리기를 다음 다섯 단계로 확장합니다.

1. [프로그램과 타입 모델](01-program-and-type-model.md) → [`01-procedural`](../../exercises/02-cpp98-systems/object-model/command-service/01-procedural/README.md)
2. [수명·값·소유권](02-lifetime-value-and-ownership.md) → [`02-value-ownership`](../../exercises/02-cpp98-systems/object-model/command-service/02-value-ownership/README.md)
3. [객체 책임 배치](03-assigning-object-responsibilities.md) → [`03-responsibilities`](../../exercises/02-cpp98-systems/object-model/command-service/03-responsibilities/README.md)
4. [상속과 다형성](04-inheritance-and-polymorphism.md) → [`04-polymorphism`](../../exercises/02-cpp98-systems/object-model/command-service/04-polymorphism/README.md)
5. [오류·검증·캐스트](05-errors-validation-and-casts.md) → [`05-errors`](../../exercises/02-cpp98-systems/object-model/command-service/05-errors/README.md)

## Part 2. 제네릭 프로그래밍과 STL

6. [템플릿·반복자·STL](06-templates-iterators-and-stl.md)
7. [STL로 문제 해결](07-solving-problems-with-stl.md)

연결 실습은 [template-array](../../exercises/02-cpp98-systems/generic-programming/template-array/README.md)와 [STL 세 문제](../../exercises/02-cpp98-systems/generic-programming/stl-problems/README.md)입니다. [mini-vector](../../exercises/02-cpp98-systems/generic-programming/mini-vector/README.md)는 [STL 내부 구조 부록](../90-appendix/04-stl-internals.md)과 연결된 **선택 심화 실습**입니다.

`mini-vector`는 표준 컨테이너를 직접 다시 구현하는 방식을 일반 애플리케이션에 권장하기 위한 실습이 아닙니다. 복사 실패, 일부 원소만 생성된 상태, 강한 예외 보장, 반복자 규칙을 제한된 구현 안에서 직접 관찰하기 위한 학습 장치입니다.

## Part 3. 네트워크와 HTTP

8. [POSIX 소켓과 이벤트 루프](08-posix-sockets-and-event-loop.md)
9. [객체지향 HTTP 서버](09-object-oriented-http-server.md)

연결 실습은 [line-server](../../exercises/02-cpp98-systems/networking/line-server/README.md)와 [5단계 HTTP 서버](../../exercises/02-cpp98-systems/networking/http-server/README.md)입니다. HTTP 실습은 `01-parser` → `02-config-router` → `03-nonblocking-server` → `04-cgi-process` → `05-integrated-server`의 실제 디렉터리 순서를 따릅니다.

이 과정에서는 `recv` 한 번이 메시지 하나를 정확히 반환한다고 가정하지 않습니다. 읽기 가능·쓰기 가능 이벤트, 부분 입출력, 연결별 버퍼, 연결 종료 순서, 시간 제한을 상태 전이로 관리합니다.

## 문서와 실습 순서

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 후 비교·다음 단계 |
|---|---|---|---|---|---|---|
| 1 | 01 프로그램·타입 | 선택적 블랙박스 실행 | `01-procedural` | `.workspace/02-cpp98-systems/object-model/command-service/01-procedural/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/01-procedural` | `reference/`와 비교 → 2 |
| 2 | 02 수명·소유권 | 선택적 블랙박스 실행 | `02-value-ownership` | `.workspace/02-cpp98-systems/object-model/command-service/02-value-ownership/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/02-value-ownership` | `reference/`와 비교 → 3 |
| 3 | 03 책임 | 기존 구조 관찰 | `03-responsibilities` | `.workspace/02-cpp98-systems/object-model/command-service/03-responsibilities/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/03-responsibilities` | `reference/`와 비교 → 4 |
| 4 | 04 다형성 | 선택적 블랙박스 실행 | `04-polymorphism` | `.workspace/02-cpp98-systems/object-model/command-service/04-polymorphism/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/04-polymorphism` | `reference/`와 비교 → 5 |
| 5 | 05 오류 | 선택적 블랙박스 실행 | `05-errors` | `.workspace/02-cpp98-systems/object-model/command-service/05-errors/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/05-errors` | `reference/`와 비교 → 6 |
| 6 | 06 템플릿·반복자·STL | template-array 데모 | template-array, mini-vector는 선택 심화 | `.workspace/02-cpp98-systems/generic-programming/<exercise>/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=generic-programming/<exercise>` | 각 `reference/`와 비교 → 7 |
| 7 | 07 STL 문제 해결 | 문제별 선택적 블랙박스 실행 | date-lookup → rpn → sorter | `.workspace/02-cpp98-systems/generic-programming/stl-problems/<problem>/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=generic-programming/stl-problems/<problem>` | 각 `reference/`와 비교 → 8 |
| 8 | 08 POSIX 소켓·이벤트 루프 | 선택적 line server 블랙박스 실행 | line-server | `.workspace/02-cpp98-systems/networking/line-server/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=networking/line-server` | `reference/`와 비교 → 9 |
| 9 | 09 객체지향 HTTP 서버 | parser·router 데모와 나머지 선택적 블랙박스 실행 | HTTP 01 → 02 → 03 → 04 → 05 | `.workspace/02-cpp98-systems/networking/http-server/<stage>/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=networking/http-server/<stage>` | 각 `reference/`와 비교, 05 완료 후 C++98 트랙 종료 |

## Modern C++ 트랙과의 관계

Modern C++을 먼저 학습했다면 [Modern C++ → C++98 대응표](../90-appendix/01-modern-to-cpp98-crosswalk.md)를 참고합니다.

| Modern C++ 기본 도구 | C++98 트랙의 대응 방식 |
|---|---|
| `unique_ptr` | 복사 금지 + 명시적 소멸자 + 소유자 문서화 |
| 이동 의미론 | 복사를 금지하거나 깊은 복사 구현 |
| `override` | 정확한 함수 시그니처와 테스트로 재정의 검증 |
| `enum class` | 이름 충돌과 암묵 변환을 별도 규칙으로 통제 |
| 람다 | 함수 객체·함수 포인터·멤버 함수 포인터 |
| range-for | 명시적 반복자 순회 |
| `optional`, `variant` | 상태값 + 출력 매개변수 또는 별도 결과 타입 |
| `jthread`, `stop_token` | POSIX 또는 프로젝트별 종료 플래그와 명시적 조인 |

Modern C++ 기능을 사용할 수 없더라도 수명과 실패 규칙을 생략해서는 안 됩니다.

## 검증

최종 저장소 전체는 루트에서 다음 명령으로 검사합니다.

```sh
./verify.sh
```

C++98 트랙 검증에는 다음 항목이 포함됩니다.

- 모든 스켈레톤의 공개 빌드 그래프
- 객체 모델과 STL 참조 구현의 계약
- 할당·복사·반영 실패 주입
- 컴파일 실패와 비가상 소멸자 경로 검사
- 분할된 프레임, 부분 입출력, 상대방 연결 종료
- 느린 수신자에 대한 백프레셔
- 반복 연결 후 파일 디스크립터 정리
- line server 동시 연결 부하
- HTTP 파서·라우터·CGI·통합 서버의 정상 경로와 실패 경로
- 지원 환경에서 ASan·UBSan 검사

수정 중인 영역만 빠르게 확인할 때는 다음 타깃을 사용할 수 있습니다.

```sh
make skeleton-build
make test
make failure-check
make sanitize
make cpp98-verify
```

개별 타깃은 개발 중 빠른 피드백을 위한 것이며 최종 완료 여부는 `./verify.sh` 결과로 판단합니다.

## 완료 기준

- 객체의 복사·대입·소멸 규칙을 설명합니다.
- 공개 API에서 소유자와 비소유자를 구분합니다.
- 접근 방식, 복잡도, 반복자 무효화 규칙에 따라 컨테이너 선택을 설명합니다.
- 소켓과 이벤트 등록의 소유자를 명시합니다.
- 부분 읽기·쓰기, 상대방 연결 종료, 시간 초과, 프로토콜 오류를 서로 다른 상태로 처리합니다.
- 서버 종료 후 열린 파일 디스크립터와 남은 자식 프로세스가 없습니다.
- 실패 주입이 참조 구현의 보장 수준을 어떻게 구분하는지 설명합니다.
