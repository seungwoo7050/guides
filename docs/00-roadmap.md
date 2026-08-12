# Java 학습 로드맵

이 가이드는 Java 문법을 모두 외운 뒤 프로젝트를 시작하게 만드는 과정이 아닙니다. 첫 프로그램을 컴파일하고 실행할 수 있는 최소 기반을 만든 뒤, 실제 구현에서 반복되는 타입·상태·오류·동시성·빌드·검증 계약을 단계적으로 추가합니다.

## 대상 독자

다음 중 하나에 해당한다면 1부부터 시작합니다.

- 프로그래밍을 처음 배우며 Java를 첫 언어로 선택했습니다.
- 다른 언어는 사용했지만 Java의 값·참조·객체·예외 모델이 낯섭니다.
- Java 코드를 작성해 보았지만 Maven, 테스트와 동시성까지 한 흐름으로 검증해 본 적은 없습니다.

조건, 반복, 함수, 배열과 클래스가 익숙하고 `javac`와 `java`의 차이를 설명할 수 있다면 1부의 익숙한 절은 빠르게 확인해도 됩니다. 다만 각 부의 완료 기준과 연결 실습은 건너뛰지 않는 편이 좋습니다.

## 선행지식과 도구

필수 선행 언어는 없습니다. 터미널에서 현재 디렉터리를 확인하고 파일을 만들 수 있으면 시작할 수 있습니다.

도구 계약은 다음과 같습니다.

- Linux 또는 macOS
- JDK 21(컴파일 대상은 Java 17 API·바이트코드)
- Bash, `curl`, `python3`, `make`
- 저장소의 `./mvnw`

최초 적용과 의존성 준비는 저장소 루트에서 수행합니다.

```sh
make prepare
make check
```

이후 전체 검증은 다음 한 명령으로 실행합니다.

```sh
VERIFY_LOG=/tmp/guide-java-verify.log make verify
make clean
```

## 이 가이드가 소유하는 범위

이 저장소는 다음 주제의 기본 설명과 검증을 소유합니다.

- Java 소스, 바이트코드, JDK와 JVM
- Java 17의 값·참조·클래스·인터페이스·record·sealed type
- 컬렉션, Stream, 정수 오버플로와 `BigDecimal`
- 예외, 입력 검증, 자원 수명, `Clock`과 식별자
- JVM 내부 공유 상태의 동시성, 잠금, 인터럽트와 실행기
- Maven Wrapper, reactor, 로컬 저장소와 빌드 수명 주기
- JUnit, AssertJ, 테스트 대역, 정적 검사와 JFR

다음은 다른 전문 가이드의 영역입니다.

- Spring IoC, MVC, Security, JPA와 Actuator
- 데이터베이스 저장 구조, 인덱스, MVCC, WAL과 실행 계획
- 여러 서비스 사이의 멱등성, Outbox, Saga와 부분 실패
- 호스트, 컨테이너, TLS, 배포, 관측 저장소와 복구 운영

이 문서에서 전문 영역이 필요하면 개념을 새로 확장하지 않고 경계를 짧게 설명합니다.

## 종료 능력

완료 여부는 읽은 문서 수가 아니라 다음 능력으로 판단합니다.

1. 빈 디렉터리에서 패키지와 `main` 메서드가 있는 프로그램을 컴파일하고 실행합니다.
2. 값 객체가 생성 시점부터 유효하고 가변 컬렉션이 소유권 밖으로 새지 않게 설계합니다.
3. 순서·중복·단위·반올림·오버플로 같은 데이터 계약을 테스트로 고정합니다.
4. 입력 오류, 상태 거절과 실행 환경의 실패를 서로 다른 경계에서 처리합니다.
5. 시간과 식별자를 외부에서 주입해 테스트를 재현할 수 있습니다.
6. 경쟁 상태를 우연한 `sleep` 없이 재현하고 올바른 원자성 범위를 선택합니다.
7. 제한된 실행기의 큐, 거절, 취소, 인터럽트와 종료를 검증합니다.
8. Maven Wrapper로 여러 모듈을 빌드하고 격리된 로컬 저장소에서 의존 관계를 확인합니다.
9. 단위 테스트, 상태·효과 검사, 코드 품질 검사와 프로파일링 근거를 구분합니다.
10. 동시 작업 원장 capstone의 learner workspace를 완성하고 정본 검사와 전체 검증을 통과합니다.

## 학습 경로

### 1부: 언어와 도메인

| 순서 | 문서 | 실습 | 완료 기준 |
|---:|---|---|---|
| 1 | [JDK·JVM과 첫 프로그램](01-language-and-domain/01-jdk-jvm-and-first-program.md) | [JVM 실행 환경 확인](../examples/runtime-model/README.md) → [첫 명령행 프로그램](../exercises/01-language-and-domain/01-first-program/README.md) | 환경을 관찰한 뒤 직접 컴파일·실행하고 종료 상태와 출력 경계를 설명합니다. |
| 2 | [Java 언어 기초](01-language-and-domain/02-java-language-foundations.md) | 첫 명령행 프로그램 확장 | 값과 참조, 분기·반복·메서드·배열·클래스의 역할을 구분합니다. |
| 3 | [도메인 타입과 계약](01-language-and-domain/03-domain-types-records-and-sealed-types.md) | [값 객체 계약](../exercises/01-language-and-domain/02-value-object-contract/README.md) | 생성자가 불변식을 만들고 타입이 잘못된 조합을 차단합니다. |
| 4 | [컬렉션·Stream과 숫자 불변식](01-language-and-domain/04-collections-streams-and-numeric-invariants.md) | 값 객체 계약 | 순서·중복·소유권과 정확한 계산 규칙을 선택합니다. |
| 5 | [오류·검증·시간과 식별자](01-language-and-domain/05-errors-validation-time-and-identifiers.md) | 값 객체 계약 완성, `Clock`·작업 ID는 capstone에서 통합 | 실패 종류와 검증 위치를 구분하고 후속 통합 위치를 설명합니다. |

### 2부: 실행 상태와 동시성

| 순서 | 문서 | 실습 | 완료 기준 |
|---:|---|---|---|
| 6 | [동시성·잠금과 실행기](02-runtime-and-concurrency/01-concurrency-locking-and-executors.md) | [동시 상태 갱신](../exercises/02-runtime-and-concurrency/01-concurrent-state-update/README.md) | 읽기·판단·쓰기의 경쟁을 결정적으로 재현합니다. |
| 7 | 같은 문서의 실행기 절 | [실행기 수명 주기](../exercises/02-runtime-and-concurrency/02-executor-lifecycle/README.md) | 큐·거절·취소·인터럽트·종료 계약을 검증합니다. |

### 3부: 빌드, 테스트와 근거

| 순서 | 문서 | 실습 | 완료 기준 |
|---:|---|---|---|
| 8 | [Maven Wrapper와 빌드 수명 주기](03-build-test-and-evidence/01-maven-wrapper-and-lifecycle.md) | [여러 저장소를 잇는 Maven](../exercises/03-build-test-and-evidence/01-multi-repository-maven/README.md) | source checkout과 Maven artifact의 상태를 구분합니다. |
| 9 | [JUnit·AssertJ와 테스트 대역](03-build-test-and-evidence/02-junit-assertj-and-test-doubles.md) | [상태와 효과 검증](../exercises/03-build-test-and-evidence/02-state-and-effect-testing/README.md) | 반환값뿐 아니라 상태·효과와 실패 뒤 상태를 확인합니다. |
| 10 | [품질 검사·프로파일링과 근거](03-build-test-and-evidence/03-quality-profiling-and-evidence.md) | 루트 전체 검사 | 각 명령이 증명하는 범위를 과장하지 않고 기록합니다. |

### 통합: 동시 작업 원장

[누적 프로젝트 설계](04-capstone.md)를 읽고 [동시 작업 원장](../exercises/04-capstone/01-concurrent-job-ledger/README.md)의 skeleton을 완성합니다.

capstone은 다음을 한 문제에서 결합합니다.

- record와 sealed interface
- 입력 불변식과 정확한 정수 계산
- `Clock`과 식별자
- 중복 작업의 단일 적용
- 잠금과 제한된 실행기
- 인터럽트와 종료
- Maven reactor와 JUnit 검증

## 실습 사용 원칙

각 구현 실습은 `skeleton`과 `reference`를 제공합니다.

1. 관련 문서와 좁은 관찰 예제가 있으면 먼저 확인합니다.
2. `./scripts/new-workspace.sh exercises/<경로>`로 learner workspace를 만듭니다.
3. `./scripts/check-workspace.sh exercises/<경로>`로 지정된 초기 실패를 확인합니다.
4. 원본 skeleton과 공개 테스트가 아니라 `.workspace/<이름>/src/main/` 구현만 수정합니다.
5. 정상 사례와 실패·경계 사례를 같은 workspace 검사로 모두 통과시킵니다.
6. 자신의 구현을 설명한 뒤에만 exercise-local `reference/` 소스를 비교합니다.

reference를 복사해 테스트를 통과하는 것은 학습 완료가 아닙니다. 반대로 reference와 구조가 다르더라도 같은 계약을 더 명확하게 지키고 검증할 수 있다면 올바른 해답이 될 수 있습니다.

`multi-repository-maven`은 이 흐름의 분석·관찰형 예외입니다. 추적된 두 모듈을 수정하지 않고 격리된 임시 Maven 저장소에서 설치 전 실패와 설치 후 성공을 관찰하며, 별도 learner workspace나 `reference/`를 만들지 않습니다.
