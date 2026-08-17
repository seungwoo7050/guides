# Command Service

## 개요

`command_service`는 표준 입력으로 줄 단위 명령을 받아 bounded in-memory key/value store를 조작하는 C++98 CLI입니다. 값은 `TextBuffer`가 직접 소유하고, parser·handler·router·store·formatter가 각자의 경계를 유지합니다.

단계별로 분리되어 있던 책임을 하나의 완성된 프로그램에 통합했습니다.

## 기능

지원 명령은 다음과 같습니다.

```text
PUT <key> <value>
GET <key>
DELETE <key>
COUNT
LIST
QUIT
```

- `PUT`은 새 key만 추가하며 기존 key에는 `CONFLICT`를 반환합니다.
- 새 key가 capacity를 넘으면 `FULL`을 반환합니다.
- `GET`과 `DELETE`는 없는 key에 `NOT_FOUND`를 반환합니다.
- `LIST`는 `std::map` 순서로 `key=value` 행을 출력합니다.
- 문법 오류는 `BAD_REQUEST`, 예기치 못한 내부 오류는 `INTERNAL_ERROR`로 정규화합니다.

## 구조

- `TextBuffer`: heap 문자열의 Rule of Three와 강한 대입 보장
- `Store`: capacity, key/value ownership, transactional insertion
- `RequestParser`: command와 arity 검증
- `Handler`: command별 domain operation
- `Router`: handler 등록과 수명 소유
- `ResponseFormatter`: 구조화 응답의 protocol 직렬화
- `main`: process I/O와 오류 번역 경계

## 빌드

```sh
make
```

## 실행

```sh
./command_service [capacity]
```

`capacity`를 생략하면 `1024`를 사용합니다.

```sh
printf 'PUT name seungwoo\nGET name\nCOUNT\nQUIT\n' | ./command_service 16
```

예상 출력:

```text
OK
VALUE seungwoo
COUNT 1
BYE
```

## 테스트

```sh
make test
```

테스트는 deep copy와 copy failure rollback, duplicate conflict, capacity rejection, failed insertion 뒤 state preservation, parser arity, handler routing, LIST ordering, CLI protocol을 확인합니다.

## 주요 설계 결정

`Store::putNew`는 duplicate와 capacity를 먼저 검사하고 owned value를 완성한 뒤 `std::map::insert`로 commit합니다. 값 복사나 node 할당이 실패해도 기존 store는 유지됩니다.

`Router`는 raw pointer 기반 C++98 구현이지만 handler의 sole owner입니다. 생성 중 등록이 실패하면 이미 등록된 handler를 모두 해제합니다.

내부 exception message는 외부 protocol에 노출하지 않습니다. caller는 안정된 response token만 관찰합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Domain failure taxonomy | `include/Errors.hpp` |
| 2 | Owned text value | `include/TextBuffer.hpp` |
| 2-1 | Allocation and object lifetime | `src/TextBuffer.cpp` |
| 2-2 | Strong copy assignment | `src/TextBuffer.cpp` |
| 3 | Bounded store ownership | `include/Store.hpp` |
| 3-1 | Transactional insertion | `src/Store.cpp` |
| 3-2 | Store observation and deletion | `src/Store.cpp` |
| 4 | Validated request parsing | `src/RequestParser.cpp` |
| 5 | Structured response model | `include/Response.hpp` |
| 6 | Polymorphic handler contract | `include/Handler.hpp` |
| 6-1 | Command execution handlers | `src/Handler.cpp` |
| 7 | Handler ownership and routing | `src/Router.cpp` |
| 8 | Process composition and error translation | `src/main.cpp` |

## 범위와 제한

값과 key는 공백을 포함하지 않는 token입니다. persistence, authentication, concurrent access, network transport는 범위에 포함하지 않습니다. `LIST`는 한 request에 여러 줄을 반환하며 별도 terminator를 추가하지 않습니다.
