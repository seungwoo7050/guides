# 컬렉션·Stream과 숫자 불변식

컬렉션과 숫자 타입은 편한 메서드가 많은 구현보다 데이터 계약에 따라 선택합니다. 순서, 중복, 키의 안정성, 단위와 반올림이 빠지면 작은 예제는 통과해도 경계값과 동시 처리에서 결과가 달라집니다.

## 조회와 변경 방식에 맞는 컬렉션

| 필요한 계약 | 기본 후보 |
|---|---|
| 순서를 보존하고 중복 허용 | `List` |
| 중복 금지와 포함 여부 확인 | `Set` |
| 키마다 하나의 값 조회 | `Map` |
| 앞뒤 삽입·제거 | `Deque` |
| 정렬된 키 또는 값 | `TreeMap`, `TreeSet` 또는 명시적인 정렬 결과 |

`HashMap`과 `HashSet`의 순회 순서를 API 응답이나 테스트 계약으로 사용하지 않습니다. 정렬이 필요하면 동점일 때의 두 번째 기준까지 정합니다.

```java
Comparator<JobReceipt> order =
    Comparator.comparing(JobReceipt::completedAt)
        .thenComparing(receipt -> receipt.id().value());
```

키로 사용하는 객체는 Map에 들어간 뒤 동등성과 hash code가 바뀌지 않아야 합니다. 가변 엔터티 전체보다 불변 식별자를 키로 사용하는 편이 안전합니다.

## 소유권과 불변 뷰

컬렉션을 생성자에서 그대로 보관하면 호출자가 나중에 내용을 바꿀 수 있습니다.

```java
public final class QueuePlan {
  private final List<JobId> jobs;

  public QueuePlan(List<JobId> jobs) {
    this.jobs = List.copyOf(jobs);
  }

  public List<JobId> jobs() {
    return jobs;
  }
}
```

`Collections.unmodifiableList`는 원본이 바뀌면 결과도 바뀌는 읽기 전용 뷰일 수 있습니다. 독립된 스냅샷이 필요하면 `List.copyOf`나 새 컬렉션을 사용합니다.

반복 중 컬렉션을 직접 수정하면 `ConcurrentModificationException`이 나거나 일부 원소를 건너뛸 수 있습니다. 제거 조건이 명확하면 `removeIf`, 새 결과가 필요하면 별도 컬렉션을 사용합니다.

## Stream을 사용할 범위

Stream은 부수 효과가 없는 짧은 변환에 잘 맞습니다.

```java
List<String> enabledNames =
    entries.stream()
        .filter(Entry::enabled)
        .map(Entry::name)
        .sorted()
        .toList();
```

다음 조건에서는 명시적인 반복문이 더 읽기 쉽습니다.

- 중간에 여러 이유로 종료합니다.
- checked exception과 복구가 섞입니다.
- 저장소 쓰기나 네트워크 호출이 있습니다.
- 여러 누적 상태를 함께 갱신합니다.
- 디버깅할 중간 단계가 많습니다.

```java
items.stream().forEach(item -> repository.save(transform(item)));
```

위 코드는 저장 실패 뒤 어디까지 반영되었는지, 트랜잭션과 재시도 경계가 무엇인지 숨깁니다.

`parallelStream()`은 공용 `ForkJoinPool`을 사용합니다. 요청 스레드, 블로킹 I/O나 트랜잭션 문맥과 섞으면 작업 수, 큐와 종료를 통제하기 어렵습니다. 병렬 처리가 필요하면 [동시성·잠금과 실행기](../02-runtime-and-concurrency/01-concurrency-locking-and-executors.md)의 명시적인 실행기 계약을 먼저 정합니다.

## `Optional`의 경계

`Optional<T>`는 “결과가 없을 수 있음”을 반환 타입에서 드러냅니다.

```java
Optional<JobReceipt> find(JobId id)
```

다음 용도에는 보통 적합하지 않습니다.

- 필드
- 메서드 인자
- 컬렉션 원소
- 직렬화 DTO의 무분별한 구성 요소

없음이 오류인지 정상 분기인지 먼저 정합니다. 오류라면 의미 있는 예외나 결과 타입이 필요하고, 빈 Optional로 모든 실패를 숨기지 않습니다.

## 정수 단위와 오버플로

소수점이 필요 없는 최소 단위는 `long`으로 표현할 수 있습니다. 연산 범위를 벗어나면 조용히 값이 돌아가므로 정확한 연산을 사용합니다.

```java
long total = Math.addExact(first, second);
long remaining = Math.subtractExact(balance, amount);
long scaled = Math.multiplyExact(quantity, unitPrice);
```

최종 결과만 범위 안이어도 중간 연산이 먼저 넘칠 수 있습니다. 연산 순서를 바꾸기 전에 수학적으로 동등한지와 중간 범위를 함께 확인합니다.

업무상 음수가 허용되지 않는다면 정확한 연산 뒤 생성자나 상태 변경 메서드가 그 규칙을 거부합니다. 오버플로와 업무상 범위 위반은 서로 다른 실패입니다.

## `BigDecimal`, scale과 반올림

소수 비율이 필요하면 문자열이나 정수에서 `BigDecimal`을 만듭니다.

```java
BigDecimal amount = new BigDecimal("1250.00");
BigDecimal rate = new BigDecimal("0.075");
BigDecimal fee = amount.multiply(rate).setScale(2, RoundingMode.HALF_UP);
```

`new BigDecimal(0.1)`은 이진 부동소수점의 근삿값을 그대로 가져옵니다. `BigDecimal.valueOf(double)`은 문자열 변환을 거치지만, 처음부터 십진 문자열이나 정수 단위를 사용하는 편이 계약이 분명합니다.

`scale`과 `RoundingMode`는 화면 장식이 아니라 계산 계약입니다. 나눗셈은 끝나지 않는 소수가 될 수 있으므로 자릿수와 반올림 없이 호출하지 않습니다.

숫자 값만 비교하면 `compareTo`, scale까지 값의 일부라면 `equals`를 사용합니다. 이 선택은 값 객체의 동등성과 테스트에 일관되게 반영합니다.

## 컬렉션과 숫자 검증

결과 하나만 보지 말고 보존되어야 하는 관계도 확인합니다.

```text
처리 전 합계
= 처리 후 합계 + 외부로 이동한 합계
```

다음 경계값을 포함합니다.

- 빈 컬렉션
- 원소 하나
- 중복 키
- 같은 정렬 값
- `Long.MAX_VALUE` 근처
- 0과 음수 경계
- 나누어떨어지지 않는 소수 계산
- 서로 다른 단위나 통화

[값 객체 계약 실습](../../exercises/01-language-and-domain/02-value-object-contract/README.md)에서 정수 최소 단위와 통화 불변식을 확인합니다.

다음은 [오류·검증·시간과 식별자](05-errors-validation-time-and-identifiers.md)입니다.
