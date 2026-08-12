# CGI 자식 프로세스

부모는 자식의 표준 입력 쓰기 끝과 표준 출력 읽기 끝을 소유합니다. 두 파이프를 논블로킹으로 처리하고 `waitpid(WNOHANG)`과 제한 시간을 함께 관리합니다. FastCGI와 PHP-FPM 운영은 다루지 않습니다.

## 실행

```sh
make observe
make exercise-test
make test
make failure-test
```

## 프로세스 실패 확인하기

- 실행 파일이 존재하지 않습니다.
- 자식 프로세스가 제한 시간보다 오래 멈춥니다.
- 자식 프로세스의 출력이 상한을 넘습니다.
- 부모 프로세스가 사용하지 않는 파이프 끝을 닫지 않습니다.

## 확인할 동작

성공, `exec` 실패, 제한 시간 초과와 출력 초과의 모든 경로에서 파이프와 자식 프로세스가 정리되고, 부분 쓰기·읽기가 완료될 때까지 폴링 상태를 정확히 갱신합니다.

## 권장 구현 순서

<!-- implementation-scope: cpp98-http-04 -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/main.cpp` | 각 pipe endpoint의 단일 owner를 만듭니다. |
| `2` | `reference/main.cpp` | child의 terminate·reap 수명을 guard로 관리합니다. |
| `3` | `reference/main.cpp` | deadline·nonblocking·stdio 복제 helper를 분리합니다. |
| `4` | `reference/main.cpp` | pipe와 child를 만들고 stdio 연결 뒤 executable로 교체합니다. |
| `5` | `reference/main.cpp` | parent가 소유할 pipe 끝만 남기고 nonblocking으로 전환합니다. |
| `6` | `reference/main.cpp` | deadline 아래 partial stdin write와 stdout read를 함께 poll합니다. |
| `7` | `reference/main.cpp` | child를 수거한 뒤 output과 종료 상태를 CLI 결과로 변환합니다. |
<!-- /implementation-scope -->
