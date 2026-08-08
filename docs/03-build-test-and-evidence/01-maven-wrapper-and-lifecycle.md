# Maven Wrapper와 빌드 수명 주기

소스가 같아도 Maven, JDK, 플러그인과 로컬 저장소 상태가 다르면 빌드 결과가 달라질 수 있습니다. 빌드 도구를 배우는 목적은 POM 문법을 외우는 것이 아니라 소스가 어떤 입력과 단계로 검증 가능한 산출물이 되는지 이해하는 것입니다.

## Wrapper와 실행 JDK

이 저장소는 Maven Wrapper 3.3.4와 Apache Maven 3.9.16을 사용합니다.

```sh
./mvnw -version
```

Wrapper는 Maven 배포본과 SHA-256을 고정하지만 JDK를 설치하지 않습니다. Maven 출력에는 실행 JDK 21이 표시되고 컴파일러에는 `--release 17`이 전달되어야 합니다.

`prepare.sh`는 Wrapper를 실행하고 프로젝트 의존성과 플러그인을 `.guide/java/maven-repository`에 준비합니다. `verify.sh`는 이 저장소를 오프라인으로 사용하므로 검증 중 임의의 새 버전을 내려받지 않습니다.

## POM과 좌표

Maven artifact는 기본적으로 다음 좌표로 식별됩니다.

```text
groupId : artifactId : version
```

POM은 프로젝트 좌표, 의존성, 플러그인, 모듈과 빌드 속성을 선언합니다. 같은 파일이 옆 디렉터리에 있다는 사실만으로 의존성이 연결되지는 않습니다.

이 저장소의 루트 POM은 packaging이 `pom`인 parent이자 reactor입니다.

- 공통 Java release와 테스트 의존성을 제공합니다.
- reference 모듈 목록을 선언합니다.
- Maven Enforcer, Spotless와 Checkstyle을 `verify`에 연결합니다.
- skeleton은 의도적으로 실패하므로 reactor에 포함하지 않습니다.

## 수명 주기 단계

| 단계 | 역할 |
|---|---|
| `validate` | 프로젝트 구조와 설정을 확인합니다. |
| `compile` | 주 소스를 컴파일합니다. |
| `test` | 테스트 소스를 컴파일하고 단위 테스트를 실행합니다. |
| `package` | JAR 같은 산출물을 만듭니다. |
| `verify` | 통합 검사와 품질 검사를 수행합니다. |
| `install` | 산출물을 로컬 Maven 저장소에 게시합니다. |
| `deploy` | 원격 저장소에 게시합니다. |

`package` 성공을 전체 품질 검사 성공으로 기록하지 않습니다. 이 가이드의 정본 검증은 루트 `./verify.sh`입니다.

## 의존성 scope

- `compile`은 주 코드와 소비자에게 필요한 기본 scope입니다.
- `runtime`은 컴파일에는 필요 없지만 실행에 필요합니다.
- `test`는 테스트 컴파일과 실행에만 사용합니다.
- `provided`는 컴파일에는 필요하지만 실행 환경이 제공한다고 가정합니다.

scope를 넓게 잡으면 테스트 라이브러리가 배포 classpath에 새거나 소비자에게 불필요한 의존성이 전파될 수 있습니다. 실제 사용 경계에 맞춰 선택합니다.

## parent와 dependency management

parent POM은 공통 속성과 플러그인 설정을 상속합니다. `dependencyManagement`는 버전을 정렬하지만 그 의존성을 자동으로 추가하지는 않습니다. 모듈은 필요한 dependency를 직접 선언합니다.

플러그인도 결과에 영향을 주므로 핵심 플러그인 버전을 고정합니다. BOM이 라이브러리 버전을 관리해도 compiler, test runner와 formatter 버전까지 모두 정하지는 않습니다.

실제 적용 결과는 다음 명령으로 확인합니다.

```sh
./mvnw help:effective-pom
./mvnw dependency:tree
```

## reactor와 `-pl`, `-am`

루트에서 Maven을 실행하면 `<modules>` 순서에 따라 reactor를 구성합니다.

```sh
./mvnw -pl :executor-lifecycle-reference -am test
```

- `-pl`은 선택할 project를 정합니다.
- `-am`은 선택한 project가 필요로 하는 reactor module도 함께 만듭니다.

artifactId가 중복되지 않게 유지하면 경로보다 의미 있는 선택이 가능합니다.

## 로컬 Maven 저장소

Maven 로컬 저장소는 source checkout이 아니라 이미 만들어진 artifact와 metadata의 캐시입니다. 오래된 SNAPSHOT이 남아 있으면 현재 소스를 빌드하지 않고도 소비 모듈이 성공할 수 있습니다.

격리된 저장소를 사용하면 숨은 상태를 발견할 수 있습니다.

```sh
repository=$(mktemp -d)
./mvnw -Dmaven.repo.local="$repository" clean verify
```

[여러 저장소를 잇는 Maven 실습](../../exercises/03-build-test-and-evidence/01-multi-repository-maven/README.md)은 다음 순서를 자동으로 검사합니다.

```text
소비 모듈 실패
→ 생산 모듈 install
→ 소비 모듈 성공
```

생산 소스를 고친 뒤 다시 install하지 않으면 소비자는 이전 artifact를 사용할 수 있습니다. source의 최신 상태와 local repository의 최신 상태를 구분합니다.

## 재현 가능한 빌드 입력

빌드에 영향을 주는 입력을 명시합니다.

- JDK와 Maven 버전
- POM과 plugin 버전
- 소스 인코딩과 시간대
- dependency repository와 lock에 해당하는 버전 정책
- 환경 변수와 생성 소스
- OS에 따라 달라지는 명령

이 저장소는 `.mvn/jvm.config`에서 UTF-8과 UTC를 고정합니다. 테스트는 기본 시간대에 기대지 않고 `Clock`과 명시적인 zone을 사용합니다.

## 자주 쓰는 명령

| 목적 | 명령 |
|---|---|
| Maven과 JDK 확인 | `./mvnw -version` |
| 빠른 단위 테스트 | `./mvnw test` |
| reactor와 품질 검사 | `./mvnw verify` |
| 한 모듈과 선행 모듈 | `./mvnw -pl :artifact-id -am verify` |
| 한 테스트 클래스 | `./mvnw -Dtest=ClassName test` |
| 의존성 트리 | `./mvnw dependency:tree` |
| 실제 POM | `./mvnw help:effective-pom` |
| 형식 자동 수정 | `./mvnw spotless:apply` |
| 생성물 정리 | `./mvnw clean` |

`-DskipTests`는 테스트 실행을 건너뛰지만 테스트 소스를 컴파일할 수 있습니다. `-Dmaven.test.skip=true`는 테스트 컴파일도 생략하므로 일반 검증에서 사용하지 않습니다.

## 완료 기준

- Wrapper, Maven과 실행 JDK의 역할을 구분합니다.
- `test`, `package`, `verify`, `install`의 증명 범위를 설명합니다.
- parent, reactor, dependency management와 실제 dependency 선언을 구분합니다.
- 격리된 로컬 저장소에서 숨은 SNAPSHOT 상태를 찾습니다.
- `effective-pom`과 `dependency:tree`로 실제 빌드 입력을 확인합니다.

다음은 [JUnit·AssertJ와 테스트 대역](02-junit-assertj-and-test-doubles.md)입니다.
