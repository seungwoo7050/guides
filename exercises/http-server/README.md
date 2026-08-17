# HTTP Server

## 개요

incremental HTTP parser, validated route configuration, non-blocking socket loop와 bounded CGI process runner를 통합한 C++98 HTTP/1.x server입니다. loopback address에서만 수신하며 실제 port를 startup line으로 출력합니다.

기존의 parser, router, non-blocking server, CGI, integrated-server 단계는 서로 다른 프로그램이 아니라 이 server를 구성하는 누적 책임이므로 하나의 project로 통합했습니다.

## 기능

- HTTP/1.0 및 HTTP/1.1 request parsing
- 8192-byte header limit, 100-header limit, 1 MiB body limit
- fragmented request와 pipelined request 처리
- exact method/path route configuration
- `health`, `echo`, `cgi` handler
- keep-alive 및 `Connection: close`
- partial socket output와 bounded pending response
- CGI stdin/stdout pipes, process group, timeout, 1 MiB output limit
- CGI timeout `504`, 실행/응답/output failure `502`
- SIGINT/SIGTERM shutdown과 connection cleanup

## 설정

```text
route GET /health health;
route POST /echo echo;
route POST /cgi cgi;
```

지원 handler name은 `health`, `echo`, `cgi`입니다. 설정 전체가 유효한 경우에만 `Router`가 생성됩니다.

## 빌드, 실행 및 테스트

```sh
make
./http_server 8080 ./config/routes.conf ./helpers/echo_cgi.py 1000
make test
```

`port`에 `0`을 지정하면 OS가 빈 port를 선택하고 server는 `PORT <n>`을 stdout에 출력합니다.

검증을 분리해서 실행할 수도 있습니다.

```sh
make integration-test
make failure-test
```

## 구조

- `include/HttpParser.hpp`, `src/HttpParser.cpp`: incremental framing과 protocol validation
- `include/Router.hpp`, `src/Router.cpp`: transactional configuration parsing과 lookup
- `include/CgiRunner.hpp`, `src/CgiRunner.cpp`: child process 및 pipe lifecycle
- `src/main.cpp`: HTTP response mapping, connection ownership, poll loop
- `helpers/`: reproducible CGI fixtures
- `tests/`: component 및 TCP integration tests

## 주요 설계 결정

parser는 완성된 request만 commit하고 남은 pipeline bytes를 보존합니다. CGI child는 별도 process group에서 실행되어 timeout 또는 output overflow 시 descendant까지 종료할 수 있습니다. `Connection`은 socket, parser와 pending response state를 단독 소유합니다.

현재 CGI 실행은 pipe 자체를 server의 main poll set에 넣지 않고 `CgiRunner::run` 안에서 동기적으로 기다립니다. 따라서 하나의 CGI가 실행되는 동안 같은 event loop의 다른 request가 대기합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Incremental HTTP request contract | `include/HttpParser.hpp` |
| 1-1 | Validated framing and request commit | `src/HttpParser.cpp` |
| 2 | Route configuration contract | `include/Router.hpp` |
| 2-1 | Transactional route parsing | `src/Router.cpp` |
| 3 | Structured CGI outcome | `include/CgiRunner.hpp` |
| 3-1 | Descriptor and child lifecycle | `src/CgiRunner.cpp` |
| 3-2 | Pipe, process, and execution environment bootstrap | `src/CgiRunner.cpp` |
| 3-3 | Deadline and output-bound collection | `src/CgiRunner.cpp` |
| 4 | Validated server startup | `src/main.cpp` |
| 5 | HTTP response mapping | `src/main.cpp` |
| 6 | Connection ownership | `src/main.cpp` |
| 6-1 | Handler dispatch | `src/main.cpp` |
| 6-2 | Parser, pipeline, and keep-alive integration | `src/main.cpp` |
| 6-3 | Partial output lifecycle | `src/main.cpp` |
| 7 | Accepted connection transaction | `src/main.cpp` |
| 8 | Poll-loop composition and shutdown | `src/main.cpp` |

## 범위와 한계

`Transfer-Encoding`, chunked bodies, TLS, static files, virtual hosts, request timeout, concurrent CGI state machines와 production-grade access logging은 지원하지 않습니다. CGI environment는 parent environment를 그대로 전달하며 CGI metadata variable을 별도로 구성하지 않습니다.
