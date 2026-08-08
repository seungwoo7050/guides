# 연습문제: signal-loop

## 목표

시그널 handler에서 복잡한 작업을 하지 않고 self-pipe로 사건을 일반 제어 흐름에 전달합니다. 설치·정리 경쟁 구간과 정상 종료를 함께 다룹니다.

## 구현 위치

`skeleton/signal_loop.c`를 구현합니다.

## 외부 계약

프로그램은 관련 시그널을 차단한 상태에서 handler와 self-pipe를 준비한 뒤 다음 한 줄을 먼저 출력합니다.

```text
ready pid=<PID>
```

- `SIGUSR1`을 받으면 `event=SIGUSR1`을 출력하고 계속 실행합니다.
- `SIGTERM`을 받으면 `event=SIGTERM`을 출력하고 descriptor와 handler를 정리한 뒤 상태 0으로 종료합니다.
- handler에서는 pending 플래그 대입, `write`, `errno` 저장·복원만 사용합니다.
- self-pipe 쓰기 끝은 nonblocking이며 두 끝 모두 close-on-exec입니다.
- 파이프가 가득 차 wake byte를 쓰지 못해도 pending 플래그가 사건의 존재를 보존합니다.
- 설치와 정리 중 관련 시그널을 block합니다.
- 설치 전 handler를 보존하고 종료 때 정확히 복구합니다.
- 표준 시그널은 여러 번 생성되어도 하나로 합쳐질 수 있으므로 정확한 이벤트 카운터로 사용하지 않습니다.

## 완료 기준

- `make exercise-test`와 `make sanitize`가 통과하며 `ready`가 먼저 출력된 뒤 SIGUSR1 사건을 처리하고 SIGTERM 사건·상태 0으로 종료합니다.
- burst 시그널에서도 멈추지 않고, self-pipe가 가득 찬 경우 pending 플래그로 사건 존재를 보존하며 정확한 발생 횟수를 약속하지 않습니다.
- 파이프의 nonblocking·close-on-exec 설정과 설치 전 handler 복구를 확인하고, 준비·정리 구간에서 관련 시그널이 차단되어 추가 출력이나 FD 누수가 없습니다.

## 자기 설명

- handler가 로그 출력이나 동적 할당 대신 pending 플래그와 self-pipe 쓰기만 수행해야 하는 이유는 무엇인가요?
- handler 설치·복구와 FD 생성·폐기 사이에서 시그널 mask를 사용하지 않으면 어떤 경쟁 순서가 잘못된 FD 접근을 만들 수 있나요?

## 검증

```sh
make exercise-test
make sanitize
```

Python 검사는 실제 프로세스를 두 번 시작해 준비 완료 순서, 순차 시그널, burst에서의 합쳐짐, 종료 상태, 추가 출력과 timeout을 확인합니다.
