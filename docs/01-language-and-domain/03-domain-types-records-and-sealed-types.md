# 도메인 타입과 계약

`long amount`, `String currency`, `String id`처럼 원시 값만 전달하면 단위, 허용 범위와 조합 규칙을 호출부에서 반복해서 추측하게 됩니다. 타입은 이름을 붙이는 장식이 아니라 잘못된 상태와 연산을 생성 경계에서 차단하는 도구입니다.

## 값 객체와 엔터티

값 객체는 구성 값이 같으면 같은 값입니다. 엔터티는 시간이 지나 필드가 바뀌어도 같은 식별자를 가진 대상을 뜻합니다.

- 금액, 기간, 이메일 주소와 작업 식별자는 값 객체 후보입니다.
- 사용자, 주문과 계좌는 식별자를 가진 엔터티 후보입니다.
- 엔터티의 모든 가변 필드를 `equals`에 넣으면 상태 변경 전후에 컬렉션 키의 의미가 바뀔 수 있습니다.

값 객체는 생성 시점부터 유효해야 합니다.

```java
public record JobId(String value) {
  public JobId {
    if (value == null || value.isBlank()) {
      throw new IllegalArgumentException("작업 식별자가 필요합니다.");
    }
    value = value.trim();
  }
}
```

record가 접근자, `equals`, `hashCode`와 `toString`을 만들어 주더라도 불변식을 자동으로 만들지는 않습니다. 구성 요소에 가변 컬렉션이 있다면 생성할 때 복사하고 반환할 때도 수정할 수 없는 값으로 노출합니다.

```java
public record Batch(List<JobId> jobs) {
  public Batch {
    jobs = List.copyOf(Objects.requireNonNull(jobs, "jobs"));
  }
}
```

## 생성자와 팩터리

항상 참이어야 하는 규칙은 생성자에 둡니다. 입력 형식 해석이나 여러 생성 경로를 이름으로 구분해야 하면 정적 팩터리를 사용할 수 있습니다.

```java
public static Percentage parse(String raw) {
  BigDecimal value = new BigDecimal(raw);
  return new Percentage(value);
}
```

팩터리가 유효하지 않은 객체를 만든 뒤 setter로 보정하게 해서는 안 됩니다. 객체가 공개되는 모든 경로가 같은 불변식을 지켜야 합니다.

현재 사용자, 저장된 상태나 외부 정책에 따라 달라지는 규칙은 값 객체 생성자에 넣지 않습니다. 예를 들어 “금액은 음수가 아니다”는 값 자체의 규칙이지만 “현재 사용자의 일일 한도를 넘지 않는다”는 정책 객체나 애플리케이션 서비스의 판단입니다.

## 클래스와 인터페이스의 책임

클래스는 상태와 구현을 함께 소유합니다. 인터페이스는 호출자가 기대하는 동작을 표현하고 실제 교체 가능성이 있는 경계에 둡니다.

```java
public interface ExchangeRateProvider {
  BigDecimal rate(Currency from, Currency to);
}
```

모든 클래스에 인터페이스를 붙이면 파일 수는 늘지만 계약은 선명해지지 않습니다. 외부 시스템, 시간, 파일 저장과 같은 경계 또는 여러 구현이 실제로 필요한 정책에 우선 사용합니다.

상속보다 합성을 기본 후보로 삼습니다. 상속은 하위 타입이 상위 타입의 모든 공개 계약을 지킬 수 있을 때 사용합니다. 구현 재사용만을 위해 상속하면 상위 상태와 수명에 강하게 결합됩니다.

## 닫힌 변형과 `sealed`

가능한 변형이 제한되고 각 변형이 서로 다른 데이터를 가질 때 sealed hierarchy가 유용합니다.

```java
public sealed interface JobCommand permits CreditJob, DebitJob {
  JobId id();
}

public record CreditJob(JobId id, long amount) implements JobCommand {}

public record DebitJob(JobId id, long amount) implements JobCommand {}
```

새 변형을 추가할 때 관련 처리 코드도 함께 검토하게 됩니다. 반대로 외부 플러그인이 자유롭게 구현해야 하는 SPI에는 닫힌 계층이 맞지 않습니다.

Java 17에서는 `instanceof` 패턴으로 안전하게 분기할 수 있습니다.

```java
if (command instanceof CreditJob credit) {
  return applyCredit(credit);
}
```

모든 분기를 긴 `if` 체인에 넣기보다 각 변형이 자신의 단순 검증을 담당하고, 상태 변경이 필요한 객체가 실제 적용을 담당하게 합니다.

## `enum`의 적절한 사용

가능한 이름이 고정되고 각 값이 추가 데이터를 갖지 않거나 같은 동작을 공유할 때 `enum`이 적합합니다.

```java
public enum JobStatus {
  ACCEPTED,
  REJECTED
}
```

새 값이 자주 추가되거나 값마다 다른 구조를 가져야 하면 sealed type이 더 명확할 수 있습니다. 외부 입력의 임의 문자열을 바로 `Enum.valueOf`에 전달하지 말고 대소문자와 오류 계약을 별도 경계에서 정합니다.

## 제네릭으로 읽기와 쓰기 계약 표현

제네릭은 캐스팅을 줄이는 문법보다 어떤 타입을 읽고 쓸 수 있는지 표현하는 장치입니다.

```java
static <T> void copy(List<? extends T> source, List<? super T> target) {
  target.addAll(source);
}
```

생산자에는 `? extends T`, 소비자에는 `? super T`를 고려할 수 있습니다. 그러나 와일드카드를 습관적으로 공개하면 호출부가 어려워집니다. 실제 변성이 필요한 API에만 사용합니다.

원시 타입과 무분별한 `@SuppressWarnings`는 타입 오류를 실행 시점으로 미룹니다. 경고를 억제해야 한다면 범위를 최소화하고 왜 안전한지 근거를 남깁니다.

## 값 객체 연산의 실패 계약

값 객체의 연산은 단위와 범위를 스스로 지킵니다.

```java
public Money add(Money other) {
  requireSameCurrency(other);
  return new Money(Math.addExact(minor, other.minor), currency);
}
```

다른 통화를 더하거나 범위를 넘은 결과를 조용히 보정하지 않습니다. 실패 뒤 기존 객체는 그대로 유효해야 합니다.

[값 객체 계약 실습](../../exercises/01-language-and-domain/02-value-object-contract/README.md)에서 생성 규칙, 동등성, 통화 일치, 정확한 덧셈과 뺄셈을 구현합니다.

## 공개 API 점검

타입을 공개하기 전에 다음을 확인합니다.

- 생성 가능한 모든 상태가 유효합니까?
- `null`, 빈 값과 경계값의 의미가 분명합니까?
- 가변 컬렉션이나 배열이 소유권 밖으로 새지 않습니까?
- `equals`와 `hashCode`가 같은 의미를 사용합니까?
- 실패가 예외인지 정상 결과인지 호출자가 구분할 수 있습니까?
- 인터페이스가 실제 교체 경계를 표현합니까?
- 새 변형이 생겼을 때 수정해야 할 지점이 드러납니까?

다음은 [컬렉션·Stream과 숫자 불변식](04-collections-streams-and-numeric-invariants.md)입니다.
