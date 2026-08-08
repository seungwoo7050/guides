# JVM 실행 환경 확인 예제

다음 명령은 예제를 컴파일한 뒤 현재 JVM과 운영체제 정보를 출력합니다.

```sh
./mvnw -pl :runtime-model package
java -cp examples/runtime-model/target/classes dev.guides.java.runtime.RuntimeProbe
```

출력에는 JDK 버전, Java 설치 경로, 운영체제와 CPU 구조, 기본 문자 인코딩과 시간대가 포함됩니다. 로컬에서만 발생하는 빌드나 실행 오류를 공유할 때 이 정보를 함께 남기면 환경 차이를 빠르게 좁힐 수 있습니다.
