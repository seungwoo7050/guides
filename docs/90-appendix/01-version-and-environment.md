# 버전과 개발 환경

이 저장소는 특정 버전 조합에서 문서, reference와 실패 실습을 함께 재현한다. 버전 표는 최신 도구 목록이 아니라 **검증 기준선**이다.

| 구성 요소 | 기준 |
|---|---|
| Java source·bytecode | 21 |
| 실행 JDK | 21 이상 |
| Python | 3.10 이상 |
| Maven Wrapper | 3.3.4 |
| Apache Maven | 3.9.16 |
| Maven Surefire | 3.5.6 (Spring Boot 4.1.0 관리) |
| Spring Boot | 4.1.0 |
| PostgreSQL image | `postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15` |
| Redis image | `redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005` |
| Spring Kafka | Spring Boot 4.1.0 관리 버전 |
| Apache Kafka client·공식 container broker | 4.3.1 |
| Testcontainers | 2.0.5 |
| Testcontainers Ryuk | `testcontainers/ryuk:0.14.0@sha256:7c1a8a9a47c780ed0f983770a662f80deb115d95cce3e2daa3d12115b8cd28f0` |
| Avro | 1.12.1 |
| Resilience4j Boot 4 | 2.4.0 |
| WireMock | 3.12.1 |

`maven.compiler.release=21`이 Java API와 bytecode 기준을 고정한다. Spring Boot 4.1과 Jackson 3 예제는 JDK 21에서 검증한다.

## 필요한 명령

```text
git
bash
java
curl
python3
docker
```

Linux와 macOS를 지원한다. `make`는 개별 편의 target을 사용할 때만 선택적으로 필요하다. Docker daemon은 현재 사용자에게 접근 가능해야 한다. PostgreSQL·Redis를 사용하는 필수 integration test는 Docker를 사용할 수 없을 때 건너뛰지 않고 실패한다.

Docker Compose는 이 저장소의 필수 도구가 아니다. 서비스 배치와 공개 운영은 `guide-web-infrastructure`가 소유하고, 이 저장소는 Testcontainers가 시험 수명 안에서 만든 컨테이너만 사용한다.

`verify.sh`는 각 container에 `dev.guides.verify-run` label을 붙이고 실행 전후 Testcontainers 자원을 비교한다. 기존 Docker 자원은 삭제하지 않으며 해당 실행의 label을 가진 자원만 비정상 종료 정리 대상으로 삼는다.

## 준비와 격리 검증

저장소 루트에서 다음 순서로 실행한다.

```sh
./prepare.sh
VERIFY_LOG="/tmp/backend-spring-boot-verify.log" ./verify.sh
```

`prepare.sh`는 source bytes·mode·symlink와 Git index를 보존하며 다음만 수행한다.

- Maven Wrapper와 JDK 확인
- `.guide/backend-spring-boot` 아래에 Maven dependency·plugin 준비
- digest가 고정된 PostgreSQL·Redis·Ryuk image 준비
- 입력 fingerprint와 실제 image ID를 `prepared.json`에 원자적으로 기록

시스템 package manager, `sudo`, Git commit·branch·index 변경을 수행하지 않는다. 생성한 `target`은 종료 전에 제거하고 namespaced cache는 `make clean`에서도 보존한다.

`verify.sh`는 저장소 밖 격리 사본에서만 source를 빌드하고 완전 offline Maven과 Docker no-pull 정책을 강제한다. 외부 절대 `VERIFY_LOG`가 없거나 marker가 stale하면 preflight에서 실패한다.

## 설정값 검토

설정 이름을 추가하거나 바꿀 때 다음을 함께 확인한다.

- 주소·사용자 이름·credential에 일관된 prefix를 사용하는가?
- timeout과 TTL이 `Duration`으로 binding되고 단위가 드러나는가?
- local 기본값이 production에도 조용히 적용되지 않는가?
- 예제 파일과 test fixture에 실제 비밀값이 들어 있지 않은가?
- application, container, test와 배포 명세가 같은 이름을 사용하는가?
- host에서 접근할 주소와 container 내부 이름을 구분했는가?
- Kafka listener 주소가 client 실행 위치와 맞는가?
- 잘못된 값이 첫 요청이 아니라 Context 시작 단계에서 거부되는가?

## 버전 변경 절차

버전 변경은 다음을 하나의 검증 단위로 다룬다.

1. root POM과 모든 module dependency
2. Maven Wrapper 배포 URL과 checksum
3. 모든 reference의 compile·test
4. 모든 skeleton의 의도한 test failure
5. PostgreSQL·Redis·Ryuk image와 host architecture
6. Flyway migration과 Hibernate mapping validation
7. Spring Security·Kafka·Actuator의 폐기 예정 API
8. 깨끗한 기준 checkout에서 `./prepare.sh && ./verify.sh`

표와 POM만 바꾸고 위 실행 근거를 만들지 않은 변경은 완료가 아니다.
