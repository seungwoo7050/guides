# 논블로킹 HTTP 서버

이벤트 루프를 이식 가능한 `poll` 어댑터로 구성하고 파서와 작은 핸들러 집합을 연결합니다. HTTP/1.1, `Content-Length`, 연결 유지와 제한된 `GET`·`POST`·`DELETE` 라우트를 지원합니다.

## 실행

```sh
make observe
make exercise-test
make test
make failure-test
```

## 연결 경계 확인하기

분할 요청, 같은 연결에서 이어지는 요청, 잘못된 요청, 존재하지 않는 라우트와 상대 연결 종료를 주입합니다. `SIGTERM` 뒤 이벤트 대기가 끝나고 자식 프로세스가 남지 않아야 합니다.

## 확인할 동작

연결 버퍼와 요청 객체의 수명이 분리되고, 파서 오류는 400, 라우트 없음은 404, 정상 처리 결과는 독립된 응답으로 직렬화됩니다.

## 권장 구현 순서

<!-- implementation-scope: cpp98-http-03 -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/HttpParser.hpp` | 선행 parser의 증분 상태 계약을 server module 경계로 가져옵니다. |
| `1-1` | `reference/HttpParser.cpp` | protocol 검증 뒤에만 request를 commit하고 pipeline bytes를 보존합니다. |
| `2` | `reference/main.cpp` | signal·listener와 accepted fd의 초기화·cleanup을 구현합니다. |
| `3` | `reference/main.cpp` | route 결과와 connection policy를 HTTP wire 응답으로 직렬화합니다. |
| `4` | `reference/main.cpp` | socket·parser·pending output과 close lifecycle의 owner를 만듭니다. |
| `4-1` | `reference/main.cpp` | recv bytes를 request dispatch와 keep-alive 흐름으로 연결합니다. |
| `4-2` | `reference/main.cpp` | partial send와 output 상한·close-after-write를 관리합니다. |
| `5` | `reference/main.cpp` | accepted fd와 Connection 소유권 이전을 transaction으로 처리합니다. |
| `6` | `reference/main.cpp` | poll interest, event 처리와 signal shutdown을 조립합니다. |
<!-- /implementation-scope -->
