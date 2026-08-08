# 단계 4: 예외 경계, journal과 종료

작업 함수가 던진 예외는 worker thread 밖으로 빠져나가지 않아야 합니다. 상태 전이는 append-only journal에 기록을 시도하되, 생성 뒤 journal append 장애가 worker를 종료시키지 않도록 health 상태를 별도로 노출합니다. 종료는 새 제출 거부, 대기 작업 취소, 실행 작업 취소 요청, worker join 순서로 진행합니다.

완료 조건은 다음과 같습니다.

- 표준 예외 메시지는 실패 snapshot에 남습니다.
- 알 수 없는 예외도 worker를 종료시키지 않습니다.
- journal 필드의 tab과 줄바꿈을 정규화합니다.
- 생성 시 journal을 열 수 없으면 constructor가 실패합니다.
- 생성 뒤 append 실패는 `journal_healthy() == false`로 관찰되며 작업 실행은 계속됩니다.
- `stop`은 여러 번 또는 여러 외부 thread에서 호출해도 하나의 join으로 수렴합니다.
- Work callback 안의 `stop`은 self-join하지 않고, 이후 외부 stop 또는 destructor가 join합니다.
- 존재하지 않는 ID의 `wait_for_terminal`은 timeout을 소비하지 않고 즉시 false를 반환합니다.
- terminal record는 기본 과제에서 계속 보존되며 자동 정리 정책이 없음을 문서화합니다.
- runtime journal health는 한 번 false가 되면 해당 runner 수명 동안 false로 유지합니다.
