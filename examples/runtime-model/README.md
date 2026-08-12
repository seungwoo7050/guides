# JVM 실행 환경 확인 예제

다음 명령은 예제를 컴파일한 뒤 현재 JVM과 운영체제 정보를 출력합니다.

## 권장 구현 순서

이 예제 디렉터리 전체가 하나의 numbering scope입니다. 번호는 Git 이력이 아니라 같은 관찰 도구를 다시 만든다면 따를 학습용 권장 구현 순서이며, 실제 project generator가 없으므로 Implementation 0은 없습니다.

| 순서 | 구현 위치 | 책임 |
|---:|---|---|
| 1 | `pom.xml` | 고정된 루트 빌드를 상속하는 독립 관찰 모듈의 좌표를 정합니다. |
| 2 | `RuntimeProbe.main` | JVM과 운영체제가 소유한 실행 환경을 명시적인 `key=value` evidence로 출력합니다. |

## 실행과 관찰

```sh
./mvnw -pl :runtime-model package
java -cp examples/runtime-model/target/classes dev.guides.java.runtime.RuntimeProbe
```

출력에는 JDK 버전, Java 설치 경로, 운영체제와 CPU 구조, 기본 문자 인코딩과 시간대가 포함됩니다. 로컬에서만 발생하는 빌드나 실행 오류를 공유할 때 이 정보를 함께 남기면 환경 차이를 빠르게 좁힐 수 있습니다.
