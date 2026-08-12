# Application Context와 Bean 수명

Spring Boot의 핵심은 어노테이션 자체가 아니라 **Application Context가 객체 그래프를 조립하고 수명을 관리한다는 사실**이다. 객체 생성 위치와 proxy 통과 여부를 모르면 설정, 트랜잭션, 보안과 재시도가 우연히 동작하는 코드를 만들게 된다.

## 진입점은 탐색 범위를 정한다

`@SpringBootApplication`은 설정 클래스, 자동 설정과 component scan을 묶는다. 진입점은 애플리케이션의 공통 상위 패키지에 둔다.

```java
package dev.guides.catalog;

@SpringBootApplication
public class CatalogApplication {
  public static void main(String[] args) {
    SpringApplication.run(CatalogApplication.class, args);
  }
}
```

진입점 바깥의 `@Service`나 `@Configuration`은 자동으로 발견되지 않는다. 넓은 `scanBasePackages`로 우연히 포함하기보다 패키지 경계와 명시적인 `@Import`로 조립 의도를 드러낸다.

## 업무 객체는 의존성을 생성하지 않는다

필수 의존성은 생성자로 요구한다.

```java
@Service
public final class CatalogService {
  private final ProjectRepository projects;
  private final Clock clock;

  public CatalogService(ProjectRepository projects, Clock clock) {
    this.projects = projects;
    this.clock = clock;
  }
}
```

생성자 주입은 다음 계약을 노출한다.

- 객체가 유효하려면 반드시 필요한 협력자
- 테스트에서 대체해야 하는 경계
- 객체 생성 직후부터 성립해야 하는 불변식

필드 주입은 초기화 전 상태와 숨은 의존성을 만들기 쉽다. 같은 타입 Bean이 여러 개라면 임의의 `@Primary`로 감추지 말고 `@Qualifier`나 목적이 다른 interface로 의미를 표현한다.

## singleton은 동시에 호출된다

기본 singleton scope는 JVM 전체가 아니라 Context마다 객체 하나라는 뜻이다. 여러 요청이 같은 Bean을 동시에 호출하므로 다음 상태를 singleton 필드에 두지 않는다.

- 현재 사용자
- 현재 요청의 DTO
- 요청별 임시 collection
- transaction마다 달라지는 entity

공유해야 하는 상태는 thread-safe해야 하고, 요청 상태는 method parameter나 명시적인 request scope에 둔다. request scope를 남용하면 업무 코드가 웹 수명에 결합되므로 먼저 parameter 전달이 가능한지 확인한다.

## 초기화와 준비 상태를 분리한다

Bean 수명은 대략 다음 순서다.

```text
Bean 정의 읽기
→ 객체 생성
→ 의존성 연결
→ 초기화 callback
→ 요청 처리
→ 종료 callback
```

생성자와 `@PostConstruct`에는 빠르고 결정적인 객체 검증만 둔다. 느린 외부 통신, 데이터 보정이나 메시지 발행을 넣으면 Context 생성과 운영 복구 정책이 섞인다. 요청 준비 여부는 readiness에서, 정상 종료는 lifecycle과 shutdown 설정에서 다룬다.

외부 자원을 소유한 Bean은 종료 경로도 가져야 한다. executor, client connection과 background worker를 만들었다면 Context 종료 때 새 작업을 거부하고 진행 중인 작업을 제한 시간 안에 마친다.

## proxy가 적용되는 호출 경로를 확인한다

Spring의 transaction, method security와 Resilience4j annotation은 대부분 proxy를 통해 동작한다.

```text
호출자 → Spring proxy → 대상 Bean method
```

다음 호출은 기대한 advice를 통과하지 않을 수 있다.

- 같은 객체가 자신의 `@Transactional` method를 직접 호출한다.
- `new`로 만든 객체의 annotation method를 호출한다.
- proxy가 가로챌 수 없는 method를 사용한다.
- 테스트에서 대상 객체만 직접 생성하고 proxy 효과까지 검증했다고 판단한다.

업무 단계를 별도 Bean으로 분리하면 transaction과 retry 경계가 코드 구조에 드러난다. annotation이 붙어 있다는 사실보다 **실제 호출이 proxy를 통과하는지**를 테스트한다.

## 요청 처리 책임을 나눈다

Spring MVC 요청은 다음 경계를 통과한다.

```text
Filter / SecurityFilterChain
→ DispatcherServlet
→ argument binding / HttpMessageConverter
→ Bean Validation
→ Controller
→ application service
→ repository 또는 외부 adapter
→ exception translation / response conversion
```

- Controller는 HTTP 입력을 애플리케이션 명령으로 바꾼다.
- application service는 업무 순서와 transaction 경계를 정한다.
- repository는 영속 상태 접근을 캡슐화한다.
- 외부 client는 protocol, timeout과 오류 번역을 담당한다.

Controller가 entity를 직접 받고 반환하면 외부 계약, 저장 모델과 lazy loading이 한 경계에 섞인다. 요청·응답 DTO와 entity를 분리한다.

## 다음 단계

[설정·프로필·준비 상태](02-configuration-profiles-and-readiness.md)에서 이 객체 그래프가 어떤 설정으로 시작되고 실패하는지 이어서 확인한다. 애플리케이션 경계 실습은 MVC 입력·오류 계약까지 읽은 뒤 시작한다. 다음 질문은 그 실습까지 가져간다.

- 어떤 객체가 Context에 의해 생성되는가?
- 요청별 값이 singleton 필드에 남지 않는가?
- 설정 오류는 첫 요청이 아니라 시작 단계에서 드러나는가?
- HTTP 오류 변환은 Controller마다 반복되지 않는가?
