# 명령과 장애 진단

저장소 전체의 공개 명령은 네 개다.

```sh
make prepare
make check
VERIFY_LOG="/tmp/backend-spring-boot-verify.log" make verify
make clean
```

개별 학습 실습을 반복할 때만 아래 명령을 사용한다.

| 목적 | 명령 |
|---|---|
| reference 전체 test | `./scripts/mvn-guide.sh verify` |
| 단일 reference | `./scripts/mvn-guide.sh -pl :모듈명 -am test` |
| 학습 workspace 생성 | `./scripts/new-workspace.sh 실습명` |
| 학습 workspace test | `./scripts/check-workspace.sh 실습명` |
| dependency tree | `./scripts/mvn-guide.sh dependency:tree` |
| 문서·구조 검사 | `python3 scripts/validate.py` |
| 결과물 정리 | `make clean` |
| Docker 접근 확인 | `docker info` |
| guide가 만든 시험 컨테이너 확인 | `docker ps --filter label=org.testcontainers=true` |

`docker system prune -a --volumes`는 이 저장소의 정리 명령이 아니다. 다른 프로젝트의 image와 data까지 제거할 수 있다. `make verify`는 외부 임시 사본을 지우고 실행 전 baseline 이후 생긴 Testcontainers 자원만 회수하며 기존 sentinel은 보존한다.

검증 로그에는 단계별 PASS/FAIL, `SUMMARY: passed=... failed=... skipped=0`과 최종 `RESULT: PASS|FAIL`이 남는다. dependency나 image가 준비되지 않았을 때 verify가 네트워크로 보충하지 않으므로 `make prepare`를 다시 실행해 원인을 드러낸다. tracked canonical skeleton은 root 검증의 고정 실패 fixture이므로 직접 고치지 않고 `.workspace/<실습명>`만 수정한다.

## 증상에서 첫 원인을 좁힌다

| 증상 | 먼저 확인할 증거 | 가능한 1차 원인 |
|---|---|---|
| Java class를 찾지 못한다. | `java -version`, `./mvnw --version` | JDK 기준 불일치 또는 `prepare.sh` 미완료 |
| offline Maven 검증이 dependency를 찾지 못한다. | `./prepare.sh`의 `go-offline` 실패 module | root 또는 skeleton 전용 dependency가 준비되지 않음 |
| Testcontainers가 시작되지 않는다. | `docker info`, Docker socket 권한, Ryuk log | daemon 중지·권한·host 연결 문제 |
| Testcontainers 실행별 자원 검사에서 중단된다. | `GUIDE_VERIFY_RUN_ID`와 `docker ps --filter label=dev.guides.verify-run=...` | 이전 비정상 종료의 해당 실행 자원 또는 별도 Testcontainers 작업 |
| Flyway에서 Context 시작이 실패한다. | 빈 DB의 migration history와 checksum | 배포된 migration 수정 또는 순서 충돌 |
| JPA 동시성 test가 간헐적으로 실패한다. | 모든 `Future`, transaction proxy와 실제 SQL | self invocation, lock 누락 또는 transaction 범위 오류 |
| Redis를 비우면 동일 요청이 외부 정책을 다시 호출한다. | DB 정본 조회 순서와 Redis miss branch | cache를 처리 결과의 정본으로 사용함 |
| Redis 장애에서 중복 행이 생긴다. | DB unique constraint·advisory lock | 정확성을 cache에 맡김 |
| Kafka 발행은 성공하지만 소비되지 않는다. | topic·key·listener·ack와 offset | 계약 불일치 또는 consumer 연결 오류 |
| 업무 거절 뒤 Circuit Breaker가 열린다. | recorded·ignored exception과 metric | 4xx 업무 결과를 의존성 장애로 분류함 |
| health는 정상인데 요청이 실패한다. | liveness·readiness와 실제 요청 경로 | process 생존만 검사하고 준비 조건을 누락함 |
| skeleton이 compile 오류로 실패한다. | Surefire test summary 이전의 compiler log | 학습 결함이 아니라 source·dependency 정합성 문제 |

## 진단 순서

증상만 보고 설정을 바꾸지 않는다.

```text
재현 가능한 한 요청 고정
→ HTTP status·errorCode 확인
→ application log와 trace 식별자 확인
→ DB·Redis·Outbox 최종 상태 확인
→ dependency 호출 횟수와 응답 확인
→ metric 변화 확인
→ 가장 먼저 깨진 경계 수정
```

후속 오류를 먼저 고치면 원래 실패를 가릴 수 있다. 예를 들어 PostgreSQL 시작 실패 뒤 Redis connection 오류가 함께 보이더라도, 요청 정본이 만들어지지 않은 첫 실패부터 확인한다.
