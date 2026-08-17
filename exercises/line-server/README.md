# Line Server

## 개요

여러 TCP client를 하나의 non-blocking event loop에서 처리하는 C++98 line protocol server입니다. Linux에서는 `epoll`, macOS와 BSD 계열에서는 `kqueue` adapter를 선택합니다.

## 프로토콜

- 일반 line: `ECHO <line>`을 반환하고 connection별 count를 증가시킵니다.
- `COUNT`: 이전 일반 line 수를 `COUNT <n>`으로 반환합니다.
- `QUIT`: `BYE`를 전송한 뒤 connection을 닫습니다.

입력 line은 최대 8192 bytes이며 connection별 pending output은 65536 bytes로 제한됩니다.

## 빌드, 실행 및 테스트

```sh
make
./line_server 8080
make test
```

`0`을 port로 지정하면 OS가 빈 port를 선택하며 server는 `PORT <n>`을 stdout에 출력합니다.

추가 검증은 다음 target으로 분리되어 있습니다.

```sh
make stress
make backpressure
make leak-check
```

## 구조

- `include/Poller.hpp`: portable event contract와 factory
- `src/Poller_epoll.cpp`: Linux adapter
- `src/Poller_kqueue.cpp`: macOS/BSD adapter
- `src/main.cpp`: socket lifecycle, connection state와 event loop
- `tests/test_server.py`: framing, 동시성, backpressure, FD cleanup 검증

## 주요 설계 결정

`Connection`이 client fd와 모든 I/O state를 단독 소유합니다. writable interest는 pending output이 있을 때만 등록합니다. 새 connection은 socket flags, poller registration, client map insertion이 모두 성공한 뒤 ownership을 이전합니다. 출력 상한을 넘긴 느린 client만 종료되며 다른 connection은 계속 처리됩니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Portable event model | `include/Poller.hpp` |
| 2 | Poller factory boundary | `include/Poller.hpp` |
| 2-1 | Linux epoll adapter | `src/Poller_epoll.cpp` |
| 2-2 | BSD kqueue adapter | `src/Poller_kqueue.cpp` |
| 3 | Socket configuration and listener | `src/main.cpp` |
| 4 | Connection ownership | `src/main.cpp` |
| 5 | Incremental line framing | `src/main.cpp` |
| 6 | Partial output and backpressure | `src/main.cpp` |
| 7 | Accepted connection transaction | `src/main.cpp` |
| 8 | Event-loop composition and shutdown | `src/main.cpp` |

## 범위와 한계

단일 process와 단일 event-loop thread만 사용합니다. TLS, authentication, persistence, idle timeout, IPv6, cross-process load balancing과 application-level flow-control negotiation은 포함하지 않습니다. kqueue adapter는 해당 platform에서 별도 build verification이 필요합니다.
