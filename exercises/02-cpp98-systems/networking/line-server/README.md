# 논블로킹 줄 단위 서버

`skeleton`는 블로킹 단일 연결 서버입니다. `reference`은 Linux에서 `epoll`, macOS에서 `kqueue`를 선택하고 연결별 입력·출력 버퍼, 부분 입출력과 역압 상한을 관리합니다.

프로토콜은 일반 줄에 `ECHO <line>`, `COUNT`에 이전 일반 줄 수, `QUIT`에 `BYE` 후 EOF를 반환합니다.

## 실행

먼저 저장소 루트에서 C++98 learner workspace를 생성하고 `.workspace/02-cpp98-systems/networking/line-server/skeleton/main.cpp`만 수정합니다.

```sh
make workspace TRACK=cpp98
make cpp98-exercise-test CPP98_EXERCISE=networking/line-server
```

아래 명령은 canonical reference를 실행하는 선택적 black-box oracle입니다. 출력을 먼저 예측하고 source는 열지 않은 채 관찰하며, 자신의 구현이 검증을 통과한 뒤에만 reference source와 비교합니다.

```sh
make observe
make test
make stress
make backpressure
make leak-check
```

## 경계 입력 확인하기

- 한 줄을 여러 `send`로 나누어 보냅니다.
- 여러 줄을 한 번에 보냅니다.
- 응답을 읽지 않는 느린 클라이언트로 송신 상한을 채웁니다.
- 연결을 반복해서 열고 닫아 파일 디스크립터 수가 증가하는지 확인합니다.

## 확인할 동작

한 연결의 부분 입력·오류·종료가 다른 연결을 막지 않고, 보낼 데이터가 있을 때만 쓰기 준비 상태를 등록하며, 모든 종료 경로에서 파일 디스크립터가 한 번만 닫힙니다.

## 권장 구현 순서

<!-- implementation-scope: cpp98-line-server -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/Poller.hpp` | platform event를 이식 가능한 read·write·hangup·error 값으로 정의합니다. |
| `2` | `reference/Poller.hpp` | event loop와 구체 adapter 사이의 factory 경계를 만듭니다. |
| `2-1` | `reference/Poller_epoll.cpp` | Linux epoll interest와 native event를 공용 계약으로 변환합니다. |
| `2-2` | `reference/Poller_kqueue.cpp` | BSD kqueue filter와 event를 공용 계약으로 변환합니다. |
| `2-3` | `Makefile` | 현재 OS에 맞는 Poller adapter 하나만 server와 link합니다. |
| `3` | `reference/main.cpp` | listener와 accepted socket의 flags 및 실패 cleanup을 구현합니다. |
| `4` | `reference/main.cpp` | client fd와 입출력 buffer·close 상태의 owner를 만듭니다. |
| `5` | `reference/main.cpp` | partial input을 line frame과 protocol 상태 전이로 처리합니다. |
| `6` | `reference/main.cpp` | partial output과 backpressure·close-after-write를 관리합니다. |
| `7` | `reference/main.cpp` | accepted fd의 등록과 Connection 소유권 이전을 transaction으로 처리합니다. |
| `8` | `reference/main.cpp` | dynamic interest update, 연결 정리와 signal shutdown을 조립합니다. |
<!-- /implementation-scope -->
