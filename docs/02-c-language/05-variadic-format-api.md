# 가변 인자와 포맷 API: 숨은 타입 계약 다루기

가변 인자 함수는 호출마다 인자의 수와 타입이 달라질 수 있습니다. 편리하지만 `...` 뒤에는 타입과 개수를 설명하는 메타데이터가 자동으로 따라오지 않습니다. 함수는 개수, 종결 표시, 포맷 문자열 같은 별도 계약에 의존해 다음 인자를 어떤 타입으로 읽을지 결정합니다.

이 장의 목표는 `printf` 전체를 복제하는 것이 아닙니다. **타입 정보가 사라지는 API에서 계약·상태·실패를 어떻게 통제하는지**를 작은 포맷터로 확인합니다.

## 고정 매개변수와 `...`

```c
int log_values(const char *label, size_t count, ...);
```

`label`과 `count`는 고정 매개변수이고 `...` 뒤가 가변 인자입니다. 함수 본문에서는 가변 인자에 이름으로 접근할 수 없습니다. `<stdarg.h>`의 인터페이스로 순서대로 읽습니다.

가변 인자 함수에는 `...` 앞에 최소 하나의 고정 매개변수가 있어야 합니다. `va_start`가 마지막 고정 매개변수를 기준으로 순회를 시작하기 때문입니다.

## 핵심 인터페이스와 생명주기

```c
#include <stdarg.h>

int sum_ints(size_t count, ...)
{
    va_list arguments;
    int total = 0;

    va_start(arguments, count);
    for (size_t index = 0; index < count; index++)
    {
        total += va_arg(arguments, int);
    }
    va_end(arguments);
    return total;
}
```

- `va_list`: 현재 읽기 위치를 포함한 순회 상태입니다.
- `va_start(list, last_fixed)`: 첫 가변 인자를 읽을 준비를 합니다.
- `va_arg(list, type)`: 다음 값을 `type`으로 읽고 순회 상태를 전진시킵니다.
- `va_end(list)`: 시작하거나 복사한 순회를 끝냅니다.
- `va_copy(destination, source)`: 독립적으로 순회할 복사본을 만듭니다.

`va_start` 또는 `va_copy`에 성공한 각 목록에는 대응하는 `va_end`가 필요합니다. 중간 오류 경로도 예외가 아닙니다.

`va_list`의 실제 표현은 플랫폼에 따라 포인터, 배열, 구조체 또는 더 복잡한 상태일 수 있습니다. 단순 대입이나 `memcpy`로 복사하지 않습니다.

## 타입 메타데이터는 없습니다

다음 호출은 컴파일되더라도 함수 계약을 위반합니다.

```c
sum_ints(3, 10, 20);      /* 약속한 개수보다 인자가 적음 */
sum_ints(2, 10, 2.5);     /* 둘째 값은 int가 아님 */
```

`va_arg`는 “다음 인자가 실제로 이 타입인가?”를 검사하지 않습니다. 실제 전달 타입과 호환되지 않는 타입으로 읽으면 정의되지 않은 동작이 발생할 수 있습니다. 함수 내부에서 일반적인 런타임 검사로 복구할 수도 없습니다. 이미 타입 정보가 사라졌기 때문입니다.

따라서 다음 둘은 구분해야 합니다.

```text
고정 인자 검증       NULL, capacity, 포맷 문법처럼 함수가 관찰할 수 있음
가변 인자 타입 오류  호출자 계약 위반이며 일반적으로 함수가 감지할 수 없음
```

잘못된 가변 인자 타입을 일부러 실행하는 테스트는 올바른 오류 테스트가 아니라 UB 실행이 될 수 있습니다.

## 기본 인자 승격

가변 인자로 전달될 때 일부 타입은 승격됩니다.

### 작은 정수형

`char`, `signed char`, `unsigned char`, `short`, `unsigned short`는 정수 승격을 거칩니다. 일반적인 환경에서는 `int` 또는 `unsigned int`로 전달됩니다.

```c
char letter = 'A';
consume(letter);

/* 수신 측 */
int value = va_arg(arguments, int);
```

`va_arg(arguments, char)`로 읽으면 안 됩니다.

### 부동소수점형

`float`는 `double`로 승격됩니다.

```c
float ratio = 1.5f;
consume(ratio);

/* 수신 측 */
double value = va_arg(arguments, double);
```

### 배열과 함수

일반 함수 호출과 마찬가지로 배열 표현식은 포인터로, 함수 지정자는 함수 포인터로 변환됩니다. 포맷 지정자는 승격과 변환이 끝난 **실제 전달 타입**을 기준으로 `va_arg` 타입을 정해야 합니다.

## 인자 경계를 알리는 세 가지 방법

함수는 어디까지 읽어야 하는지 별도 규칙이 필요합니다.

### 개수 전달

```c
int sum_ints(size_t count, ...);
```

간단하지만 호출자가 개수와 실제 인자를 정확히 맞춰야 합니다.

### 종결 표시

```c
const char *first_nonempty(const char *first, ...);
```

마지막에 `(const char *)NULL` 같은 sentinel을 넘겨 끝을 표시할 수 있습니다. 정수 상수 `0`이 어떤 타입으로 전달되는지와 포인터 sentinel을 혼동하지 않도록 계약을 명확히 합니다.

### 포맷 문자열

```c
int diagnostic_format(
    char *buffer,
    size_t capacity,
    const char *format,
    ...
);
```

포맷 문자열이 이후 인자의 수와 타입을 설명합니다.

```text
%s   const char *
%d   int
%%   인자를 소비하지 않고 '%' 출력
```

이 문자열은 단순 출력 데이터가 아니라 **런타임 타입 명세**입니다. 포맷과 실제 인자가 일치해야 합니다.

## 제한된 포맷 문법부터 시작합니다

교육용 API의 범위를 작게 고정합니다.

```text
일반 문자  그대로 출력
%%         '%' 하나 출력
%s         문자열
%d         부호 있는 10진수 정수
```

다음 입력의 정책도 미리 정합니다.

- 문자열 끝에 홀로 남은 `%`
- 지원하지 않는 `%x`
- `%s`에 널 포인터
- 출력 길이가 반환 타입 범위를 넘는 경우
- 버퍼가 결과보다 작은 경우

이번 연습은 널 문자열을 `(null)`로 표현하고, 지원하지 않는 지시자나 단독 `%`는 형식 오류로 처리합니다. 폭, 정밀도, 길이 수정자와 모든 표준 `printf` 기능을 한 번에 구현하지 않습니다.

## `v` 함수로 핵심 로직을 분리합니다

가변 인자 래퍼는 `va_list` 버전에 위임합니다.

```c
int diagnostic_vformat(
    char *buffer,
    size_t capacity,
    const char *format,
    va_list arguments
);

int diagnostic_format(char *buffer, size_t capacity, const char *format, ...)
{
    int result;
    va_list arguments;

    va_start(arguments, format);
    result = diagnostic_vformat(buffer, capacity, format, arguments);
    va_end(arguments);
    return result;
}
```

이 구조의 장점은 다음과 같습니다.

- 다른 가변 인자 함수가 현재 인자 목록을 전달할 수 있습니다.
- 파서와 출력 로직을 한곳에 유지합니다.
- 핵심 함수를 직접 테스트할 수 있습니다.
- `...`를 다른 `...` 함수에 직접 전달할 수 없다는 제한을 해결합니다.

## `va_list`는 소비되는 상태입니다

`va_arg`를 호출하면 목록의 현재 위치가 다음 인자로 이동합니다. 한 번 끝까지 읽은 목록을 처음부터 다시 사용할 수 있다고 가정하지 않습니다.

전달받은 원본 목록을 보존하려면 함수 내부에서 복사합니다.

```c
int diagnostic_vformat(
    char *buffer,
    size_t capacity,
    const char *format,
    va_list arguments
)
{
    int result;
    va_list copy;

    va_copy(copy, arguments);
    result = format_with_copy(buffer, capacity, format, copy);
    va_end(copy);
    return result;
}
```

헬퍼 함수가 목록을 소비하는지, 내부 복사해 원본을 보존하는지 API 계약에 써야 합니다. “함수 인자로 넘겼으니 자동 복사된다”는 가정은 이식 가능하지 않습니다.

## 한 번 순회와 두 번 순회

포맷터는 크게 두 방식으로 구현할 수 있습니다.

### 한 번 순회

인자를 읽으면서 다음을 동시에 수행합니다.

```text
필요한 전체 길이 계산
용량 안에 들어오는 바이트 기록
```

작은 버퍼에서도 전체 필요 길이를 반환할 수 있도록 실제 기록 길이와 논리적 길이를 분리해야 합니다.

### 두 번 순회

```text
첫 패스   필요한 전체 길이 계산
둘째 패스 버퍼에 실제 기록
```

두 패스에는 독립된 `va_list`가 필요합니다.

```c
va_list measure_arguments;
va_list write_arguments;

va_copy(measure_arguments, arguments);
va_copy(write_arguments, arguments);

/* 각각 독립적으로 순회 */

va_end(write_arguments);
va_end(measure_arguments);
```

두 번째 패스 전에 포맷 문법 전체를 검증할 수 있어 “형식 오류인데 접두사만 출력됨”을 피하기 쉽지만, 인자를 두 번 읽고 구현이 길어집니다. 어느 방식을 택하든 실패 뒤 버퍼 상태를 명시합니다.

## 버퍼 계약

`snprintf`와 비슷한 계약을 사용할 수 있습니다.

```text
capacity == 0이면 buffer는 NULL일 수 있음
capacity > 0이면 buffer는 쓰기 가능한 capacity 바이트
성공 결과는 필요했던 전체 문자 수(NUL 제외)
공간이 있으면 항상 NUL 종료
작은 버퍼에서는 잘리지만 전체 필요 길이는 계산
형식 오류 또는 표현 범위 초과는 -1
```

이 계약은 다음 세 값을 구분합니다.

```text
전체 필요 길이
실제로 기록한 데이터 길이
마지막 NUL을 포함한 버퍼 용량
```

`capacity == 1`이면 일반 문자는 하나도 기록하지 못하지만 `buffer[0] = '\0'`은 보장할 수 있습니다. `capacity == 0`일 때는 포인터를 역참조하지 않습니다.

## 출력 누적기

```c
struct output
{
    char *buffer;
    size_t capacity;
    size_t length;
    int failed;
};
```

문자 하나를 추가하는 함수가 다음 책임을 갖게 합니다.

- 전체 필요 길이를 증가시킵니다.
- `size_t` 오버플로를 검사합니다.
- 버퍼에 공간이 있을 때만 씁니다.
- 종료 NUL을 위한 한 바이트를 남깁니다.
- 이미 실패했다면 추가 상태 변경을 제한합니다.

문자열과 정수 변환이 같은 출력 경계를 사용하면 잘림 정책이 한곳에 모입니다.

## 길이 표현 범위

내부 길이는 `size_t`로 계산해도 공개 반환형이 `int`라면 `INT_MAX`보다 큰 결과를 표현할 수 없습니다.

```text
내부 size_t 덧셈 overflow 검사
→ 최종 길이가 INT_MAX 이하인지 검사
→ 표현 가능할 때만 int로 변환
```

캐스트는 큰 값을 안전하게 만들지 않습니다. API의 반환형이 표현할 수 없는 결과는 명시적 오류로 처리합니다.

## `INT_MIN` 변환

잘못된 구현:

```c
if (value < 0)
{
    value = -value;
}
```

`INT_MIN`의 양수 대응값은 `int`에 들어가지 않을 수 있습니다. unsigned 산술로 magnitude를 만듭니다.

```c
unsigned int magnitude;

if (value < 0)
{
    magnitude = 0u - (unsigned int)value;
}
else
{
    magnitude = (unsigned int)value;
}
```

부호 없는 정수의 모듈러 규칙을 이용하면 `INT_MIN`도 표현 가능한 magnitude를 얻을 수 있습니다. 숫자를 역순으로 모은 뒤 뒤집거나, 재귀 없이 가장 큰 자리부터 기록할 수 있습니다.

## `%c`와 포함된 NUL

이번 연습 범위에는 `%c`가 없지만, 포맷 API를 확장할 때 중요한 경계입니다.

```c
format_text(buffer, capacity, "A%cB", 0);
```

논리적 결과 바이트는 다음과 같습니다.

```text
'A' 00 'B' 00
```

첫 NUL 뒤에도 출력 바이트가 존재하지만 `strlen`과 `%s`는 볼 수 없습니다. `%c`로 NUL을 허용하는 API는 반환 길이와 `memcmp`로 검사해야 합니다. “결과는 항상 일반 C 문자열로만 관찰할 수 있다”는 계약과 임의 바이트 결과는 서로 다릅니다.

## 형식 오류 뒤 상태

지원하지 않는 `%x`를 만났을 때 선택지는 다음과 같습니다.

- 버퍼를 빈 문자열로 되돌립니다.
- 오류 지점 전까지의 접두사를 유지합니다.
- 임시 공간에 전체를 만든 뒤 성공할 때만 commit합니다.
- 첫 패스에서 문법을 검증해 쓰기 전에 오류를 반환합니다.

이번 연습은 오류 전까지 기록된 접두사를 NUL 종료하고 `-1`을 반환합니다. 강한 실패 보장이 아니라 **유효하게 종료된 부분 결과**를 제공하는 계약입니다. 호출자는 반환값이 음수이면 버퍼 내용을 정상 결과로 사용하지 않습니다.

## 형식 문자열은 신뢰 경계입니다

외부 입력을 포맷 문자열로 직접 사용하면 데이터 안의 `%`가 추가 인자를 읽으려 할 수 있습니다.

```c
printf(user_text);       /* 잘못된 패턴 */
printf("%s", user_text); /* 데이터를 문자열 인자로 전달 */
```

형식 문자열 취약점은 메모리 노출이나 쓰기로 이어질 수 있습니다. 로그 API에서도 “포맷”과 “데이터”를 분리합니다.

GCC와 Clang의 format attribute를 사용하면 자체 포맷 함수 일부를 컴파일 시 검사하게 할 수 있지만 이는 비표준 확장입니다. 지원 범위가 표준 `printf`와 다르면 잘못된 보장을 줄 수 있으므로 핵심 계약과 테스트를 대신하지 않습니다.

## 오류 계약 점검표

가변 인자 API는 최소한 다음을 정해야 합니다.

- `format == NULL`을 허용합니까?
- `capacity > 0`인데 `buffer == NULL`이면 어떻게 됩니까?
- `%s`의 널 포인터는 오류입니까, 고정 문자열입니까?
- 형식 오류 반환값은 무엇입니까?
- 길이 오버플로와 반환형 범위 초과는 어떻게 알립니까?
- 버퍼 부족은 오류입니까, 정상적인 잘림입니까?
- 실패 전에 쓴 접두사는 어떤 상태입니까?
- 전달받은 `va_list`를 소비합니까, 보존합니까?

호출자가 관찰할 수 없는 타입 불일치를 이 목록의 런타임 오류처럼 약속해서는 안 됩니다.

## 실습

[diagnostic-formatter](../../exercises/02-c-language/04-diagnostic-formatter/README.md)에서 다음을 구현합니다.

- `%s`, `%d`, `%%`
- 널 문자열의 `(null)` 표현
- 용량 0, 1, 정확한 크기와 잘림
- 모든 성공 경로의 NUL 종료
- `INT_MIN`, `INT_MAX`
- 지원하지 않는 지정자와 단독 `%`
- 전체 필요 길이의 overflow와 `int` 표현 범위
- `va_copy`를 이용한 원본 목록 보존

표준 `printf` 전체 재현이 아니라, 숨은 타입 계약과 소비되는 상태, 버퍼의 부분 성공을 정확히 다루는 것이 목표입니다.

## 다음 단계

포맷 결과를 파일 디스크립터에 직접 쓰려면 `write`의 부분 성공과 `EINTR`을 처리해야 합니다. [POSIX I/O와 스트림 상태](../03-unix-programming/01-posix-io-streams.md)에서 이어집니다.
