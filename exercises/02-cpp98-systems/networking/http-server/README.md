# HTTP 서버의 책임 나누기

전송, 프로토콜, 라우팅과 자식 프로세스를 작은 단계로 나누어 구현한 뒤 하나의 서버로 연결합니다.

1. `01-parser`: 바이트 조각에서 유효한 `Request`를 만듭니다.
2. `02-config-router`: 설정을 검증한 뒤 핸들러를 선택합니다.
3. `03-nonblocking-server`: 파서와 라우터를 논블로킹 소켓 어댑터에 연결합니다.
4. `04-cgi-process`: 자식 프로세스의 표준 입출력, 종료와 제한 시간을 검증합니다.
5. `05-integrated-server`: 앞의 네 요소를 실제 요청 처리 흐름으로 연결합니다.

## 실행

```sh
make observe
make exercise-test
make test
make failure-test
```

각 하위 디렉터리는 `skeleton`, `reference`, 자동 테스트와 실패 실험을 독립적으로 제공합니다. 앞 단계의 참조 구현이 다음 단계의 개념적 시작점이지만, 어느 단계부터 열어도 실행할 수 있습니다. 최종 단계는 실제 TCP 요청이 파서, 라우터와 CGI 실행기를 차례로 통과하는지 검사합니다.
