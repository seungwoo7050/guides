# 자료구조와 API 계약: 불변식·소유권·실패 보장

자료구조 구현의 핵심은 필드를 고르는 일이 아니라 모든 공개 연산 전후에 유지할 상태를 정의하는 일입니다. API는 정상 결과뿐 아니라 잘못된 인자, 자원 실패와 범위 오류 뒤의 상태도 약속해야 합니다.

## `struct`, `typedef`와 `enum`

구조체 값은 대입하고 함수 인자로 전달할 수 있습니다.

```c
struct point
{
    int x;
    int y;
};

struct point first = {1, 2};
struct point second = first;
```

이 복사는 멤버별 값 복사입니다. 포인터 멤버가 있다면 가리키는 자원까지 복제하지 않습니다.

```c
struct user
{
    char *name;
};
```

`struct user second = first;` 뒤 두 객체가 같은 할당을 가리킬 수 있습니다. 둘을 독립 소유자처럼 destroy하면 이중 해제가 됩니다. 깊은 복사가 필요하면 별도 함수와 실패 계약을 둡니다.

```c
int user_clone(const struct user *source, struct user *out_user);
```

`typedef`는 타입에 새 이름을 붙이지만 소유권을 만들어 주지는 않습니다. 특히 포인터 자체를 숨기는 typedef는 간접 수준과 null 가능성을 흐릴 수 있으므로 신중하게 사용합니다.

`enum`은 상태와 오류를 의미 있는 이름으로 표현합니다.

```c
enum parse_status
{
    PARSE_OK,
    PARSE_EMPTY,
    PARSE_INVALID,
    PARSE_NO_MEMORY
};
```

열거형의 정확한 크기와 표현을 파일 또는 네트워크 형식으로 사용하지 않습니다.

## 값 객체와 자원 소유 객체

다음과 같은 값 객체는 일반적인 구조체 복사가 자연스럽습니다.

```c
struct rectangle
{
    int width;
    int height;
};
```

반면 동적 메모리, 파일 디스크립터나 mutex를 가진 객체는 자원 수명 규칙이 필요합니다.

```c
struct document
{
    char *text;
    size_t length;
};
```

자원 소유 객체는 보통 다음과 같은 함수군을 갖습니다.

```c
void document_init(struct document *document);
void document_destroy(struct document *document);
int document_set(struct document *document, const char *text);
int document_clone(const struct document *source, struct document *out_document);
```

`init`/`destroy`는 호출자가 객체 저장 공간을 제공하는 패턴이고, `create`/`destroy`는 구현이 객체 자체까지 할당하는 패턴일 수 있습니다. 같은 이름을 사용하더라도 정확히 무엇을 해제하는지 문서화합니다.

전체를 0으로 채우는 것이 모든 타입의 유효한 초기화는 아닙니다. 포인터와 길이만 가진 단순 구조에는 잘 맞을 수 있지만 mutex, FD와 외부 라이브러리 handle은 전용 초기화가 필요합니다.

## 소유권을 나타내는 동사

함수 이름만으로 계약 전체를 표현할 수는 없지만 일관된 동사는 오해를 줄입니다.

| 동사 | 일반적인 의미 |
|---|---|
| `init` | 이미 존재하는 객체 저장 공간을 초기 상태로 만듦 |
| `create` | 객체 또는 자원을 새로 만들어 소유 포인터를 반환 |
| `clone` | 독립적으로 해제할 수 있는 깊은 복사 생성 |
| `take` | 성공 뒤 호출자의 소유권을 객체가 받음 |
| `release` | 객체가 가진 소유권을 호출자에게 넘김 |
| `destroy` | 객체가 소유한 자원을 정리 |

이 동사와 함께 null 허용 여부, 성공 뒤 소유자, 실패 뒤 입력 포인터 상태를 명시합니다.

## 동적 배열의 상태

```c
struct int_vector
{
    int *data;
    size_t size;
    size_t capacity;
};
```

대표 불변식:

```text
size <= capacity
capacity == 0이면 data == NULL
capacity > 0이면 data는 capacity개의 int를 저장할 수 있음
0 <= index < size인 원소만 초기화되어 있음
```

모든 공개 함수의 시작과 성공 반환 뒤에 이 불변식이 참이어야 합니다.

## API를 상태 전이로 보기

`push`는 다음 전이입니다.

```text
입력 상태 V, 값 x
→ 성공: size가 1 증가하고 마지막 원소가 x
→ 실패: V가 관찰 가능하게 동일
```

실패 뒤 상태가 유효하기만 하면 되는 basic guarantee와, 호출 전 상태를 그대로 보존하는 strong guarantee를 구분합니다. 작은 컨테이너의 `push`는 임시 포인터를 이용해 강한 보장을 제공하기 쉽습니다.

## 소유·빌림·이동

API 문서에서 포인터 역할을 명확히 합니다.

- owned: 함수나 객체가 해제 책임을 가집니다.
- borrowed const: 읽기만 하며 소유권을 받지 않습니다.
- borrowed mutable: 잠시 수정할 수 있지만 해제하지 않습니다.
- transferred: 성공하면 해제 책임이 이동합니다.

예:

```c
int vector_get(const struct int_vector *vector, size_t index, int *out_value);
```

`vector`는 읽기 전용 빌림, `out_value`는 호출자가 소유한 쓰기 가능한 객체입니다. 함수는 어느 것도 해제하지 않습니다.

## 출력 매개변수의 실패 보존

```c
int vector_get(const struct int_vector *vector, size_t index, int *out_value)
{
    if (vector == NULL || out_value == NULL || index >= vector->size)
    {
        return -1;
    }
    *out_value = vector->data[index];
    return 0;
}
```

검증을 먼저 하고 성공한 뒤에만 결과를 씁니다. 호출자는 실패 시 이전 `out_value`가 보존된다고 의존할 수 있습니다.

## opaque type과 공개 구조체

작은 교육용 구조체는 필드를 공개해 불변식을 직접 관찰할 수 있습니다. 라이브러리에서는 구현을 숨길 수 있습니다.

```c
struct int_vector;

struct int_vector *int_vector_create(void);
void int_vector_destroy(struct int_vector *vector);
```

구현 은닉은 호출자가 필드를 직접 깨뜨리지 못하게 하지만, 동적 생성과 ABI 같은 새 계약이 생깁니다. 어떤 선택도 자동으로 우월하지 않으며 변경 경계에 맞춰 결정합니다.

## 용량 증가 정책

매 push마다 정확히 한 칸만 늘리면 전체 복사량이 커집니다. 보통 용량을 배수로 늘립니다.

```text
0 → 4 → 8 → 16 → 32
```

성장 전에 다음을 확인합니다.

- `capacity * 2`가 `SIZE_MAX`를 넘지 않는가
- `new_capacity * sizeof(element)`가 넘지 않는가
- 실패하면 이전 포인터와 필드를 그대로 둘 수 있는가

성장 정책은 성능뿐 아니라 실패 지점과 메모리 상한을 결정하는 API의 일부입니다.

## 부분 초기화와 정리

여러 자원을 순서대로 얻는 함수는 역순 정리 경로를 가져야 합니다.

```c
int component_init(struct component *component)
{
    component->buffer = NULL;
    component->fd = -1;

    component->buffer = malloc(1024);
    if (component->buffer == NULL)
    {
        return -1;
    }
    component->fd = open(...);
    if (component->fd == -1)
    {
        component_destroy(component);
        return -1;
    }
    return 0;
}
```

초기 상태를 정리 가능한 sentinel로 만들고, 한 정리 함수가 완전·부분 초기화 모두 처리하게 합니다.

## 오류 코드 설계

`-1` 하나로 충분한 내부 함수도 있지만 호출자가 실패 원인에 따라 다르게 처리해야 한다면 열거형을 사용할 수 있습니다.

```c
enum vector_result
{
    VECTOR_OK = 0,
    VECTOR_INVALID = -1,
    VECTOR_NO_MEMORY = -2,
    VECTOR_RANGE = -3
};
```

오류 코드를 세분화하면 호출자 계약과 테스트도 늘어납니다. 실제 복구 행동이 다를 때만 구분합니다.

## allocator 주입

메모리 부족을 실제 시스템 상태에 맡기면 테스트가 결정적이지 않습니다. 교육용 자료구조는 allocator 함수를 주입해 특정 호출에서 실패하게 할 수 있습니다.

```c
struct allocator
{
    void *context;
    void *(*resize)(void *context, void *pointer, size_t size);
    void (*release)(void *context, void *pointer);
};
```

이 인터페이스는 운영 코드의 추상화를 늘리기 위한 것이 아니라 실패 계약을 검증하기 위한 테스트 경계입니다.

## 연결 리스트와 컨테이너 선택

```c
struct node
{
    char *value;
    struct node *next;
};
```

연결 리스트는 노드를 개별 할당하므로 삽입 때문에 기존 노드 주소가 이동하지 않습니다. 대신 인덱스 접근은 선형이고, 할당 수가 많으며, 포인터 추적으로 cache locality가 낮을 수 있습니다.

머리 노드를 바꾸는 함수는 포인터 슬롯 자체를 변경해야 합니다.

```c
int list_push_front(struct node **head, const char *value);
```

삭제 중에는 다음 노드를 먼저 보존합니다.

```c
struct node *next = current->next;
node_destroy(current);
current = next;
```

동적 배열과 리스트는 추상적인 “삽입이 많은가”만으로 선택하지 않습니다.

| 기준 | 동적 배열 | 연결 리스트 |
|---|---|---|
| 인덱스 접근 | 빠름 | 선형 탐색 |
| 순차 처리 | 연속 메모리 | 포인터 추적 |
| 중간 삽입·삭제 | 원소 이동 가능 | 위치를 알면 link 변경 |
| 원소 주소 | 성장 시 무효화 가능 | 노드 수명 동안 유지 |
| 할당 수 | 비교적 적음 | 노드마다 필요 |

실제 접근 패턴, 원소 수, 주소 안정성, 메모리 상한과 오류 지점을 기준으로 선택합니다.

## 헤더가 제공해야 하는 계약

공개 헤더와 문서는 호출자가 다음을 알 수 있게 해야 합니다.

- 타입을 어떤 함수로 초기화하고 정리하는가
- 입력 포인터가 null일 수 있는가
- 어느 포인터를 빌리고 복제하거나 이전하는가
- 성공과 각 실패를 어떤 값으로 구분하는가
- 실패 뒤 객체와 출력 매개변수의 상태는 무엇인가
- 반환된 view나 내부 포인터는 언제 무효화되는가
- 동시에 호출해도 되는가

구현 전용 helper와 파일 전용 상태는 `.c` 파일에 `static`으로 둡니다. 공개 구조체를 택했더라도 호출자가 임의로 필드를 바꾸는 것을 지원하는지 명시해야 합니다.

## `errno`와 자체 오류 타입

자체 라이브러리 오류를 무조건 `errno`에 저장하지 않습니다. `errno`는 C/POSIX 함수가 실패를 알린 직후 해석하는 보조 채널이며 성공한 호출이 0으로 초기화하지 않습니다.

단순한 성공·실패만 필요하면 0과 -1로 충분합니다. 호출자의 복구 행동이 실제로 달라질 때만 열거형이나 상세 상태를 추가합니다. 오류 종류가 늘어나면 테스트와 문서 계약도 함께 늘어납니다.

## 불변식 검사와 `assert`

개발 빌드에서는 내부 프로그래밍 오류를 조기에 드러내기 위해 불변식을 검사할 수 있습니다.

```c
assert(vector->size <= vector->capacity);
```

`assert`는 외부 입력 검증이나 복구 가능한 오류 처리를 대신하지 않습니다. `NDEBUG`가 정의되면 사라질 수 있으므로 표현식에 필수 side effect를 넣지 않습니다.

공개 함수 진입과 성공 반환 직전에 내부 검사를 두면 어느 연산이 상태를 깨뜨렸는지 좁히기 쉽습니다.

## 상태 머신

단순한 컨테이너를 넘어 연결·파서·작업 객체에는 명시적인 상태가 필요할 수 있습니다.

```c
enum connection_state
{
    CONNECTION_NEW,
    CONNECTION_OPEN,
    CONNECTION_CLOSED,
    CONNECTION_FAILED
};
```

```text
NEW → OPEN → CLOSED
NEW → FAILED
OPEN → FAILED
```

허용되지 않는 전이를 조용히 적용하지 않습니다. 상태를 확인한 뒤 변경하는 과정이 원자적이어야 하는 경우에는 뒤의 동시성 장에서 동기화 경계까지 함께 설계합니다.

## 함수 포인터와 callback

함수 포인터는 동작을 주입하고 테스트 실패를 결정적으로 만들 수 있습니다.

```c
typedef int (*item_predicate)(const void *item, void *context);
```

callback 계약에는 적어도 다음이 필요합니다.

- 어느 시점과 스레드에서 호출하는가
- 전달 포인터의 수명이 얼마나 지속되는가
- callback이 호출 중 컨테이너를 바꿔도 되는가
- callback 실패를 어떻게 반환하는가
- context를 누가 소유하는가

함수 포인터를 지나치게 일반화하면 타입 검사가 약해지고 소유권이 흐려집니다. allocator 주입처럼 검증 목적과 경계가 분명한 곳부터 사용합니다.

## 실습

[int-vector 연습](../../exercises/02-c-language/03-int-vector/README.md)에서 다음을 검사합니다.

- 초기 빈 상태
- 여러 번 성장
- 모든 기존 원소 보존
- 범위 밖 get과 출력 매개변수 보존
- 다음 성장 할당 실패 뒤 포인터·size·capacity·내용 보존
- overflow 거부
- 반복 가능한 destroy

완료 뒤 API 계약만 보고 다른 사람이 구현할 수 있는지, 테스트가 계약의 중요한 문장을 각각 확인하는지 검토합니다.
