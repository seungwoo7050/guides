# 함수·배열·문자열: 문제를 작은 계약으로 나누기

코드가 길어졌을 때 필요한 것은 단순히 코드를 여러 파일로 옮기는 일이 아니라 책임을 나누는 일입니다. 좋은 함수는 무엇을 입력으로 받고, 무엇을 반환하며, 실패할 수 있는 조건과 변경하는 상태가 무엇인지 짧게 설명할 수 있어야 합니다.

## 함수 계약부터 정하기

숫자로 이루어진 문자열을 `long` 값으로 변환하는 함수를 만든다고 가정합니다. 구현에 앞서 먼저 함수의 계약을 정합니다.

```c
int parse_long(const char *text, long *out_value);
```

```text
입력: NUL로 끝나는 문자열 text와 값을 쓸 수 있는 out_value
성공: 0을 반환하고 *out_value에 변환한 값을 저장
실패: -1을 반환하고 *out_value는 변경하지 않음
```

여기서는 반환값으로 성공 여부를 알리고 출력 매개변수를 통해 실제 결과를 전달합니다.

실패했을 때 출력값을 그대로 유지하도록 계약하면 호출자는 실패 이후에 부분적으로 변경된 값을 따로 해석할 필요가 없습니다.

## 값 전달과 호출자의 상태

C에서 함수의 인자는 값으로 전달됩니다.

```c
void set_zero(int value)
{
    value = 0;
}
```

이 함수가 변경하는 것은 매개변수 `value`뿐입니다. 호출자가 넘긴 원래 변수의 값은 바뀌지 않습니다.

호출자의 객체를 변경하려면 그 객체의 주소를 전달해야 합니다.

```c
void set_zero(int *value)
{
    *value = 0;
}
```

포인터를 받는 함수라면 해당 포인터가 `NULL`일 수 있는지, 가리키는 객체가 호출 중에 유효한지, 함수를 통해 그 객체를 변경해도 되는지를 계약으로 정해야 합니다.

포인터와 객체 수명에 대한 자세한 내용은 [메모리·포인터 문서](../02-c-language/02-memory-pointers-strings.md)에서 다룹니다.

## 함수마다 하나의 책임 맡기기

`number-report` 프로그램을 다음과 같이 나눌 수 있습니다.

```text
parse_long      문자열 하나를 검사하고 숫자로 변환
stats_add       숫자 하나를 통계 상태에 반영
print_report    완성된 통계 결과를 출력
print_usage     사용법을 stderr에 출력
main            전체 실행 순서와 종료 상태를 결정
```

`main` 하나에서 문자 검사, 숫자 변환, 통계 계산과 출력까지 모두 처리하면 각 기능의 경계가 흐려지고 개별 동작을 따로 검사하기도 어려워집니다.

함수를 나누는 기준은 코드의 길이가 아니라 **서로 다른 책임과 계약을 분리할 수 있는가**입니다.

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

이 필드들은 서로 독립적인 값이 아니라 다음과 같은 관계를 함께 유지합니다.

```text
count == even_count + odd_count
count == 0이면 minimum과 maximum을 사용하지 않는다
count > 0이면 minimum <= maximum
sum은 지금까지 처리한 모든 값의 합이다
```

이러한 조건은 `struct statistics`가 유효한 상태인지 판단하는 기준이 됩니다.

구조체는 단순히 여러 필드를 한곳에 모아 두는 문법이 아닙니다. 함께 유효해야 하고 함께 갱신되는 상태를 하나의 단위로 표현하는 방법입니다.

## 배열과 길이

배열은 같은 타입의 원소를 연속해서 저장하는 객체입니다.

```c
int values[4] = {10, 20, 30, 40};
size_t count = sizeof values / sizeof values[0];
```

위 식은 현재 배열 전체의 크기를 원소 하나의 크기로 나누어 원소 개수를 구합니다.

하지만 배열을 함수에 전달하면 배열의 길이가 자동으로 함께 전달되지는 않습니다.

```c
long sum_values(const int *values, size_t count);
```

따라서 여러 원소를 처리하는 함수에서는 보통 첫 원소를 가리키는 포인터와 원소 개수를 함께 전달합니다.

이때 경계 조건도 계약에 포함해야 합니다. 예를 들어 `count == 0`일 때는 `values`가 가리키는 값을 읽지 않는다고 정할 수 있습니다.

## 문자열은 NUL로 끝나는 문자 배열이다

C 문자열은 NUL 문자(`'\0'`)로 끝나는 문자 배열입니다.

```c
char word[] = "hello";
```

이 배열은 실제로 여섯 개의 문자를 저장합니다.

```text
'h' 'e' 'l' 'l' 'o' '\0'
```

C의 문자열 함수는 일반적으로 `'\0'`을 만날 때까지 문자를 읽습니다. 배열 안에 종료 문자가 없다면 문자열 함수가 배열의 범위를 넘어 계속 읽게 될 수 있습니다.

따라서 문자열을 직접 만드는 코드에서는 실제 문자뿐 아니라 마지막 NUL 문자를 저장할 공간까지 확보해야 합니다.

문자열 리터럴의 내용은 수정해서는 안 됩니다.

```c
const char *name = "Ada";
```

문자열 리터럴을 변경하려는 동작은 정의되지 않은 동작이 됩니다. 읽기 전용 문자열을 다룰 때 `const char *`를 사용하면 함수나 변수의 사용 의도를 타입에도 드러낼 수 있습니다.

문자열의 길이와 문자열을 저장하는 버퍼의 용량도 구분해야 합니다.

```text
length      현재 저장된 문자 수, NUL 제외
capacity    버퍼가 저장할 수 있는 전체 바이트 수, NUL 공간 포함
```

예를 들어 길이가 5인 `"hello"`를 저장하려면 최소 6바이트의 공간이 필요합니다.

## `const`로 변경 가능 여부 표현하기

다음 두 함수는 포인터를 받지만 허용하는 동작이 다릅니다.

```c
size_t text_length(const char *text);
void uppercase_ascii(char *text);
```

`text_length`는 `text`를 통해 문자열 내용을 변경하지 않겠다는 뜻을 타입으로 표현합니다.

반면 `uppercase_ascii`는 전달받은 문자 배열의 내용을 변경할 수 있습니다.

`const`가 객체의 소유권이나 전체 수명을 관리해 주는 것은 아닙니다. 다만 함수 경계에서 해당 포인터를 통해 허용되는 동작을 제한하고 호출자에게 함수의 의도를 더 명확하게 전달합니다.

## 헤더와 구현 분리 미리 보기

여러 `.c` 파일에서 같은 공개 함수나 타입을 사용해야 한다면 그 선언을 헤더에 둡니다.

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

이 예에서는 호출자가 직접 `struct statistics` 객체를 만들어 사용하므로 구조체의 내부 표현도 헤더에 공개되어 있습니다.

```c
struct statistics stats;
```

반대로 호출자가 내부 필드를 알 필요가 없다면 구조체의 정의를 감추고 불투명 타입으로 설계할 수도 있습니다. 이러한 API 설계는 Part 2에서 다룹니다.

함수의 구현은 `.c` 파일에 둡니다. 여러 `.c` 파일과 헤더가 어떻게 각각의 번역 단위를 구성하고 최종 프로그램으로 연결되는지는 [C 프로그램의 구성과 빌드](../02-c-language/01-c-program-model.md)에서 자세히 다룹니다.

## 함수 단위로 테스트하기

작은 함수로 책임을 나누면 전체 프로그램을 실행하지 않고도 각 계약을 따로 검사할 수 있습니다.

```c
long value = 999;

CHECK(parse_long("42", &value) == 0);
CHECK(value == 42);

value = 999;

CHECK(parse_long("42x", &value) == -1);
CHECK(value == 999);
```

첫 번째 검사는 정상 입력에서 성공 여부와 결과값을 확인합니다.

두 번째 검사는 잘못된 입력에서 실패를 반환하는지만 확인하는 것이 아니라, 계약대로 기존 출력값을 변경하지 않았는지도 함께 확인합니다.

함수를 테스트할 때는 성공했을 때의 결과뿐 아니라 **실패한 뒤 어떤 상태가 남는지도 계약의 일부로 검사해야 합니다.**

## 실습

`number-report`의 한 파일 구현을 다음 함수로 분리합니다.

- `parse_long`
- `statistics_init`
- `statistics_add`
- `statistics_print`
- `print_usage`

그 뒤 각 함수의 실패 시 변경 범위를 문서화합니다. 최종 자동 검증은 [연습문제 README](../../exercises/01-foundations/01-number-report/README.md)를 따릅니다.
