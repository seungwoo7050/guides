# 설정, 프로필과 준비 상태

운영 설정은 문자열 모음이 아니라 애플리케이션의 입력 계약이다. 주소, 제한값과 시간 단위가 잘못되었다면 첫 요청까지 기다리지 않고 시작 단계에서 실패해야 한다.

## 연관된 값을 타입으로 묶는다

여러 `@Value`에 흩어진 설정은 이름, 단위와 검증 규칙을 추적하기 어렵다. `@ConfigurationProperties`로 하나의 목적을 가진 값을 묶는다.

```java
@ConfigurationProperties("client.policy")
@Validated
public record PolicyClientProperties(
    @NotBlank String baseUrl,
    @NotNull Duration connectTimeout,
    @NotNull Duration readTimeout,
    @Positive int maxConnections) {

  public PolicyClientProperties {
    if (readTimeout != null && connectTimeout != null
        && readTimeout.compareTo(connectTimeout) < 0) {
      throw new IllegalArgumentException("readTimeout은 connectTimeout보다 짧을 수 없습니다.");
    }
  }
}
```

- 단위가 있는 값은 `Duration`, `DataSize` 같은 타입으로 받는다.
- 단일 값의 범위는 Bean Validation으로 검사한다.
- 여러 값 사이의 관계는 생성자나 별도 validator로 검사한다.
- 설정 클래스는 외부 호출이나 데이터 변경을 수행하지 않는다.

`@ConfigurationPropertiesScan` 또는 `@EnableConfigurationProperties` 중 어느 방식으로 등록하는지 명시한다. 테스트에서는 설정 Bean이 실제로 생성되는 Context를 한 번은 띄워 binding까지 확인한다.

## 기본값은 안전한 경우에만 둔다

개발 편의를 위한 기본값이 운영 누락을 숨길 수 있다.

- timeout과 batch size처럼 안전한 기본값은 코드에 둘 수 있다.
- credential, 공개 host와 암호화 key는 운영에서 필수로 받는다.
- 비밀값은 로그, exception message와 Actuator 환경 노출에 남기지 않는다.
- 환경 변수 이름을 바꾸면 배포 명세와 CI도 같은 변경에 포함한다.

설정 우선순위를 이용해 우연히 덮어쓰기보다 어떤 source를 허용하는지 문서화한다. 테스트는 최소한 기본 설정, 유효한 운영 설정과 잘못된 설정의 시작 실패를 포함한다.

## profile은 환경 묶음이지 기능 플래그가 아니다

profile은 실행 환경 차이를 표현한다.

```text
local       로컬 애플리케이션 + 컨테이너 의존성
test        Testcontainers, 고정 Clock, 짧은 poll interval
production  외부 주소와 secret 필수, 진단 노출 제한
```

세부 업무 기능마다 profile을 추가하면 가능한 조합이 폭증한다. 기능 플래그가 필요하다면 이름, 기본값, 제거 시점과 관찰 지표를 별도 계약으로 둔다.

## 실행됨과 요청 가능함을 구분한다

Spring Context가 생성되었다고 모든 요청을 처리할 준비가 끝난 것은 아니다.

- liveness: 프로세스가 스스로 회복할 수 없는 상태인가?
- readiness: 새 요청을 받아도 되는가?

일시적인 Kafka 지연이나 외부 API 장애로 liveness를 실패시키면 재시작이 반복될 수 있다. 반대로 필수 migration이 끝나지 않았거나 연결 풀이 구성되지 않았다면 readiness는 실패해야 한다.

readiness check가 외부 시스템에 매번 비싼 요청을 보내지 않도록 한다. 상태는 짧게 평가하고, 상세 원인은 로그와 metric에서 확인한다. 실제 host·container probe 설정은 `guide-web-infrastructure`가 담당하고, 이 가이드는 애플리케이션이 올바른 health group을 노출하는 데 집중한다.

## 정상 종료도 시작 계약의 일부다

종료 신호를 받으면 다음 순서가 필요하다.

```text
readiness 해제
→ 새 요청·새 background 작업 거부
→ 진행 중 요청과 transaction 제한 시간 안에 완료
→ consumer·scheduler·executor 중지
→ 연결과 Context 종료
```

종료 제한 시간을 무한히 늘리지 않는다. 처리 중이던 작업이 중단될 수 있다는 전제로 Outbox와 consumer가 다시 복구할 수 있어야 한다.

## 실습

[애플리케이션 경계 실습](../../exercises/application-boundaries/README.md)에서 두 설정값의 관계가 잘못되면 Context가 시작되지 않는지 확인한다. [단일 서비스 통합 과제](../../exercises/single-service-capstone/README.md)에서는 외부 client 설정, 데이터베이스 migration과 health endpoint를 함께 검증한다.
