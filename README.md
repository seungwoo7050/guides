# Java 애플리케이션 개발 가이드

이 저장소는 JDK 21에서 Java 17 API·바이트코드 호환성을 지키며 작은 애플리케이션을 독립적으로 설계하고, 빌드하고, 검증하기 위한 과정입니다. 첫 소스의 컴파일과 실행에서 시작해 값과 참조, 객체의 불변식, 컬렉션과 숫자 계약, 오류와 시간, 동시성, Maven, JUnit, 품질 근거를 하나의 누적 경로로 연결합니다.

Java를 배우기 위해 C를 먼저 완료할 필요는 없습니다. 조건, 반복, 함수와 배열 같은 일반 프로그래밍 개념이 처음이라면 1부를 순서대로 진행하고, 다른 언어로 프로그램을 작성해 본 경험이 있다면 익숙한 절은 빠르게 확인해도 됩니다.

## 완료 뒤 할 수 있는 일

과정을 마치면 다음 작업을 스스로 수행할 수 있어야 합니다.

- 빈 디렉터리에서 패키지가 있는 Java 프로그램을 컴파일하고 실행합니다.
- 값 객체와 엔터티, 불변 객체와 가변 상태의 책임을 구분합니다.
- 컬렉션의 순서·중복·소유권과 숫자 오버플로·반올림 계약을 코드에 남깁니다.
- 입력 오류, 현재 상태의 거절과 실행 환경의 실패를 구분합니다.
- `Clock`, 명시적인 식별자와 닫을 수 있는 자원으로 재현 가능한 코드를 만듭니다.
- 경쟁 상태를 결정적으로 재현하고 잠금과 제한된 실행기의 수명 주기를 검증합니다.
- Maven Wrapper, JUnit, AssertJ, Spotless, Checkstyle과 JFR을 이용해 검증 근거를 남깁니다.
- 위 내용을 통합한 동시 작업 원장 애플리케이션을 구현합니다.

## 지원 환경

- Linux 또는 macOS
- JDK 21(컴파일 대상은 `--release 17`)
- POSIX 셸과 Bash
- `curl`, `python3`, `make`
- 저장소에 포함된 Maven Wrapper 3.3.4와 Apache Maven 3.9.16

시스템 패키지는 스크립트가 설치하지 않습니다. 필요한 명령이 없거나 JDK가 다르면 원인을 출력하고 중단합니다.

## 최초 준비와 전체 검증

저장소 루트의 공개 명령은 다음 네 가지입니다.

```sh
make prepare
make check
VERIFY_LOG=/tmp/guide-java-verify.log make verify
make clean
```

`make prepare`는 소스·파일 모드·심볼릭 링크·Git index를 바꾸지 않고 Maven Wrapper와 프로젝트 의존성을 `.guide/java/`에 준비합니다. 준비 fingerprint는 canonical curriculum source를 대상으로 하므로 학습자 `.workspace/`를 바꾸어도 cache가 불필요하게 무효화되지 않습니다. fingerprint와 도구 버전은 `.guide/java/prepared.json`에 원자적으로 기록되며 같은 상태에서 다시 실행해도 결과가 달라지지 않습니다. `make check`는 빠른 문서·구조·계약 검사를, `make clean`은 명시된 빌드 생성물만 정리하며 준비 캐시와 학습자 작업공간은 보존합니다.

`make verify`는 현재 working tree를 저장소 밖 임시 디렉터리로 복사하고 준비된 의존성을 오프라인으로 사용합니다. 학습자 `.workspace/`도 복사와 source bytes·mode·symlink 불변성 검사에는 포함하지만 정확한 curriculum tree 검사에서는 제외합니다. 문서 링크, 셸 문법, `javac --release 17`, Maven reference 모듈, 실패해야 하는 원본 skeleton, 격리된 로컬 저장소 실습과 JFR 기록을 검사하며 전체 로그는 저장소 밖의 절대 `VERIFY_LOG`에 남깁니다.

## 정본 학습 순서

먼저 [학습 로드맵](docs/00-roadmap.md)에서 전체 범위와 선택 경로를 확인합니다. 이후 아래 표를 한 행씩 진행합니다. 관찰 예제가 있으면 개념을 좁게 확인하고, 구현 실습은 `skeleton`을 안전한 `.workspace/`로 복사해 그 복사본만 수정합니다. 정본 검사에 통과하고 자신의 설계를 설명한 뒤에만 `reference/` 소스를 비교합니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 0 | [학습 로드맵](docs/00-roadmap.md) | — | 필수·선택 경로와 지원 환경을 정합니다. | — | `make check` | [JDK·JVM과 첫 프로그램](docs/01-language-and-domain/01-jdk-jvm-and-first-program.md)으로 이동합니다. |
| 1 | [JDK·JVM과 첫 프로그램](docs/01-language-and-domain/01-jdk-jvm-and-first-program.md) | [JVM 실행 환경 확인](examples/runtime-model/README.md) | [첫 명령행 프로그램](exercises/01-language-and-domain/01-first-program/README.md)의 workspace를 만들고 초기 실패를 확인합니다. | `.workspace/first-program/src/main/java/.../NumberReportApplication.java` | `./scripts/check-workspace.sh exercises/01-language-and-domain/01-first-program` | 아직 `reference/`를 보지 않고 Java 언어 기초로 이동합니다. |
| 2 | [Java 언어 기초](docs/01-language-and-domain/02-java-language-foundations.md) | — | 첫 프로그램의 입력·계산·출력 경계를 완성합니다. | `.workspace/first-program/src/main/java/.../NumberReportApplication.java` | `./scripts/check-workspace.sh exercises/01-language-and-domain/01-first-program` | 통과·자기 설명 뒤 `exercises/01-language-and-domain/01-first-program/reference/`와 비교하고 도메인 타입으로 이동합니다. |
| 3 | [도메인 타입과 계약](docs/01-language-and-domain/03-domain-types-records-and-sealed-types.md) | — | [값 객체 계약](exercises/01-language-and-domain/02-value-object-contract/README.md)의 workspace를 만들고 생성 불변식을 구현합니다. | `.workspace/value-object-contract/src/main/java/.../Money.java` | `./scripts/check-workspace.sh exercises/01-language-and-domain/02-value-object-contract` | 아직 `reference/`를 보지 않고 컬렉션·숫자 계약으로 이동합니다. |
| 4 | [컬렉션·Stream과 숫자 불변식](docs/01-language-and-domain/04-collections-streams-and-numeric-invariants.md) | — | 같은 값 객체에 통화·정확한 연산·오버플로 계약을 적용합니다. | `.workspace/value-object-contract/src/main/java/.../Money.java` | `./scripts/check-workspace.sh exercises/01-language-and-domain/02-value-object-contract` | 아직 `reference/`를 보지 않고 오류·시간·식별자 문서로 이동합니다. |
| 5 | [오류·검증·시간과 식별자](docs/01-language-and-domain/05-errors-validation-time-and-identifiers.md) | — | 값 객체의 실패 전 상태 보존을 완성합니다. `Clock`과 작업 ID의 통합 적용은 capstone에서 수행합니다. | `.workspace/value-object-contract/src/main/java/.../Money.java` | `./scripts/check-workspace.sh exercises/01-language-and-domain/02-value-object-contract` | 통과·자기 설명 뒤 `exercises/01-language-and-domain/02-value-object-contract/reference/`와 비교하고 동시성 문서로 이동합니다. |
| 6 | [동시성 문서의 race·lock 절](docs/02-runtime-and-concurrency/01-concurrency-locking-and-executors.md) | — | [동시 상태 갱신](exercises/02-runtime-and-concurrency/01-concurrent-state-update/README.md)에서 learner 재현 프로그램을 실행하고 잠금 경계를 구현합니다. | `.workspace/concurrent-state-update/src/main/java/.../LockedCounter.java` | `./scripts/check-workspace.sh exercises/02-runtime-and-concurrency/01-concurrent-state-update` | 통과·자기 설명 뒤 해당 `reference/`와 비교하고 같은 문서의 실행기 절로 이동합니다. |
| 7 | [동시성 문서의 executor 절](docs/02-runtime-and-concurrency/01-concurrency-locking-and-executors.md) | — | [실행기 수명 주기](exercises/02-runtime-and-concurrency/02-executor-lifecycle/README.md)를 구현합니다. | `.workspace/executor-lifecycle/src/main/java/.../BoundedTaskRunner.java` | `./scripts/check-workspace.sh exercises/02-runtime-and-concurrency/02-executor-lifecycle` | 통과·자기 설명 뒤 해당 `reference/`와 비교하고 Maven 문서로 이동합니다. |
| 8 | [Maven Wrapper와 빌드 수명 주기](docs/03-build-test-and-evidence/01-maven-wrapper-and-lifecycle.md) | — | [여러 저장소를 잇는 Maven](exercises/03-build-test-and-evidence/01-multi-repository-maven/README.md)에서 설치 전 실패→artifact 설치→설치 후 성공을 관찰합니다. | —(관찰용 fixture는 읽기 전용) | `./exercises/03-build-test-and-evidence/01-multi-repository-maven/verify.sh` | 설치 전·후 evidence를 설명하고 JUnit 문서로 이동합니다. 별도 `reference/`는 없습니다. |
| 9 | [JUnit·AssertJ와 테스트 대역](docs/03-build-test-and-evidence/02-junit-assertj-and-test-doubles.md) | — | [상태와 효과 검증](exercises/03-build-test-and-evidence/02-state-and-effect-testing/README.md)을 구현합니다. | `.workspace/state-and-effect-testing/src/main/java/.../IdempotentOperationService.java` | `./scripts/check-workspace.sh exercises/03-build-test-and-evidence/02-state-and-effect-testing` | 통과·자기 설명 뒤 해당 `reference/`와 비교하고 품질 문서로 이동합니다. |
| 10 | [품질 검사·프로파일링과 근거](docs/03-build-test-and-evidence/03-quality-profiling-and-evidence.md) | — | 빠른 검사·전체 검증이 증명하는 범위와 JFR 실행기 evidence를 기록합니다. | — | `make check`, `VERIFY_LOG=/tmp/guide-java-verify.log make verify` | 검증 근거를 남기고 [누적 프로젝트 설계](docs/04-capstone.md)로 이동합니다. |
| 11 | [누적 프로젝트 설계](docs/04-capstone.md) | — | [동시 작업 원장](exercises/04-capstone/01-concurrent-job-ledger/README.md)을 완성합니다. | `.workspace/concurrent-job-ledger/src/main/java/.../jobledger/` | `./scripts/check-workspace.sh exercises/04-capstone/01-concurrent-job-ledger` | 통과·자기 설명 뒤 해당 `reference/`와 비교하고 전체 `make verify`로 종료합니다. |

## 예제와 실습 계약

[JVM 실행 환경 확인 예제](examples/runtime-model/README.md)는 현재 JVM, 운영체제, 문자 인코딩과 시간대를 실제 출력으로 확인합니다.

각 구현 실습은 다음 두 디렉터리를 사용합니다.

```text
skeleton/   테스트가 계약 위반을 드러내는 시작 상태
reference/  같은 테스트를 통과하는 비교용 구현
```

원본 `skeleton`은 루트 검증이 지정된 의미 계약에서 실패하는지 확인하는 배포 fixture이므로 직접 고치지 않습니다. 구현 실습은 다음처럼 안전한 학습자 복사본을 만든 뒤 정본 검사 명령으로 실행합니다.

```sh
./scripts/new-workspace.sh exercises/01-language-and-domain/01-first-program
./scripts/check-workspace.sh exercises/01-language-and-domain/01-first-program
```

복사 직후 검사는 의도한 의미 계약에서 실패합니다. `.workspace/first-program/`의 구현만 고쳐 같은 검사를 통과한 뒤 `reference`와 설계 차이를 비교합니다. 공개 테스트와 workspace POM은 검사기가 원본 계약과 같은지 확인하며, `reference`를 먼저 복사하는 것은 완료 기준이 아닙니다. `.workspace/`는 Git과 exact curriculum tree에서는 제외되지만 정식 검증의 격리 복사와 원본 상태 보존 대상에는 포함됩니다.

## Implementation annotation 읽는 법

완성된 예제와 `reference/`의 Implementation 번호 표식은 source line, runtime 호출 순서 또는 실제 Git history를 뜻하지 않습니다. 각 독립 프로젝트를 처음 구성한다고 가정한 **학습용 권장 구현 순서**이며, 한 프로젝트의 여러 파일을 오가는 순서를 공유합니다. 세부 단계는 `N-M`으로 표시하고 각 범위의 README가 전체 순서와 파일 간 연결을 설명합니다.

이 브랜치는 Maven archetype, project generator 또는 dependency 설치 명령으로 학습 프로젝트를 생성하지 않으므로 Implementation 0이 없습니다. `make prepare`는 저장소 검증 의존성 캐시 준비이고, workspace 생성 스크립트는 추적된 skeleton의 안전한 복사이므로 구현 bootstrap 번호로 세지 않습니다. 정답을 누설하지 않도록 `skeleton/`, 공개 테스트와 검증 infrastructure에는 이 표식을 넣지 않습니다.

## 다음 가이드와의 경계

이 저장소는 Java·JVM·Maven·JUnit의 주 소유자입니다. HTTP, 데이터베이스, 프레임워크와 분산 시스템을 Java 문법 안에 억지로 포함하지 않습니다.

- Spring의 Bean 수명, MVC, Security, JPA와 Actuator는 Spring Boot 백엔드 가이드에서 다룹니다.
- 관계 모델, 인덱스, MVCC, WAL과 실행 계획은 데이터베이스 시스템 가이드에서 다룹니다.
- 멱등성, Outbox, Saga, 이벤트 순서와 부분 실패는 분산 서비스 가이드에서 다룹니다.
