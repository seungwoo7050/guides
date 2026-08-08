# Java 언어 기초

이 장은 뒤의 설계 문서를 읽고 작은 프로그램을 직접 만들기 위한 언어 최소선입니다. Java 문법 사전처럼 모든 키워드를 나열하지 않고 값이 이동하고 상태가 바뀌며 실패가 전달되는 방식을 중심으로 설명합니다.

## 값의 종류와 초기화

Java의 값은 크게 기본형과 참조형으로 나뉩니다.

| 종류 | 예 | 변수에 들어 있는 것 |
|---|---|---|
| 기본형 | `boolean`, `char`, `int`, `long`, `double` | 실제 값 |
| 참조형 | `String`, 배열, 클래스, 인터페이스 | 객체를 가리키는 참조 |

```java
int retryCount = 3;
long fileSize = 4_294_967_296L;
double ratio = 0.75;
boolean enabled = true;
```

지역 변수는 읽기 전에 직접 초기화해야 합니다. 필드는 자료형의 기본값을 갖지만 생성자가 의도한 상태를 명시하면 누락을 더 일찍 발견할 수 있습니다.

정수 나눗셈은 소수 부분을 버립니다.

```java
int truncated = 5 / 2;        // 2
double precise = 5.0 / 2.0;  // 2.5
```

정수 오버플로는 기본적으로 예외를 내지 않습니다. 범위 초과가 잘못된 상태라면 `Math.addExact`, `Math.subtractExact`, `Math.multiplyExact`를 사용합니다.

## 메서드는 모든 인자를 값으로 받습니다

기본형 값도 객체 참조도 복사되어 전달됩니다.

```java
static void replaceName(String name) {
  name = "Lee";
}

String name = "Kim";
replaceName(name);
System.out.println(name); // Kim
```

참조의 복사본을 다른 객체로 바꿔도 호출자의 변수는 바뀌지 않습니다. 그러나 두 참조가 같은 가변 객체를 가리키면 그 객체의 내용은 바뀔 수 있습니다.

```java
static void addItem(List<String> items) {
  items.add("note");
}
```

입력을 보존해야 한다면 새 컬렉션을 반환합니다.

```java
static List<String> withItem(List<String> items, String item) {
  List<String> result = new ArrayList<>(items);
  result.add(item);
  return List.copyOf(result);
}
```

## 문자열, `null`과 동등성

`String`은 참조형이지만 생성 뒤 내용이 바뀌지 않는 불변 객체입니다.

```java
String first = "board";
String second = new String("board");

System.out.println(first == second);      // false
System.out.println(first.equals(second)); // true
```

`==`는 같은 객체를 가리키는지 확인하고 `equals`는 값의 동등성을 확인합니다. 문자열과 값 객체는 내용 비교에 `equals`를 사용합니다.

`null`은 참조가 어떤 객체도 가리키지 않는 상태입니다. 필요한 값이라면 경계에서 즉시 거부합니다.

```java
static int titleLength(String title) {
  Objects.requireNonNull(title, "title");
  return title.length();
}
```

없음이 정상 결과라면 빈 문자열, 임의의 숫자나 예외를 섞지 말고 호출자가 구분할 수 있는 반환 계약을 선택합니다. `Optional`은 반환값의 부재를 표현할 수 있지만 필드와 메서드 인자에 습관적으로 사용하지 않습니다.

## 조건과 반복

조건문은 상태를 분류하고 반복문은 같은 규칙을 여러 값에 적용합니다.

```java
static String accessLabel(boolean active, int roleLevel) {
  if (!active) {
    return "비활성";
  }
  return roleLevel >= 2 ? "편집 가능" : "읽기 전용";
}
```

가능한 값이 명확하면 `switch` 표현식이 누락을 줄입니다.

```java
static int retryLimit(String mode) {
  return switch (mode) {
    case "interactive" -> 1;
    case "batch" -> 3;
    default -> throw new IllegalArgumentException("알 수 없는 모드: " + mode);
  };
}
```

컬렉션의 원소만 필요하면 향상된 `for`문을 사용합니다.

```java
for (String item : items) {
  System.out.println(item);
}
```

인덱스 자체가 계약일 때만 전통적인 `for`문을 사용하고, 반복 경계가 `< length`인지 확인해 off-by-one 오류를 막습니다.

## 메서드로 문제 나누기

한 메서드가 입력 해석, 계산, 상태 변경과 출력을 모두 맡으면 실패 위치와 테스트 경계가 흐려집니다.

```text
문자열 입력 해석
→ 유효한 값 만들기
→ 순수 계산
→ 결과 표현
```

계산 메서드는 가능한 한 값을 반환하고, stdout이나 파일 쓰기는 바깥 경계에서 수행합니다. 실패할 수 있는 변환은 성공 결과와 실패 진단이 섞이지 않게 먼저 끝냅니다.

[첫 명령행 프로그램 실습](../../exercises/01-language-and-domain/01-first-program/README.md)은 다음 분리를 요구합니다.

- 인자 존재 여부 확인
- 문자열을 정수로 변환
- 합계·최솟값·최댓값·평균 계산
- stdout과 stderr 분리
- 실패 종료 상태 반환

## 배열과 컬렉션

배열은 길이가 고정되어 있고 인덱스로 접근합니다.

```java
String[] roles = {"viewer", "editor", "owner"};
System.out.println(roles[1]);
```

원소 수가 변하는 목록은 `List`, 중복이 없어야 하는 값은 `Set`, 키로 찾는 값은 `Map`을 기본 후보로 삼습니다.

```java
List<String> names = new ArrayList<>();
names.add("Kim");

Set<String> permissions = new HashSet<>();
permissions.add("board:read");

Map<String, Integer> versions = new HashMap<>();
versions.put("board-a", 3);
```

구현체보다 필요한 동작을 드러내기 위해 변수와 인자는 보통 `List`, `Set`, `Map` 같은 인터페이스 타입으로 선언합니다. 구체적인 선택 기준은 [컬렉션·Stream과 숫자 불변식](04-collections-streams-and-numeric-invariants.md)에서 다룹니다.

## 클래스, 생성자와 캡슐화

클래스는 상태와 그 상태를 지키는 동작을 함께 둡니다.

```java
public final class Counter {
  private final int minimum;
  private int value;

  public Counter(int minimum, int initialValue) {
    if (initialValue < minimum) {
      throw new IllegalArgumentException("initialValue가 minimum보다 작습니다.");
    }
    this.minimum = minimum;
    this.value = initialValue;
  }

  public int value() {
    return value;
  }

  public void decrease() {
    if (value == minimum) {
      throw new IllegalStateException("최솟값보다 줄일 수 없습니다.");
    }
    value -= 1;
  }
}
```

필드는 기본적으로 `private`로 두고 필요한 동작만 공개합니다. 모든 필드에 setter를 만드는 대신 상태 변경의 이름과 거부 조건을 메서드에 담습니다.

`final` 필드는 생성 뒤 다른 참조나 값으로 교체되지 않습니다. 참조가 `final`이어도 가리키는 가변 객체의 내용은 바뀔 수 있으므로 불변성과 같은 뜻은 아닙니다.

`static` 멤버는 특정 객체가 아니라 클래스에 속합니다. 진입점과 상태 없는 유틸리티에는 알맞지만 가변 전역 상태를 두면 테스트와 동시 실행이 어려워집니다.

## 패키지와 접근 범위

패키지는 이름 충돌을 피하고 접근 경계를 만듭니다.

```java
package dev.guides.foundations;

import java.util.List;
```

접근 범위는 `public`, `protected`, 같은 패키지에 보이는 생략 표기, 같은 클래스에만 보이는 `private`로 나뉩니다. 다른 패키지가 실제로 사용해야 하는 타입과 메서드만 `public`으로 엽니다.

## 예외와 자원 수명

잘못된 인자는 `IllegalArgumentException`, 현재 객체 상태에서 실행할 수 없는 동작은 `IllegalStateException`처럼 실패의 성격을 드러냅니다. I/O처럼 호출자가 처리 여부를 선택해야 하는 실패는 checked exception을 만날 수 있습니다.

원래 원인을 보존해 번역합니다.

```java
try {
  return Files.readString(path);
} catch (IOException error) {
  throw new IllegalStateException("설정 파일을 읽지 못했습니다: " + path, error);
}
```

파일, 소켓, Stream과 실행기처럼 닫아야 하는 자원은 수명 주기를 명시합니다. `AutoCloseable` 자원은 try-with-resources로 관리합니다.

```java
static List<String> readLines(Path path) throws IOException {
  try (BufferedReader reader = Files.newBufferedReader(path)) {
    return reader.lines().toList();
  }
}
```

성공, 예외와 조기 반환에서 같은 정리 규칙이 적용되어야 합니다.

## 완료 기준

- 기본형 값과 객체 참조의 복사를 구분합니다.
- 문자열의 `==`와 `equals` 차이를 설명합니다.
- 입력 해석, 계산과 출력을 별도 메서드로 나눕니다.
- 배열, `List`, `Set`, `Map`의 기본 목적을 구분합니다.
- 생성자가 유효한 객체를 만들고 상태 변경 메서드가 규칙을 지키게 합니다.
- 예외의 원인을 보존하고 닫을 자원의 수명을 명시합니다.

다음은 [도메인 타입과 계약](03-domain-types-records-and-sealed-types.md)입니다.
