# 함수·배열·텍스트: 문제를 작은 계약으로 나누기

코드가 길어질 때 필요한 것은 문장을 다른 파일로 옮기는 일이 아니라 책임을 나누는 일입니다. 좋은 함수는 입력, 성공 결과, 실패와 변경하는 상태를 짧게 설명할 수 있습니다.

## 함수 계약부터 적기

숫자 문자열을 변환하는 함수의 계약을 먼저 정합니다.

```c
int parse_long(const char *text, long *out_value);
```

```text
입력: NUL 종료 문자열 text, 쓰기 가능한 out_value
성공: 0을 반환하고 *out_value를 설정
실패: -1을 반환하고 *out_value를 변경하지 않음
```

반환값은 성공 여부, 출력 매개변수는 결과를 전달합니다. 실패 시 출력값을 보존하면 호출자가 부분적으로 갱신된 상태를 해석하지 않아도 됩니다.

## 값 전달과 호출자의 상태

C 함수 인자는 값으로 전달됩니다.

```c
void set_zero(int value)
{
    value = 0;
}
```

이 함수는 호출자의 변수를 바꾸지 않습니다. 호출자의 객체를 바꾸려면 주소를 전달합니다.

```c
void set_zero(int *value)
{
    *value = 0;
}
```

포인터를 사용하기 전에 null 가능성과 대상의 수명을 계약으로 정해야 합니다. 포인터 자체의 자세한 모델은 [메모리·포인터 문서](../02-c-language/02-memory-pointers-strings.md)에서 다룹니다.

## 함수가 한 가지 책임을 갖게 하기

`number-report`를 다음 책임으로 나눌 수 있습니다.

```text
parse_long       문자열 하나를 검증하고 숫자로 변환
stats_add        숫자 하나를 통계 상태에 반영
print_report     완성된 상태를 출력
print_usage      사용법을 stderr에 출력
main             전체 순서와 종료 상태를 결정
```

`main` 안에서 문자 검사, 숫자 계산과 출력 형식을 모두 처리하면 테스트할 경계가 흐려집니다.

## 구조체로 함께 변하는 값 묶기

```c
struct statistics
{
    size_t count;
    long minimum;
    long maximum;
    long sum;
    size_t even_count;
    size_t odd_count;
};
```

서로 같은 불변식을 구성하는 값은 구조체로 묶을 수 있습니다.

```text
count == even_count + odd_count
count == 0이면 minimum과 maximum을 읽지 않는다
count > 0이면 minimum <= maximum
sum은 처리한 모든 값의 합
```

구조체는 단지 필드 묶음이 아니라 함께 유효하거나 함께 갱신되는 상태의 경계입니다.

## 배열과 길이

```c
int values[4] = {10, 20, 30, 40};
size_t count = sizeof values / sizeof values[0];
```

배열은 고정된 개수의 원소를 연속해서 포함하는 객체입니다. 함수에 전달될 때 길이가 자동으로 함께 전달되지 않습니다.

```c
long sum_values(const int *values, size_t count);
```

포인터와 길이를 함께 전달하는 것이 기본 계약입니다. `count`가 0이면 `values`를 읽지 않는다는 규칙도 명시합니다.

## 문자열은 NUL로 끝나는 문자 배열

```c
char word[] = "hello";
```

실제 배열에는 여섯 바이트가 있습니다.

```text
'h' 'e' 'l' 'l' 'o' '\0'
```

문자열 함수는 `\0`을 만날 때까지 읽습니다. 종료 문자가 없으면 객체 범위를 넘어 읽을 수 있습니다. 따라서 문자열을 만드는 함수는 공간에 종료 문자 한 바이트를 포함해야 합니다.

문자열 리터럴을 수정하지 않습니다.

```c
const char *name = "Ada";
```

문자열의 길이와 버퍼의 용량은 다른 값입니다.

```text
length   현재 문자 수, NUL 제외
capacity 저장 가능한 전체 바이트 수, NUL 포함
```

## const는 변경 권한을 드러낸다

```c
size_t text_length(const char *text);
void uppercase_ascii(char *text);
```

첫 함수는 문자열 내용을 바꾸지 않겠다는 계약을 타입으로 표현합니다. `const`는 객체의 전체 수명과 소유권을 자동으로 해결하지 않지만, 함수 경계에서 허용된 동작을 좁힙니다.

## 헤더와 구현 분리의 예고

공개 함수 선언과 구조체가 여러 `.c` 파일에서 필요하면 헤더에 둡니다.

```c
#ifndef STATISTICS_H
#define STATISTICS_H

#include <stddef.h>

struct statistics
{
    size_t count;
    long minimum;
    long maximum;
    long sum;
    size_t even_count;
    size_t odd_count;
};

int statistics_add(struct statistics *stats, long value);

#endif
```

호출자가 스택에 `struct statistics` 객체를 만들므로 이 예에서는 구조체 표현도 공개합니다. 내부 표현을 숨기는 불투명 타입은 Part 2의 API 설계 문서에서 다룹니다. 함수 본문은 `.c` 파일에 두며, 자세한 번역 단위와 링크 모델은 [C 프로그램 모델](../02-c-language/01-c-program-model.md)에서 다룹니다.

## 함수 테스트하기

작은 함수는 `main` 전체를 실행하지 않고 검사할 수 있습니다.

```c
long value = 999;

CHECK(parse_long("42", &value) == 0);
CHECK(value == 42);

value = 999;
CHECK(parse_long("42x", &value) == -1);
CHECK(value == 999);
```

정상 결과와 실패 뒤 상태를 함께 검사합니다.

## 실습

`number-report`의 한 파일 구현을 다음 함수로 분리합니다.

- `parse_long`
- `statistics_init`
- `statistics_add`
- `statistics_print`
- `print_usage`

그 뒤 각 함수의 실패 시 변경 범위를 문서화합니다. 최종 자동 검증은 [연습문제 README](../../exercises/01-foundations/01-number-report/README.md)를 따릅니다.
