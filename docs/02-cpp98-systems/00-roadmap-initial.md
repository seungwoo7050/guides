# C++98 시스템 프로그래밍 트랙

## 목적

C++98 제약 아래 객체 수명과 STL을 이해한 뒤 POSIX non-blocking server까지 확장합니다. 사용할 수 없는 Modern C++ 기능을 흉내 내기보다, 제한된 언어 기능 안에서 ownership과 failure boundary를 명시적으로 설계하는 것이 목적입니다.

## Part 1. Object model and responsibility

1. `01-program-and-type-model.md`
2. `02-lifetime-value-and-ownership.md`
3. `03-assigning-object-responsibilities.md`
4. `04-inheritance-and-polymorphism.md`
5. `05-errors-validation-and-casts.md`

이 구간은 하나의 command service를 중심으로 value ownership, store responsibility, parser, polymorphic dispatch와 error translation을 연결할 예정입니다.

## Part 2. Generic programming and STL

6. `06-templates-iterators-and-stl.md`
7. `07-solving-problems-with-stl.md`

`template-array`, `mini-vector`, `date-lookup`, `rpn-calculator`, `stable-sorter` 같은 독립 project로 container contract와 STL 선택을 검증할 예정입니다.

## Part 3. Networking and HTTP

8. `08-posix-sockets-and-event-loop.md`
9. `09-object-oriented-http-server.md`

`line-server`에서 non-blocking socket, partial I/O와 event readiness를 다룬 뒤, `http-server`에서 incremental parser, routing, CGI process와 connection lifecycle을 통합할 예정입니다.

## 완료 기준

- Rule of Three와 explicit ownership을 설명할 수 있습니다.
- STL container와 algorithm 선택을 access pattern과 complexity로 설명할 수 있습니다.
- socket, event registration과 child process의 owner를 구분할 수 있습니다.
- partial I/O, timeout, peer close와 protocol error를 독립 상태로 처리할 수 있습니다.
