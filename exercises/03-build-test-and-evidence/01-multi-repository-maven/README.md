# 여러 저장소를 잇는 Maven 실습

생산 모듈의 소스가 옆 디렉터리에 있어도 소비 모듈은 Maven 저장소에서 게시된 산출물을 찾습니다. 이 실습은 두 모듈을 서로 독립된 저장소처럼 실행해 설치 순서와 로컬 저장소 상태를 확인합니다.

## 목표

source checkout, 빌드 산출물과 로컬 Maven 저장소를 구분하고, 생산 artifact의 설치 전 실패와 설치 후 성공을 네트워크 없이 재현합니다.

## 권장 구현 순서

추적된 두 Maven module은 learner가 고치는 skeleton이 아니라 이 관찰 실습을 위한 first-party 완성 fixture입니다. 두 module 전체를 하나의 numbering scope로 보고, 번호는 실제 과거 작성 순서가 아니라 같은 artifact boundary를 구성할 때의 학습용 권장 순서를 뜻합니다. Maven archetype이나 project init을 사용하지 않으므로 Implementation 0은 없습니다.

| 순서 | 구현 위치·명령 | 책임 |
|---:|---|---|
| 1 | `contract-library/pom.xml` | producer artifact의 좌표와 Java build boundary를 고정합니다. |
| 1-1 | `ContractVersion` | consumer가 사용할 최소 public contract를 제공합니다. |
| 2 | `consumer-service/pom.xml` | source directory가 아니라 producer의 정확한 artifact 좌표에 의존합니다. |
| 2-1 | `ConsumerApplication` | 설치된 contract를 사용하는 최소 consumer 경계를 만듭니다. |
| [Implementation 3] | `verify.sh`의 `"$ROOT/mvnw" "${COMMON[@]}" -f "$EXERCISE/contract-library/pom.xml" clean install` | source construction 뒤 producer artifact를 격리 저장소에 게시하는 실제 중간 Maven CLI입니다. |

```text
contract-library/   소비자가 사용할 계약 JAR을 만듭니다.
consumer-service/   계약의 SNAPSHOT 버전을 의존성으로 사용합니다.
```

`prepare.sh`가 준비한 의존성 캐시를 임시 저장소로 복사한 뒤, 내부 계약 산출물만 제거합니다. 검증은 네트워크 없이 다음 순서를 확인합니다.

## 관찰할 근거

1. 계약 설치 전 소비 모듈 빌드는 실패합니다.
2. 계약 모듈을 임시 저장소에 설치합니다.
3. 소비 모듈의 테스트가 성공합니다.
4. 임시 저장소와 로그를 제거합니다.

```sh
./exercises/03-build-test-and-evidence/01-multi-repository-maven/verify.sh
```

공개 명령은 `make prepare`가 기록한 `.guide/java/prepared.json`에서 준비 cache를 읽습니다. 전체 검증처럼 `GUIDE_MAVEN_REPOSITORY`와 `MAVEN_USER_HOME`이 주어진 격리 환경에서는 그 경로를 사용합니다.

이 실습은 checkout, 소스 디렉터리, 빌드 산출물과 Maven 저장소가 각각 다른 상태라는 점을 보여 줍니다.

이 실습은 구현 skeleton을 고치는 과제가 아니라 추적된 두 모듈을 관찰용 fixture로 사용합니다. 원본 소스를 수정하지 않으며 위 검증 명령이 실행별 내부 workspace와 임시 Maven 저장소를 만들고 성공·실패 경로에서 모두 정리합니다. 다른 여섯 구현 실습의 top-level `.workspace/`와 역할이 다릅니다.

## 완료 기준

- [ ] 준비 캐시를 복제한 임시 저장소에서 계약 artifact만 제거한 상태를 만듭니다.
- [ ] 생산 모듈 설치 전 소비 빌드가 dependency resolution 실패로 끝났음을 로그로 구분합니다.
- [ ] 계약을 `install`한 뒤 같은 임시 저장소에서 소비 테스트가 성공하고 workspace가 정리됩니다.

## 자기 설명

- 옆 디렉터리에 생산 소스가 있는데도 소비자의 Maven 빌드가 실패하는 이유는 무엇인가요?
- 기존 로컬 저장소를 그대로 쓰면 설치 순서 실습이 거짓 양성으로 끝날 수 있는 이유는 무엇인가요?

## 검증

```sh
./exercises/03-build-test-and-evidence/01-multi-repository-maven/verify.sh
```
