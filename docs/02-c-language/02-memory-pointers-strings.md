# 메모리·포인터·문자열: 수명과 소유권 추적

포인터는 주소를 저장하는 값이지만, 주소 비트만으로 안전성을 판단할 수 없습니다. 그 주소가 가리키는 객체가 살아 있는지, 접근 범위가 맞는지, 읽기·쓰기가 허용되는지와 누가 해제할지를 함께 추적해야 합니다.

## 객체·주소·수명

```c
int number = 42;
int *pointer = &number;
```

`number`는 저장 공간과 타입, 값과 수명을 가진 객체입니다. `pointer`도 별도의 객체이고 그 값이 `number`의 주소입니다.

```c
printf("%d\n", *pointer);
*pointer = 7;
```

간접 참조가 유효하려면 다음이 모두 필요합니다.

1. 적절한 타입과 정렬의 객체를 가리킵니다.
2. 그 객체의 수명이 끝나지 않았습니다.
3. 객체 또는 같은 배열의 허용된 범위 안입니다.
4. 해당 접근이 읽기 또는 쓰기를 허용합니다.

## null과 dangling은 다르다

`NULL`은 어떤 객체도 가리키지 않는 상태를 표현합니다. null을 간접 참조하면 안 됩니다. null이 아니라고 유효한 것은 아닙니다.

```c
int *bad_pointer(void)
{
    int local = 10;
    return &local;
}
```

함수 반환 뒤 `local`의 수명이 끝나므로 반환 포인터는 dangling 상태입니다. `free` 뒤의 포인터도 같은 문제가 있습니다.

```c
free(pointer);
pointer = NULL;
```

변수 하나를 null로 바꿔도 같은 객체를 가리키던 다른 별칭까지 안전해지는 것은 아닙니다.

## 값 전달과 출력 매개변수

포인터도 값으로 전달됩니다.

```c
int allocate_int(int **out_value)
{
    int *value = malloc(sizeof *value);

    if (value == NULL)
    {
        return -1;
    }
    *value = 0;
    *out_value = value;
    return 0;
}
```

출력 매개변수는 성공한 뒤에만 변경하는 것이 좋습니다. 할당이 실패하면 호출자의 이전 포인터가 보존됩니다.

## 배열과 포인터

```c
int values[4] = {10, 20, 30, 40};
```

배열은 네 `int`를 포함하는 하나의 객체입니다. 포인터 변수와 크기, 수명과 대입 가능성이 다릅니다. 다만 대부분의 식에서 첫 원소를 가리키는 포인터로 변환됩니다.

```c
size_t count = sizeof values / sizeof values[0];
int *begin = values;
int *end = values + count;
```

마지막 다음 포인터 `end`는 비교할 수 있지만 간접 참조할 수 없습니다. 포인터 산술은 같은 배열 객체의 범위에서만 의미가 있습니다.

함수는 배열 길이를 자동으로 알지 못합니다.

```c
void process(const int *values, size_t count);
```

## 문자열 불변식

C 문자열은 NUL 문자로 끝나는 문자 배열입니다.

```text
length < capacity
data[length] == '\0'
```

`strlen`은 NUL을 찾을 때까지 읽으므로 종료 문자가 없는 버퍼에 호출하면 경계를 넘을 수 있습니다. 복사·연결 시 용량에는 NUL 한 바이트를 포함해야 합니다.

`memcpy`는 겹치는 영역을 지원하지 않고, `memmove`는 겹침을 지원합니다. 그러나 어느 함수도 대상 용량을 자동으로 검사하지 않습니다.

## 동적 메모리와 소유권

```c
char *copy = malloc(length + 1);
```

호출 성공 뒤에는 다음 질문에 답해야 합니다.

- 이 객체를 누가 소유합니까?
- 어느 함수가 `free`합니까?
- 소유권이 다른 객체로 이동합니까?
- 오류 경로에서도 정확히 한 번 해제됩니까?
- 빌린 포인터는 소유 객체보다 오래 살아 있지 않습니까?

소유권은 C 문법이 자동으로 강제하지 않으므로 API 계약과 코드 구조로 표현합니다.

## `realloc`의 실패 계약

잘못된 패턴:

```c
buffer = realloc(buffer, new_capacity);
if (buffer == NULL)
{
    /* 이전 포인터를 잃음 */
}
```

안전한 패턴:

```c
char *resized = realloc(buffer, new_capacity);

if (resized == NULL)
{
    return -1;
}
buffer = resized;
```

실패한 `realloc`은 원래 할당을 그대로 유지합니다. 임시 포인터를 사용해야 이전 소유권을 잃지 않습니다.

## 크기 계산 overflow

```c
if (count > SIZE_MAX / sizeof *items)
{
    return -1;
}
items = malloc(count * sizeof *items);
```

곱셈 뒤 결과가 작아졌는지 확인하면 이미 잘못된 크기로 연산했을 수 있습니다. 연산 전에 나눗셈으로 가능 범위를 확인합니다. 문자열 길이 덧셈도 같은 방식으로 검사합니다.

## 포인터 선언과 `const`

선언의 `*`는 타입을 만들고, 식의 `*`는 가리키는 객체에 접근합니다.

```c
int *value_pointer;
const char *read_only_view;
int **out_pointer;
```

`const`의 위치도 계약에 포함됩니다.

```c
const char *text;        /* 이 경로로 문자를 수정하지 않음 */
char *const fixed = buf; /* 포인터 변수 자체를 바꾸지 않음 */
const char *const both = text;
```

`const`는 소유권이나 수명을 뜻하지 않습니다. `const char *`가 정적 문자열인지, 호출자가 빌려준 메모리인지, 다른 객체가 소유한 동적 할당인지는 별도로 정해야 합니다.

다중 포인터에서는 간접 수준마다 쓰기 권한이 달라집니다. `char **`를 `const char **`로 단순 변환할 수 있다고 가정하지 않습니다. 그런 변환은 수정 가능한 포인터 슬롯에 `const` 객체 주소를 넣는 경로를 만들 수 있습니다.

## 2차원 배열과 포인터 배열

```c
int matrix[3][4];
```

이 객체는 `int[4]` 세 개가 연속된 배열입니다. 식에서 변환될 때 타입은 `int (*)[4]`입니다.

```c
void print_matrix(const int matrix[][4], size_t rows);
```

반면 다음은 서로 다른 문자 배열을 가리킬 수 있는 포인터 배열입니다.

```c
char *words[4];
```

`int **`는 일반적인 `int[3][4]`의 대체 타입이 아닙니다. 실제 메모리 배치와 포인터 산술이 다릅니다. 함수 매개변수 타입은 “몇 차원처럼 보이는가”가 아니라 실제 객체 배치와 일치해야 합니다.

## 바이트 표현·정렬·별칭

`void *`는 객체 포인터를 일반적인 경계로 전달할 때 사용합니다. 직접 간접 참조할 수 없고 구체적인 타입과 계약이 필요합니다.

객체의 바이트 표현은 `unsigned char *`로 관찰할 수 있습니다.

```c
const unsigned char *bytes = (const unsigned char *)&number;
```

그러나 임의의 다른 타입 포인터로 바꿔 읽는 것은 정렬, 유효 타입과 별칭 규칙을 위반할 수 있습니다. 문법적으로 캐스트할 수 있다는 사실과 그 주소 접근이 정의되어 있다는 사실은 다릅니다.

직렬화 형식은 구조체의 메모리 바이트를 그대로 파일에 쓰는 방식으로 정하지 않습니다. padding, 정렬, 정수 크기와 byte order가 구현마다 다를 수 있습니다.

## 문자열과 바이트 버퍼 구분

모든 `char *`가 C 문자열은 아닙니다. 문자열 함수는 접근 가능한 범위 안에 NUL 종료가 존재한다는 선행조건을 요구합니다.

```c
char data[4] = {'A', '\0', 'B', '\0'};
```

이 배열에는 네 바이트가 있지만 `strlen(data)`는 1입니다. 저장된 바이트 수와 문자열 길이는 다른 값입니다.

문자열 리터럴은 수정하지 않습니다.

```c
const char *name = "reader";
```

`strlen`, `strcmp`, `strchr`는 유효한 문자열을 요구합니다. `memcpy`, `memmove`, `memcmp`는 명시한 바이트 수를 사용합니다.

- 원본과 대상이 겹치지 않으면 `memcpy`
- 겹칠 가능성이 있으면 `memmove`
- 임의 바이트 결과는 길이와 `memcmp`로 검사

`strcpy`는 대상 용량을 알지 못합니다. `strncpy`도 일반적인 “안전한 문자열 복사”가 아닙니다. 공간이 부족하면 NUL 종료를 보장하지 않으며 남은 공간을 0으로 채우는 별도 의미를 가집니다. 필요한 크기를 먼저 계산하거나 용량을 받는 명시적인 API를 사용합니다.

`strdup`은 널리 제공되지만 ISO C99 함수는 아닙니다. POSIX 기능을 사용할지, 작은 복제 함수를 직접 제공할지 프로젝트 기준에 맞춰 결정합니다.

## `malloc`·`calloc`·`free`

```c
int *items = malloc(count * sizeof *items);
```

C에서는 `malloc` 반환값을 불필요하게 캐스트하지 않습니다. `sizeof *items`는 포인터 대상 타입이 바뀌면 크기 계산도 함께 바뀌게 합니다.

- `malloc`은 초기화되지 않은 저장 공간을 제공합니다.
- `calloc(count, size)`는 배열 크기 곱을 구현이 처리하고 저장 공간을 0 비트로 채웁니다.
- `free(NULL)`은 아무 동작도 하지 않습니다.
- `free`는 객체 수명을 끝내지만 다른 별칭을 자동으로 null로 바꾸지 않습니다.

크기가 0인 할당의 반환 포인터에 특별한 의미를 부여하지 않습니다. 빈 상태를 `NULL, 0, 0`처럼 명시적으로 표현하면 구현별 세부 결과에 덜 의존합니다.

## 소유권을 API에 기록하기

포인터 매개변수와 반환값마다 역할을 정합니다.

| 역할 | 함수가 하는 일 | 호출 뒤 책임 |
|---|---|---|
| 빌림 | 호출 동안만 읽거나 제한적으로 수정 | 원래 소유자가 계속 관리 |
| 복제 | 별도 할당을 만들어 보관 | 새 소유자가 새 할당 해제 |
| 이전 | 기존 소유권을 받아 보관 | 성공 뒤 호출자는 사용·해제하지 않음 |
| 분리 | 보관하던 소유권을 반환 | 호출자가 새 소유자가 됨 |

```c
int string_join(const char *left, const char *right, char **out_result);
```

명확한 계약 예:

- `left`, `right`는 호출 중 빌립니다.
- 성공하면 `*out_result`는 새 할당을 가리킵니다.
- 호출자가 `free(*out_result)`합니다.
- 실패하면 `*out_result`를 변경하지 않습니다.

이 규칙을 함수 이름, `const`, 문서와 일관된 호출 패턴으로 함께 표현합니다.

## 실패 중 상태 교체

소유 객체를 바꿀 때는 가능한 한 다음 순서를 사용합니다.

```text
필요 크기와 overflow 확인
→ 새 자원 확보
→ 새 내용 완성
→ 객체가 가리키는 상태 교체
→ 이전 자원 정리
```

실패 전에 객체 필드를 먼저 바꾸면 호출자는 유효하지 않은 중간 상태를 받게 됩니다. 모든 API가 호출 전 상태를 완전히 보존할 수 있는 것은 아니지만, 다음 중 무엇인지 명시해야 합니다.

- 실패하면 호출 전 상태 유지
- 객체는 유효하지만 일부 상태가 바뀜
- 더 이상 재사용할 수 없고 destroy만 허용

## 흔한 결함 점검표

- 초기화하지 않은 포인터 간접 참조
- 지역 객체 주소 반환
- `free` 뒤 사용 또는 두 번 해제
- 배열 길이가 함수에 자동 전달된다고 가정
- 마지막 다음 포인터 간접 참조
- NUL 한 바이트를 용량에서 누락
- 바이트 버퍼를 문자열로 취급
- 겹치는 범위에 `memcpy` 사용
- 할당 크기 overflow를 연산 뒤 검사
- `realloc` 결과를 기존 포인터에 직접 대입
- 성장 가능한 버퍼 내부 주소를 장기간 보관
- 빌린 포인터를 소유 포인터처럼 해제

AddressSanitizer와 UndefinedBehaviorSanitizer는 많은 결함을 드러내지만, 호출하지 않은 경로와 잘못된 소유권 문서를 자동으로 교정하지는 않습니다.

## 성장 가능한 소유 문자열

```c
struct owned_string
{
    char *data;
    size_t length;
    size_t capacity;
};
```

유효 상태를 다음처럼 정할 수 있습니다.

```text
빈 상태:
  data == NULL
  length == 0
  capacity == 0

할당 상태:
  data != NULL
  length < capacity
  data[length] == '\0'
```

append의 강한 실패 보장은 다음입니다.

```text
성공: 새 문자열과 길이·용량을 모두 반영
실패: 호출 전 내용·포인터·길이·용량을 보존
```

현재 `data` 전체나 내부 suffix를 source로 다시 전달하면 `realloc` 뒤 source 주소가 바뀔 수 있습니다. 성장 전에 내부 offset을 기록하고, 성공한 새 `data`를 기준으로 source를 다시 계산해야 합니다.

## 정리 함수는 멱등하게

```c
void owned_string_destroy(struct owned_string *string)
{
    free(string->data);
    string->data = NULL;
    string->length = 0;
    string->capacity = 0;
}
```

`free(NULL)`은 안전합니다. 정리 뒤 빈 상태로 되돌리면 같은 정리 함수를 반복 호출해도 안전하고, 부분 초기화 오류 경로에서도 사용하기 쉽습니다.

## 실습

[owned-string 연습](../../exercises/02-c-language/02-owned-string/README.md)에서 다음을 구현합니다.

- 문자열 불변식
- 지수적 용량 증가
- 크기 overflow 검사
- `realloc` 실패 뒤 상태 보존
- 전체 문자열과 내부 suffix의 alias append
- 반복 가능한 destroy
- 할당 실패의 결정적 주입

테스트가 통과한 뒤 일부러 직접 대입 `realloc`, NUL 누락, 길이 선반영 결함을 넣어 어떤 검사가 잡는지 확인합니다.
