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

저장소 루트에서 다음 두 명령을 순서대로 실행합니다.

```sh
./prepare.sh
VERIFY_LOG=/tmp/guide-java-verify.log ./verify.sh
```

`prepare.sh`는 소스·파일 모드·심볼릭 링크·Git index를 바꾸지 않고 Maven Wrapper와 프로젝트 의존성을 `.guide/java/`에 준비합니다. 입력 fingerprint와 도구 버전은 `.guide/java/prepared.json`에 원자적으로 기록되며 같은 상태에서 다시 실행해도 결과가 달라지지 않습니다.

`verify.sh`는 현재 working tree를 저장소 밖 임시 디렉터리로 복사하고 준비된 의존성을 오프라인으로 사용합니다. 문서 링크, 정확한 tree, 셸 문법, `javac --release 17`, Maven reference 모듈, 실패해야 하는 skeleton, 격리된 로컬 저장소 실습과 JFR 기록을 검사하며 전체 로그는 저장소 밖의 절대 `VERIFY_LOG`에 남깁니다.

## 읽는 순서

전체 지도와 선택 경로는 [학습 로드맵](docs/00-roadmap.md)에 있습니다.

| 구간 | 문서 | 연결 실습 |
|---|---|---|
| 1부 | [JDK·JVM과 첫 프로그램](docs/01-language-and-domain/01-jdk-jvm-and-first-program.md) | [첫 명령행 프로그램](exercises/01-language-and-domain/01-first-program/README.md) |
| 1부 | [Java 언어 기초](docs/01-language-and-domain/02-java-language-foundations.md) | 첫 명령행 프로그램 확장 |
| 1부 | [도메인 타입과 계약](docs/01-language-and-domain/03-domain-types-records-and-sealed-types.md) | [값 객체 계약](exercises/01-language-and-domain/02-value-object-contract/README.md) |
| 1부 | [컬렉션·Stream과 숫자 불변식](docs/01-language-and-domain/04-collections-streams-and-numeric-invariants.md) | 값 객체 계약 |
| 1부 | [오류·검증·시간과 식별자](docs/01-language-and-domain/05-errors-validation-time-and-identifiers.md) | 값 객체 계약 |
| 2부 | [동시성·잠금과 실행기](docs/02-runtime-and-concurrency/01-concurrency-locking-and-executors.md) | [동시 상태 갱신](exercises/02-runtime-and-concurrency/01-concurrent-state-update/README.md), [실행기 수명 주기](exercises/02-runtime-and-concurrency/02-executor-lifecycle/README.md) |
| 3부 | [Maven Wrapper와 빌드 수명 주기](docs/03-build-test-and-evidence/01-maven-wrapper-and-lifecycle.md) | [여러 저장소를 잇는 Maven](exercises/03-build-test-and-evidence/01-multi-repository-maven/README.md) |
| 3부 | [JUnit·AssertJ와 테스트 대역](docs/03-build-test-and-evidence/02-junit-assertj-and-test-doubles.md) | [상태와 효과 검증](exercises/03-build-test-and-evidence/02-state-and-effect-testing/README.md) |
| 3부 | [품질 검사·프로파일링과 근거](docs/03-build-test-and-evidence/03-quality-profiling-and-evidence.md) | 전체 저장소 검증 |
| 통합 | [누적 프로젝트 설계](docs/04-capstone.md) | [동시 작업 원장](exercises/04-capstone/01-concurrent-job-ledger/README.md) |

## 예제와 실습 계약

[JVM 실행 환경 확인 예제](examples/runtime-model/README.md)는 현재 JVM, 운영체제, 문자 인코딩과 시간대를 실제 출력으로 확인합니다.

각 구현 실습은 다음 두 디렉터리를 사용합니다.

```text
skeleton/   테스트가 계약 위반을 드러내는 시작 상태
reference/  같은 테스트를 통과하는 비교용 구현
```

기본 학습 순서는 `skeleton`을 직접 고치고 공개 테스트를 통과한 뒤 `reference`와 설계 차이를 비교하는 것입니다. `reference`를 먼저 복사하는 것은 완료 기준이 아닙니다.

## 다음 가이드와의 경계

이 저장소는 Java·JVM·Maven·JUnit의 주 소유자입니다. HTTP, 데이터베이스, 프레임워크와 분산 시스템을 Java 문법 안에 억지로 포함하지 않습니다.

- Spring의 Bean 수명, MVC, Security, JPA와 Actuator는 Spring Boot 백엔드 가이드에서 다룹니다.
- 관계 모델, 인덱스, MVCC, WAL과 실행 계획은 데이터베이스 시스템 가이드에서 다룹니다.
- 멱등성, Outbox, Saga, 이벤트 순서와 부분 실패는 분산 서비스 가이드에서 다룹니다.
