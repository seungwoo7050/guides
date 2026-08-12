# 통합 HTTP 서버

앞 단계에서 나누어 다룬 요청 파서, 설정 라우터, 논블로킹 소켓 루프와 CGI 실행기를 하나의 C++98 서버로 연결합니다. 서버는 루프백 주소에서만 수신하며 시작할 때 실제 포트를 표준 출력으로 알립니다.

## 실행

```sh
make
./reference/integrated_http_server \
  8080 \
  ./config/routes.conf \
  ./helpers/echo_cgi.py \
  300
```

명령 인자는 포트, 라우트 설정, CGI 실행 파일, CGI 제한 시간 순서입니다. 포트에 `0`을 지정하면 운영체제가 빈 포트를 고릅니다.

라우트 설정은 다음 세 처리기를 지원합니다.

```text
route GET /health health;
route POST /echo echo;
route POST /cgi cgi;
```

`health`는 준비 상태를 반환하고 `echo`는 요청 본문을 그대로 돌려줍니다. `cgi`는 본문을 자식 프로세스의 표준 입력으로 전달한 뒤 CGI 머리글과 본문을 읽습니다.

## 동작 제한

- 요청 머리글은 8192바이트, 헤더는 100개, 본문은 1MiB까지 받습니다.
- CGI 출력도 1MiB로 제한합니다.
- CGI가 제한 시간을 넘기면 프로세스 그룹을 종료하고 `504`를 반환합니다.
- 실행 실패, 비정상 종료, 잘못된 CGI 응답과 출력 초과는 `502`로 구분합니다.
- 소켓 입출력은 `poll` 기반이지만 CGI 한 건을 처리하는 동안 같은 이벤트 루프의 다른 요청은 기다립니다.

마지막 항목은 구현을 단순하게 유지하기 위한 현재 제약입니다. 여러 CGI를 동시에 처리하려면 자식 파이프도 서버의 주 `poll` 집합에 등록하고 요청별 상태를 따로 관리해야 합니다.

## 검사

```sh
make workspace TRACK=cpp98
make cpp98-exercise-test CPP98_EXERCISE=networking/http-server/05-integrated-server
```

완성 검사는 `.workspace/02-cpp98-systems/networking/http-server/05-integrated-server/skeleton/`을 build하고 분할 요청, 파이프라이닝, 라우트 선택, CGI 본문 전달, 연결 종료를 실제 TCP 소켓으로 확인합니다. 느린 CGI, 출력 초과, 실행 파일 누락, 잘못된 설정과 요청 뒤에도 서버가 다음 요청을 받을 수 있는지 함께 검사합니다.

canonical 저장소의 `make start-state`는 배포 skeleton이 의도한 exit `78`로 종료하는지 확인하는 negative-fixture 검사입니다. learner 완성 판정과 다르며, `make check`는 canonical start-state·reference·failure 계약을 함께 검사합니다.

## 권장 구현 순서

<!-- implementation-scope: cpp98-http-05 -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/HttpParser.hpp` | 증분 HTTP parser의 독립 module 계약을 유지합니다. |
| `1-1` | `reference/HttpParser.cpp` | protocol 검증 뒤 request를 commit하고 pipeline bytes를 보존합니다. |
| `2` | `reference/Router.hpp` | 설정을 route key와 handler name lookup 계약으로 정의합니다. |
| `2-1` | `reference/Router.cpp` | 설정 전체를 검증한 뒤 handler name을 resolve합니다. |
| `3` | `reference/CgiRunner.hpp` | process exit·timeout·output limit을 구조화된 결과로 정의합니다. |
| `3-1` | `reference/CgiRunner.cpp` | pipe fd와 child terminate·wait 수명을 관리합니다. |
| `3-2` | `reference/CgiRunner.cpp` | pipe·process group을 만들고 child를 executable로 교체합니다. |
| `3-3` | `reference/CgiRunner.cpp` | parent poll·deadline·output cap을 CgiResult로 commit합니다. |
| `4` | `reference/main.cpp` | CLI·설정·listener startup 의존성을 검증합니다. |
| `5` | `reference/main.cpp` | route·CGI outcome을 HTTP status와 wire 응답으로 변환합니다. |
| `6` | `reference/main.cpp` | socket·parser·router/CGI와 response lifecycle의 owner를 만듭니다. |
| `6-1` | `reference/main.cpp` | handler name을 health·echo·CGI 실행에 연결합니다. |
| `6-2` | `reference/main.cpp` | parser completion을 dispatch·pipeline·keep-alive에 연결합니다. |
| `6-3` | `reference/main.cpp` | partial send와 output 상한·close-after-write를 관리합니다. |
| `7` | `reference/main.cpp` | shared 의존성을 가진 Connection 소유권 이전을 처리합니다. |
| `8` | `reference/main.cpp` | startup, poll loop와 typed exit·shutdown 경계를 조립합니다. |
<!-- /implementation-scope -->
