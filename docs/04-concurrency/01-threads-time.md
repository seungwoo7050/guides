# 스레드·동기화·시간: 공유 불변식과 종료 설계

스레드는 같은 프로세스의 주소 공간을 공유하는 여러 실행 흐름입니다. 공유가 쉽기 때문에 경쟁 상태도 쉽게 생깁니다. pthread 함수를 호출하는 문법보다 중요한 것은 **어떤 데이터가 어떤 동기화 규칙으로 보호되며, 어떤 상태 전이까지 한 임계 구역에서 끝나야 하는지**를 일관되게 설계하는 일입니다.

## 프로세스와 스레드

한 프로세스의 스레드는 일반적으로 다음을 공유합니다.

- 코드와 전역 객체
- 힙 할당
- 파일 디스크립터 테이블
- 프로세스 환경과 작업 디렉터리

각 스레드는 별도의 스택, 레지스터와 실행 문맥을 가집니다. 지역 변수는 보통 해당 스레드의 스택에 있지만 주소를 다른 스레드에 전달하면 공유 접근이 됩니다.

프로세스는 주소 공간이 분리되어 IPC가 필요하지만 스레드는 같은 객체를 직접 볼 수 있습니다. 이 편의가 데이터 경쟁의 원인이기도 합니다.

## 생성과 join

```c
void *worker_main(void *opaque)
{
    struct worker_argument *argument = opaque;

    /* 작업 */
    return NULL;
}
```

```c
pthread_t thread;
int error = pthread_create(&thread, NULL, worker_main, &argument);
```

pthread 함수는 많은 POSIX 시스템 호출처럼 `-1`과 `errno`를 사용하는 대신 오류 번호를 직접 반환합니다.

```c
if (error != 0)
{
    fprintf(stderr, "pthread_create: %s\n", strerror(error));
}
```

join 가능한 스레드는 종료 뒤 `pthread_join`으로 자원을 회수합니다.

```c
error = pthread_join(thread, NULL);
```

join하지 않을 스레드는 detach 정책을 명확히 합니다. 생성한 각 스레드마다 누가 join하거나 detach하는지 소유권이 필요합니다.

## 스레드 인자의 수명

잘못된 패턴:

```c
for (int index = 0; index < count; index++)
{
    pthread_create(&threads[index], NULL, worker_main, &index);
}
```

모든 스레드가 같은 루프 변수 주소를 봅니다. worker가 실제로 읽을 때 값은 이미 바뀌었거나 함수 반환 뒤 수명이 끝났을 수 있습니다.

각 스레드가 고유한 배열 원소를 받게 합니다.

```c
for (size_t index = 0; index < count; index++)
{
    arguments[index].id = index;
    pthread_create(
        &threads[index],
        NULL,
        worker_main,
        &arguments[index]
    );
}
```

호출자 스택의 `arguments` 배열은 모든 worker가 끝날 때까지 살아 있어야 합니다. 동적 할당 인자를 worker가 해제한다면 소유권 이전을 명시합니다.

## data race는 정의되지 않은 동작입니다

두 스레드가 같은 메모리 위치에 동기화 없이 접근하고 적어도 하나가 쓰기라면 data race가 발생할 수 있습니다.

```c
shared_count++; /* 읽기, 계산, 쓰기의 복합 연산 */
```

기계어 한 번처럼 보이거나 실행 결과가 자주 맞더라도 언어 수준에서 자동 동기화되는 것은 아닙니다. C의 data race는 “가끔 값이 틀릴 수 있음”이 아니라 정의되지 않은 동작입니다.

공유 상태를 줄이고 가능한 데이터는 worker별로 분리합니다. 실제 공유 상태에는 mutex, 조건 변수 또는 요구에 맞는 C atomic을 사용합니다. 이 장은 mutex 기반 불변식 설계에 집중합니다.

## mutex의 생명주기

```c
pthread_mutex_t mutex;

int error = pthread_mutex_init(&mutex, NULL);
if (error != 0)
{
    /* 초기화 실패 */
}
```

```c
pthread_mutex_lock(&mutex);
/* 임계 구역 */
pthread_mutex_unlock(&mutex);
```

어떤 스레드도 더 이상 접근하지 않고 mutex가 잠겨 있지 않을 때 해제합니다.

```c
pthread_mutex_destroy(&mutex);
```

초기화하지 않은 mutex, 잠긴 mutex 또는 다른 스레드가 사용할 수 있는 mutex를 destroy하면 안 됩니다. 타입의 `initialized` 상태와 상위 객체 수명을 함께 관리합니다.

정적 수명의 단일 mutex에는 `PTHREAD_MUTEX_INITIALIZER`를 사용할 수 있지만, 동적 배열과 부분 초기화 정리에는 명시적인 init/destroy가 보통 더 적합합니다.

## mutex는 특정 메모리를 자동으로 보호하지 않습니다

```c
struct account
{
    unsigned long id;
    long balance;
    pthread_mutex_t mutex;
};
```

mutex와 `balance`가 같은 구조체 안에 있다고 자동으로 연결되는 것은 아닙니다. 프로그램 전체가 다음 규칙을 지켜야 합니다.

```text
account.mutex는 account.balance와 관련 불변식을 보호한다.
balance를 읽거나 쓸 때 항상 해당 mutex를 가진다.
```

읽기 함수에도 같은 규칙이 필요합니다.

```c
int account_get_balance(struct account *account, long *out_balance)
{
    long snapshot;

    pthread_mutex_lock(&account->mutex);
    snapshot = account->balance;
    pthread_mutex_unlock(&account->mutex);
    *out_balance = snapshot;
    return 0;
}
```

한 경로만 잠그고 다른 경로는 직접 읽으면 보호 계약이 깨집니다. “읽기니까 안전하다”는 가정은 writer와 동시에 실행될 수 있을 때 성립하지 않습니다.

## 임계 구역은 불변식 단위입니다

다음 두 연산을 따로 잠그면 경쟁이 생깁니다.

```text
잔액이 충분한지 확인
잔액을 차감
```

검증과 변경을 하나의 임계 구역에서 끝냅니다.

```c
pthread_mutex_lock(&account->mutex);
if (account->balance >= amount)
{
    account->balance -= amount;
    result = 0;
}
pthread_mutex_unlock(&account->mutex);
```

여러 필드가 하나의 불변식을 이루면 관련 읽기와 쓰기도 함께 잠급니다. 임계 구역 안에서 외부 callback, 느린 I/O 또는 다른 계층의 잠금 함수를 호출하면 예상하지 못한 대기와 lock 순서가 생길 수 있으므로 피하거나 계약을 명시합니다.

## 두 객체 잠금과 deadlock

계좌 이체는 두 계좌를 동시에 잠가야 전체 합을 보존할 수 있습니다.

```text
스레드 A: 계좌 1 잠금 → 계좌 2 잠금
스레드 B: 계좌 2 잠금 → 계좌 1 잠금
```

서로 상대 lock을 기다리면 deadlock입니다. 모든 스레드가 같은 전역 순서로 lock을 잡게 합니다.

```text
항상 작은 account id 먼저, 큰 id 다음
```

```c
struct account *first = source->id < destination->id
    ? source : destination;
struct account *second = source->id < destination->id
    ? destination : source;
```

관련 없는 객체 포인터의 `<` 비교를 잠금 순서로 사용하는 것은 이식 가능한 일반 규칙이 아닙니다. 명시적이고 유일한 ID나 상위 컨테이너 인덱스가 더 분명합니다.

같은 객체가 두 인자로 들어오면 같은 비재귀 mutex를 두 번 잠그지 않도록 별도 처리합니다. 서로 다른 객체가 같은 ID를 가진다면 전역 순서가 유일하지 않으므로 입력을 거부합니다.

## 이체의 원자적 상태 전이

계좌 이체 계약:

```text
전제:
  amount >= 0
  두 객체가 초기화됨
  서로 다른 객체라면 ID가 다름

성공 조건:
  source 잔액 충분
  destination 덧셈이 LONG_MAX를 넘지 않음

성공 결과:
  source -= amount
  destination += amount
  두 계좌 합 보존

실패 결과:
  두 잔액 모두 호출 전과 동일
```

검증과 두 갱신을 모두 두 lock을 가진 상태에서 수행합니다. source에서 먼저 차감한 뒤 destination overflow를 발견하면 강한 실패 보장이 깨집니다. 모든 전제를 확인한 뒤 두 필드를 commit합니다.

같은 계좌로의 이체는 잔액이 충분하면 성공하지만 상태는 바뀌지 않는 계약으로 둘 수 있습니다. 이 경우 mutex를 한 번만 잠급니다.

## 여러 mutex와 해제 순서

두 번째 lock에 실패하면 첫 번째 lock을 풀고 오류를 반환합니다.

```c
if (pthread_mutex_lock(&first->mutex) != 0)
{
    return -1;
}
if (pthread_mutex_lock(&second->mutex) != 0)
{
    pthread_mutex_unlock(&first->mutex);
    return -1;
}
```

일반적으로 획득 역순으로 해제하면 중첩 구조를 읽기 쉽습니다. unlock 실패를 무시할지 치명적 상태로 다룰지도 라이브러리 경계에 따라 정합니다. mutex 소유권 위반을 정상 복구 가능한 입력 오류처럼 취급해서는 안 됩니다.

## 상태용 mutex와 출력용 mutex를 분리할 수 있습니다

느린 로그 출력을 잔액 mutex 안에서 수행하면 다른 worker의 상태 접근이 불필요하게 막힙니다.

```text
state mutex  잔액·queue·종료 flag 같은 업무 상태
log mutex    한 줄 출력이 섞이지 않게 직렬화
```

mutex를 너무 잘게 나누면 lock 순서가 복잡해지고, 하나로 합치면 경쟁 범위가 커집니다. 보호할 불변식을 기준으로 나눕니다.

로그에 상태 snapshot이 필요하면 상태 lock 안에서 값을 복사하고 lock을 푼 뒤 출력할 수 있습니다. 그 로그는 특정 시점의 snapshot이지 출력 시점의 최신 상태는 아닙니다.

## 조건 변수는 조건 자체가 아닙니다

mutex는 한 번에 한 스레드만 상태를 변경하게 합니다. 조건 변수는 상태가 바뀔 때까지 잠들어 기다리게 합니다.

```c
pthread_mutex_lock(&queue->mutex);
while (queue->length == 0 && !queue->closed)
{
    pthread_cond_wait(&queue->not_empty, &queue->mutex);
}
/* 조건을 다시 검사한 뒤 처리 */
pthread_mutex_unlock(&queue->mutex);
```

`pthread_cond_wait`는 mutex를 원자적으로 풀고 잠들며, 깨어날 때 다시 잡습니다. 반드시 `while`로 조건을 재검사합니다.

- spurious wakeup이 가능합니다.
- 여러 대기자가 같은 통지를 받을 수 있습니다.
- 깨어난 뒤 lock을 얻기 전에 다른 스레드가 상태를 소비할 수 있습니다.
- signal은 과거 상태를 저장하는 queue가 아닙니다.

실제 조건은 `queue->length > 0` 같은 공유 상태이며 condition variable은 변화 통지 수단입니다.

## 종료는 별도의 상태 전이입니다

worker가 반복 실행하는 프로그램은 stop flag와 깨우기 수단이 필요합니다.

```text
RUNNING → STOP_REQUESTED → DRAINING → STOPPED
```

```c
pthread_mutex_lock(&state->mutex);
state->stopping = 1;
pthread_cond_broadcast(&state->changed);
pthread_mutex_unlock(&state->mutex);
```

flag만 바꾸고 condition variable을 깨우지 않으면 잠든 worker가 종료를 관찰하지 못할 수 있습니다.

다음 정책을 정합니다.

- 새 작업 수락을 언제 중단합니까?
- queue에 남은 작업을 처리합니까, 버립니까?
- 누가 모든 worker를 join합니까?
- worker가 외부 I/O에서 block 중이면 어떻게 깨웁니까?
- 부분 결과를 어떤 상태로 남깁니까?

`pthread_cancel`은 cancellation point와 cleanup handler 규칙이 복잡합니다. 초기 설계에서는 공유 종료 상태를 설정하고 worker가 정상 경로로 반환하게 하는 편이 단순합니다.

## 단조 시계와 wall clock

달력 시간과 경과 시간을 구분합니다.

```c
struct timespec now;
clock_gettime(CLOCK_MONOTONIC, &now);
```

wall clock은 관리자 변경, NTP 보정과 시간대 정책으로 점프할 수 있습니다. timeout, deadline과 경과 시간에는 `CLOCK_MONOTONIC`을 사용합니다.

시간을 밀리초 정수로 바꿀 때는 다음을 확인합니다.

- `tv_sec * 1000`의 overflow
- 나노초를 밀리초로 자를 때의 정밀도 손실
- signed/unsigned 혼합
- deadline 덧셈의 carry

가능하면 `struct timespec`을 유지하며 비교·덧셈·차감을 담당하는 작은 헬퍼를 둡니다.

## 상대 sleep과 절대 deadline

바쁜 대기는 CPU를 계속 사용합니다.

```c
while (before_deadline())
{
    /* 아무것도 하지 않음 */
}
```

`nanosleep`은 CPU를 양보하지만 시그널로 중단될 수 있습니다.

```c
struct timespec remaining = requested;

while (nanosleep(&remaining, &remaining) < 0 && errno == EINTR)
{
    /* 남은 시간으로 재시도 */
}
```

주기 작업에서 “작업 후 10ms sleep”을 반복하면 작업 시간과 scheduling 지연이 누적됩니다. 다음 절대 deadline을 기준으로 계산하면 drift를 줄일 수 있습니다.

```text
next_deadline += period
현재가 deadline보다 이르면 남은 시간만 대기
이미 늦었다면 지연 정책 적용
```

condition variable의 timed wait가 어떤 시계를 사용하는지도 확인합니다. 환경에 따라 속성으로 monotonic clock을 선택할 수 있습니다.

## 부분 mutex 초기화 실패

mutex 배열의 k번째 초기화에서 실패할 수 있습니다.

```c
size_t initialized = 0;

for (size_t index = 0; index < count; index++)
{
    int error = pthread_mutex_init(&items[index].mutex, NULL);

    if (error != 0)
    {
        while (initialized > 0)
        {
            initialized--;
            pthread_mutex_destroy(&items[initialized].mutex);
        }
        return error;
    }
    initialized++;
}
```

초기화에 성공한 개수만 destroy합니다. 아직 초기화되지 않은 객체에 destroy를 호출하지 않습니다.

## 부분 스레드 생성 실패

N개 중 k번째 `pthread_create`가 실패할 수 있습니다. 이미 생성한 worker는 실행 중입니다.

```text
stop 상태 설정
→ 잠든 worker 깨우기
→ 생성된 개수만 join
→ worker 인자와 공유 자원 정리
→ 오류 반환
```

생성하지 않은 `pthread_t` 값을 join하지 않습니다. worker가 시작 gate에서 기다리는 테스트라면 main이 실패 경로에서도 gate를 열거나 종료 상태를 전달해 이미 생성된 worker가 빠져나오게 해야 합니다.

## 공정성, 기아와 성능

Deadlock이 없다고 모든 스레드가 공정하게 진행하는 것은 아닙니다. 한 스레드가 lock을 반복 선점해 다른 스레드가 오래 기다리는 starvation이 생길 수 있습니다.

기본 POSIX mutex가 강한 공정성을 보장한다고 가정하지 않습니다. 필요하면 다음을 측정합니다.

- 스레드별 성공 횟수
- 평균·최대 lock 대기 시간
- 임계 구역 길이
- lock 경합률
- condition variable wakeup 패턴
- 작업 분배 불균형

`usleep(1)` 같은 임의 지연은 특정 실행에서 경합을 바꿀 뿐 공정성 보장이 아닙니다.

## 동시성 테스트는 실행 순서가 아니라 불변식을 봅니다

계좌 이체 예:

```text
모든 잔액은 음수가 아님
전체 잔액 합은 시작과 동일
overflow 실패 뒤 두 잔액 보존
모든 worker가 종료
정해진 timeout 안에 완료
```

여러 worker를 비슷한 시점에 시작하려면 barrier 또는 mutex+condition 기반 start gate를 사용합니다. 단순 `sleep`으로 “아마 동시에 시작했을 것”이라고 추측하지 않습니다.

일정한 최종 잔액을 기대하려면 양방향 이체 횟수와 초기 조건을 대칭으로 설계합니다. 실행 순서 자체는 고정하지 않습니다.

## sanitizer와 도구의 한계

ThreadSanitizer:

```sh
cc -fsanitize=thread ...
```

실행한 경로에서 data race를 찾는 데 유용하지만 다음을 증명하지는 않습니다.

- 모든 interleaving이 안전함
- deadlock이 없음
- 업무 불변식이 맞음
- starvation이 없음
- timeout이 정확함

AddressSanitizer와 동시에 사용할 수 없는 환경이 많으므로 별도 target으로 둡니다. 외부 timeout은 무한 대기를 막지만 정상 종료의 논리적 증명은 아닙니다.

## 객체 해제 계약

`account_destroy`는 다음 전제를 요구합니다.

```text
어떤 worker도 account에 접근하지 않음
해당 mutex를 아무도 보유하지 않음
모든 관련 worker가 join됨
```

이 전제 없이 mutex를 destroy하고 `initialized` flag를 바꾸면 다른 스레드가 파괴된 동기화 객체를 사용할 수 있습니다. 해제 함수가 자체 lock만으로 전체 수명을 해결할 수 있는 것은 아닙니다. 상위 소유자가 thread 종료 순서를 보장해야 합니다.

## 실습

[account-simulator](../../exercises/04-concurrency/01-account-simulator/README.md)에서 다음을 구현합니다.

- 계좌별 mutex 초기화와 반복 destroy 안전성
- balance 읽기의 동기화와 출력 매개변수 보존
- 명시적 ID 기반 두 lock 순서
- 같은 객체와 같은 ID의 다른 객체 구분
- 잔액 부족·음수 금액·목적지 overflow 검증
- 실패 시 두 잔액 보존
- 같은 계좌 이체의 단일 lock 처리
- 두 계좌 합을 일관된 snapshot으로 읽기
- 8개 worker의 양방향 반복 이체
- condition variable 기반 start gate
- 전체 합과 개별 잔액 불변식
- timeout, AddressSanitizer·UndefinedBehaviorSanitizer와 ThreadSanitizer

검사는 특정 출력 순서가 아니라 상태 계약을 확인합니다. 완료 뒤 한 방향만 ID 순서를 무시하도록 바꿔 timeout 또는 ThreadSanitizer가 아니라 기본 불변식·교착 검사가 어떤 결함을 잡는지 관찰합니다.

## 과정의 종료

여기까지 완료하면 작은 C 프로그램을 다음 기준으로 설계할 수 있어야 합니다.

- 타입·수명·소유권을 공개 API에 드러냅니다.
- 부분 성공과 실패 뒤 상태를 정합니다.
- FD, process와 thread의 정리 책임을 추적합니다.
- 논리적 레코드와 커널 I/O 경계를 분리합니다.
- 비동기 handler와 일반 정책 코드를 분리합니다.
- 동시 실행 순서가 아니라 공유 불변식으로 정확성을 검사합니다.

전체 경로와 다음 프로젝트 선택은 [학습 경로](../00-roadmap.md)에서 다시 확인할 수 있습니다.
