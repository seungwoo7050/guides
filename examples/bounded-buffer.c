#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

enum { BUFFER_CAPACITY = 8 };

/* [Implementation 1] 하나의 mutex가 ring 위치, item 수, 종료 flag와 결과 통계를 함께 소유해야 predicate와 관찰값이 일치합니다. */
typedef struct s_buffer {
    int values[BUFFER_CAPACITY];
    size_t head;
    size_t tail;
    size_t count;
    int producer_done;
    long long produced_sum;
    long long consumed_sum;
    size_t produced_count;
    size_t consumed_count;
    pthread_mutex_t mutex;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
} t_buffer;

/* [Implementation 2] mutex와 두 condition을 의존 순서로 만들고 부분 실패에서는 만들어진 자원만 역순으로 파기합니다. */
static int buffer_init(t_buffer *buffer)
{
    buffer->head = 0U;
    buffer->tail = 0U;
    buffer->count = 0U;
    buffer->producer_done = 0;
    buffer->produced_sum = 0LL;
    buffer->consumed_sum = 0LL;
    buffer->produced_count = 0U;
    buffer->consumed_count = 0U;
    if (pthread_mutex_init(&buffer->mutex, NULL) != 0)
        return -1;
    if (pthread_cond_init(&buffer->not_empty, NULL) != 0) {
        (void)pthread_mutex_destroy(&buffer->mutex);
        return -1;
    }
    if (pthread_cond_init(&buffer->not_full, NULL) != 0) {
        (void)pthread_cond_destroy(&buffer->not_empty);
        (void)pthread_mutex_destroy(&buffer->mutex);
        return -1;
    }
    return 0;
}

static void buffer_destroy(t_buffer *buffer)
{
    (void)pthread_cond_destroy(&buffer->not_full);
    (void)pthread_cond_destroy(&buffer->not_empty);
    (void)pthread_mutex_destroy(&buffer->mutex);
}

/* [Implementation 3] full predicate를 while로 재검사한 뒤 ring 갱신과 통계를 같은 critical section에서 commit하고 consumer를 깨웁니다. */
static int buffer_push(t_buffer *buffer, int value)
{
    if (pthread_mutex_lock(&buffer->mutex) != 0)
        return -1;
    while (buffer->count == BUFFER_CAPACITY) {
        if (pthread_cond_wait(&buffer->not_full, &buffer->mutex) != 0) {
            (void)pthread_mutex_unlock(&buffer->mutex);
            return -1;
        }
    }
    buffer->values[buffer->tail] = value;
    buffer->tail = (buffer->tail + 1U) % BUFFER_CAPACITY;
    buffer->count += 1U;
    buffer->produced_count += 1U;
    buffer->produced_sum += value;
    (void)pthread_cond_signal(&buffer->not_empty);
    return pthread_mutex_unlock(&buffer->mutex) == 0 ? 0 : -1;
}

/* [Implementation 4] 종료 flag도 buffer 상태의 일부로 publish하고, 빈 queue에서 기다리는 모든 consumer가 종료 predicate를 다시 보게 합니다. */
static int mark_producer_done(t_buffer *buffer)
{
    if (pthread_mutex_lock(&buffer->mutex) != 0)
        return -1;
    buffer->producer_done = 1;
    (void)pthread_cond_broadcast(&buffer->not_empty);
    return pthread_mutex_unlock(&buffer->mutex) == 0 ? 0 : -1;
}

/* [Implementation 5] empty-or-done predicate로 data와 정상 종료를 구분하고 slot 회수 뒤 producer에게 진행 가능성을 넘깁니다. */
static int buffer_pop(t_buffer *buffer, int *value, int *finished)
{
    if (pthread_mutex_lock(&buffer->mutex) != 0)
        return -1;
    while (buffer->count == 0U && buffer->producer_done == 0) {
        if (pthread_cond_wait(&buffer->not_empty, &buffer->mutex) != 0) {
            (void)pthread_mutex_unlock(&buffer->mutex);
            return -1;
        }
    }
    if (buffer->count == 0U) {
        *finished = 1;
        return pthread_mutex_unlock(&buffer->mutex) == 0 ? 0 : -1;
    }
    *value = buffer->values[buffer->head];
    buffer->head = (buffer->head + 1U) % BUFFER_CAPACITY;
    buffer->count -= 1U;
    buffer->consumed_count += 1U;
    buffer->consumed_sum += *value;
    *finished = 0;
    (void)pthread_cond_signal(&buffer->not_full);
    return pthread_mutex_unlock(&buffer->mutex) == 0 ? 0 : -1;
}

static void *consumer_main(void *argument)
{
    t_buffer *buffer;
    int value;
    int finished;

    buffer = argument;
    finished = 0;
    while (finished == 0) {
        if (buffer_pop(buffer, &value, &finished) != 0)
            return (void *)1;
    }
    return NULL;
}

static int parse_items(const char *text, int *value)
{
    char *end;
    long parsed;

    end = NULL;
    parsed = strtol(text, &end, 10);
    if (text[0] == '\0' || end == NULL || *end != '\0' || parsed <= 0L || parsed > 100000L)
        return -1;
    *value = (int)parsed;
    return 0;
}

/* [Implementation 6] producer와 consumer 수명을 join으로 닫은 뒤 count와 합계 불변식을 외부 성공 조건으로 노출합니다. */
int main(int argc, char **argv)
{
    t_buffer buffer;
    pthread_t consumer;
    int items;
    int item;
    int producer_failed;
    void *status;
    int result;

    items = 1000;
    if (argc > 1 && parse_items(argv[1], &items) != 0) {
        fprintf(stderr, "사용법: %s [items:1..100000]\n", argv[0]);
        return 2;
    }
    if (buffer_init(&buffer) != 0) {
        fprintf(stderr, "버퍼 초기화에 실패했습니다.\n");
        return 1;
    }
    if (pthread_create(&consumer, NULL, consumer_main, &buffer) != 0) {
        fprintf(stderr, "소비자 스레드를 만들지 못했습니다.\n");
        buffer_destroy(&buffer);
        return 1;
    }

    producer_failed = 0;
    item = 1;
    while (item <= items) {
        if (buffer_push(&buffer, item) != 0) {
            producer_failed = 1;
            break;
        }
        item += 1;
    }
    if (mark_producer_done(&buffer) != 0)
        producer_failed = 1;

    status = NULL;
    if (pthread_join(consumer, &status) != 0 || status != NULL)
        producer_failed = 1;
    printf("produced=%zu consumed=%zu sums_match=%s\n",
        buffer.produced_count,
        buffer.consumed_count,
        buffer.produced_sum == buffer.consumed_sum ? "yes" : "no");
    result = producer_failed == 0
        && buffer.produced_count == buffer.consumed_count
        && buffer.produced_sum == buffer.consumed_sum ? 0 : 1;
    buffer_destroy(&buffer);
    return result;
}
