# 함수·배열·문자열: 문제를 작은 계약으로 나누기

코드가 길어졌다고 단순히 여러 파일로 옮기는 것만으로는 구조가 나아지지 않습니다. 먼저 책임을 나눠야 합니다. 좋은 함수는 무엇을 입력으로 받고 무엇을 반환하는지, 어떤 조건에서 실패하는지, 어떤 상태를 변경하는지를 짧게 설명할 수 있어야 합니다.

## 함수 계약부터 정하기

숫자로 이루어진 문자열을 `long` 값으로 변환하는 함수를 만든다고 가정합니다. 구현하기 전에 함수의 계약을 먼저 정합니다.

```c
int parse_long(const char *text, long *out_value);
```

```text
입력: NUL로 끝나는 문자열 text와 쓰기 가능한 long 객체를 가리키는 out_value
성공: 0을 반환하고 *out_value에 변환한 값을 저장
실패: -1을 반환하고 *out_value를 변경하지 않음
```

이 계약에서는 반환값으로 성공 여부를 알리고 출력 매개변수로 실제 결과를 전달합니다.

실패했을 때 출력값을 그대로 유지하면 호출자는 부분적으로 변경된 값을 별도로 해석하거나 복구할 필요가 없습니다.

## 값 전달과 호출자 상태

C에서 함수 인자는 값으로 전달됩니다.

```c
void set_zero(int value)
{
    value = 0;
}
```

이 함수가 변경하는 것은 함수 내부의 매개변수 `value`뿐입니다. 호출자가 전달한 원래 변수의 값은 바뀌지 않습니다.

호출자의 객체를 변경하려면 그 객체의 주소를 전달해야 합니다.

```c
void set_zero(int *value)
{
    *value = 0;
}
```

포인터를 받는 함수는 해당 포인터가 `NULL`일 수 있는지, 가리키는 객체가 함수 실행 중에도 유효한지, 그 객체를 변경해도 되는지를 계약으로 정해야 합니다.

포인터와 객체 수명은 [메모리·포인터·문자열](../02-c-language/02-memory-pointers-strings.md)에서 자세히 다룹니다.

## 함수마다 하나의 책임 맡기기

`number-report` 프로그램은 다음과 같이 나눌 수 있습니다.

```text
parse_long      문자열 하나를 검사하고 숫자로 변환
stats_add       숫자 하나를 통계 상태에 반영
print_report    완성된 통계 결과를 출력
print_usage     사용법을 stderr에 출력
main            전체 실행 순서와 종료 상태를 결정
```

`main` 하나에서 문자 검사, 숫자 변환, 통계 계산, 출력까지 모두 처리하면 기능 간 경계가 흐려지고 각 동작을 독립적으로 검사하기도 어려워집니다.

함수를 나누는 기준은 코드 길이가 아니라 **서로 다른 책임과 계약을 분리할 수 있는가**입니다.

## 함께 변하는 상태를 구조체로 묶기

여러 값이 하나의 상태를 구성한다면 구조체로 묶을 수 있습니다.

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

이 필드들은 서로 독립적이지 않으며 다음 관계를 함께 유지해야 합니다.

```text
count == even_count + odd_count
count == 0이면 minimum과 maximum을 사용하지 않는다
count > 0이면 minimum <= maximum
sum은 지금까지 처리한 모든 값의 합이다
```

이 조건들은 `struct statistics`가 유효한 상태인지 판단하는 기준입니다.

구조체는 여러 필드를 한곳에 모으는 문법에 그치지 않습니다. 함께 유효해야 하고 함께 변경되는 상태를 하나의 단위로 표현합니다.

## 배열과 길이

배열은 같은 타입의 원소를 연속된 공간에 저장하는 객체입니다.

```c
int values[4] = {10, 20, 30, 40};
size_t count = sizeof values / sizeof values[0];
```

위 식은 배열 전체의 크기를 원소 하나의 크기로 나누어 원소 개수를 구합니다.

하지만 배열을 함수 인자로 전달하면 배열 길이가 자동으로 함께 전달되지는 않습니다.

```c
long sum_values(const int *values, size_t count);
```

따라서 여러 원소를 처리하는 함수에는 일반적으로 첫 원소를 가리키는 포인터와 원소 개수를 함께 전달합니다.

경계 조건도 계약에 포함해야 합니다. 예를 들어 `count == 0`이면 `values`가 가리키는 메모리를 읽지 않는다고 정할 수 있습니다.

## 문자열은 NUL로 끝나는 문자 배열이다

C 문자열은 NUL 문자(`'\0'`)로 끝나는 문자 배열입니다.

```c
char word[] = "hello";
```

이 배열에는 실제로 여섯 바이트가 저장됩니다.

```text
'h' 'e' 'l' 'l' 'o' '\0'
```

C 문자열 함수는 일반적으로 `'\0'`을 만날 때까지 바이트를 읽습니다. 배열 안에 종료 문자가 없으면 배열 경계를 넘어 계속 읽을 수 있습니다.

따라서 문자열을 직접 구성할 때는 내용뿐 아니라 마지막 NUL 문자를 저장할 공간도 확보해야 합니다.

문자열 리터럴의 내용은 수정해서는 안 됩니다.

```c
const char *name = "Ada";
```

문자열 리터럴을 변경하려는 동작은 정의되지 않은 동작입니다. 읽기 전용 문자열을 다룰 때 `const char *`를 사용하면 함수나 변수의 의도를 타입에 드러낼 수 있습니다.

문자열의 길이와 문자열을 저장하는 버퍼의 용량도 구분해야 합니다.

```text
length      현재 저장된 바이트 수, NUL 제외
capacity    버퍼가 저장할 수 있는 전체 바이트 수, NUL 공간 포함
```

예를 들어 길이가 5인 `"hello"`를 저장하려면 최소 6바이트가 필요합니다.

## `const`로 변경 가능 여부 표현하기

다음 두 함수는 모두 포인터를 받지만 허용하는 동작이 다릅니다.

```c
size_t text_length(const char *text);
void uppercase_ascii(char *text);
```

`text_length`는 `text` 포인터를 통해 문자열 내용을 변경하지 않겠다는 의도를 타입으로 표현합니다.

반면 `uppercase_ascii`는 전달받은 문자 배열의 내용을 변경할 수 있습니다.

`const`가 객체의 소유권이나 수명을 관리해 주는 것은 아닙니다. 다만 함수 경계에서 해당 포인터를 통해 허용되는 동작을 제한하고 함수의 의도를 호출자에게 더 명확하게 전달합니다.

## 헤더와 구현 분리 미리 보기

여러 `.c` 파일에서 같은 공개 함수나 타입을 사용해야 한다면 선언을 헤더에 둡니다.

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

이 예제에서는 호출자가 직접 `struct statistics` 객체를 만들어 사용하므로 구조체의 내부 표현도 헤더에 공개합니다.

```c
struct statistics stats;
```

호출자가 내부 필드를 알 필요가 없다면 구조체 정의를 감추고 불투명 타입으로 설계할 수도 있습니다. 이러한 API 설계는 2부에서 다룹니다.

함수 구현은 `.c` 파일에 둡니다. 여러 `.c` 파일과 헤더가 각각 번역 단위를 이루고 최종 프로그램으로 연결되는 과정은 [C 프로그램 모델](../02-c-language/01-c-program-model.md)에서 자세히 다룹니다.

## 함수 단위로 테스트하기

책임을 작은 함수로 나누면 전체 프로그램을 실행하지 않고도 각 계약을 독립적으로 검사할 수 있습니다.

```c
long value = 999;

CHECK(parse_long("42", &value) == 0);
CHECK(value == 42);

value = 999;

CHECK(parse_long("42x", &value) == -1);
CHECK(value == 999);
```

첫 번째 검사는 정상 입력에서 반환값과 변환 결과를 확인합니다.

두 번째 검사는 잘못된 입력에서 실패를 반환하는지만 보는 것이 아니라, 계약대로 기존 출력값을 변경하지 않았는지도 확인합니다.

함수를 테스트할 때는 성공 결과뿐 아니라 **실패한 뒤 어떤 상태가 남는지도 계약의 일부로 검사해야 합니다.**

## 실습

`number-report`의 단일 파일 구현을 다음 함수로 분리합니다.

- `parse_long`
- `statistics_init`
- `statistics_add`
- `statistics_print`
- `print_usage`

그런 다음 각 함수가 실패했을 때 변경할 수 있는 상태의 범위를 문서화합니다. 최종 자동 검증은 [연습문제 README](../../exercises/01-foundations/01-number-report/README.md)를 따릅니다.
