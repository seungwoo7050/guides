#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

struct account
{
    size_t id;
    long balance;
    pthread_mutex_t mutex;
};

struct bank
{
    struct account *accounts;
    size_t account_count;
    pthread_mutex_t log_mutex;
    size_t initialized_accounts;
    int log_ready;
    int verbose;
};

struct worker
{
    struct bank *bank;
    size_t id;
    size_t operations;
    uint32_t random_state;
    size_t completed;
};

static uint32_t next_random(uint32_t *state)
{
    uint32_t value = *state;

    value ^= value << 13;
    value ^= value >> 17;
    value ^= value << 5;
    *state = value;
    return value;
}

static void bank_destroy(struct bank *bank)
{
    while (bank->initialized_accounts > 0)
    {
        bank->initialized_accounts--;
        pthread_mutex_destroy(&bank->accounts[bank->initialized_accounts].mutex);
    }
    if (bank->log_ready)
    {
        pthread_mutex_destroy(&bank->log_mutex);
        bank->log_ready = 0;
    }
    free(bank->accounts);
    bank->accounts = NULL;
    bank->account_count = 0;
}

static int bank_init(
    struct bank *bank,
    size_t account_count,
    long initial_balance,
    int verbose
)
{
    size_t i;
    int error;

    memset(bank, 0, sizeof *bank);
    bank->verbose = verbose;
    bank->accounts = calloc(account_count, sizeof bank->accounts[0]);
    if (bank->accounts == NULL)
        return ENOMEM;
    bank->account_count = account_count;
    error = pthread_mutex_init(&bank->log_mutex, NULL);
    if (error != 0)
    {
        bank_destroy(bank);
        return error;
    }
    bank->log_ready = 1;
    for (i = 0; i < account_count; i++)
    {
        bank->accounts[i].id = i;
        bank->accounts[i].balance = initial_balance;
        error = pthread_mutex_init(&bank->accounts[i].mutex, NULL);
        if (error != 0)
        {
            bank_destroy(bank);
            return error;
        }
        bank->initialized_accounts++;
    }
    return 0;
}

static int transfer(
    struct bank *bank,
    size_t from_index,
    size_t to_index,
    long amount,
    size_t worker_id
)
{
    struct account *from;
    struct account *to;
    struct account *first;
    struct account *second;
    int completed = 0;

    if (from_index == to_index || amount <= 0)
        return 0;
    from = &bank->accounts[from_index];
    to = &bank->accounts[to_index];
    first = from->id < to->id ? from : to;
    second = from->id < to->id ? to : from;

    pthread_mutex_lock(&first->mutex);
    pthread_mutex_lock(&second->mutex);
    if (from->balance >= amount)
    {
        from->balance -= amount;
        to->balance += amount;
        completed = 1;
    }
    pthread_mutex_unlock(&second->mutex);
    pthread_mutex_unlock(&first->mutex);

    if (completed && bank->verbose)
    {
        pthread_mutex_lock(&bank->log_mutex);
        printf("worker=%zu from=%zu to=%zu amount=%ld\n",
            worker_id, from_index, to_index, amount);
        pthread_mutex_unlock(&bank->log_mutex);
    }
    return completed;
}

static void *worker_main(void *argument)
{
    struct worker *worker = argument;
    size_t i;

    for (i = 0; i < worker->operations; i++)
    {
        size_t from = next_random(&worker->random_state) % worker->bank->account_count;
        size_t to = next_random(&worker->random_state) % worker->bank->account_count;
        long amount = (long)(next_random(&worker->random_state) % 50u) + 1;

        if (transfer(worker->bank, from, to, amount, worker->id))
            worker->completed++;
    }
    return NULL;
}

static long bank_total(struct bank *bank)
{
    long total = 0;
    size_t i;

    for (i = 0; i < bank->account_count; i++)
    {
        pthread_mutex_lock(&bank->accounts[i].mutex);
        total += bank->accounts[i].balance;
        pthread_mutex_unlock(&bank->accounts[i].mutex);
    }
    return total;
}

static int parse_size(const char *text, size_t *out)
{
    char *end;
    unsigned long value;

    errno = 0;
    value = strtoul(text, &end, 10);
    if (errno != 0 || *text == '\0' || *end != '\0' || value == 0)
        return -1;
    *out = (size_t)value;
    if ((unsigned long)*out != value)
        return -1;
    return 0;
}

static long elapsed_ms(const struct timespec *start, const struct timespec *end)
{
    long seconds = (long)(end->tv_sec - start->tv_sec);
    long nanoseconds = end->tv_nsec - start->tv_nsec;

    return seconds * 1000L + nanoseconds / 1000000L;
}

int main(int argc, char **argv)
{
    size_t account_count = 8;
    size_t worker_count = 8;
    size_t operations = 10000;
    long initial_balance = 100000;
    struct bank bank;
    struct worker *workers = NULL;
    pthread_t *threads = NULL;
    size_t started = 0;
    size_t i;
    long initial_total;
    long final_total;
    size_t completed = 0;
    int result = EXIT_FAILURE;
    const char *fail_text;
    size_t fail_after = (size_t)-1;
    struct timespec start_time;
    struct timespec end_time;

    if (argc == 4 &&
        (parse_size(argv[1], &account_count) != 0 ||
         parse_size(argv[2], &worker_count) != 0 ||
         parse_size(argv[3], &operations) != 0))
    {
        fprintf(stderr, "사용법: %s [계좌-수 작업자-수 연산-수]\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (argc != 1 && argc != 4)
    {
        fprintf(stderr, "사용법: %s [계좌-수 작업자-수 연산-수]\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (account_count < 2)
    {
        fprintf(stderr, "계좌는 두 개 이상이어야 합니다\n");
        return EXIT_FAILURE;
    }

    fail_text = getenv("BANK_FAIL_AFTER");
    if (fail_text != NULL && parse_size(fail_text, &fail_after) != 0)
        fail_after = (size_t)-1;

    if (bank_init(&bank, account_count, initial_balance, getenv("BANK_VERBOSE") != NULL) != 0)
    {
        fprintf(stderr, "계좌 저장소를 초기화하지 못했습니다\n");
        return EXIT_FAILURE;
    }
    workers = calloc(worker_count, sizeof workers[0]);
    threads = calloc(worker_count, sizeof threads[0]);
    if (workers == NULL || threads == NULL)
        goto cleanup;

    initial_total = bank_total(&bank);
    clock_gettime(CLOCK_MONOTONIC, &start_time);
    for (i = 0; i < worker_count; i++)
    {
        int error;

        workers[i].bank = &bank;
        workers[i].id = i;
        workers[i].operations = operations;
        workers[i].random_state = (uint32_t)(0x9e3779b9u ^ (uint32_t)(i + 1));
        if (i == fail_after)
            error = EAGAIN;
        else
            error = pthread_create(&threads[i], NULL, worker_main, &workers[i]);
        if (error != 0)
        {
            fprintf(stderr, "%zu번 작업자 스레드를 만들지 못했습니다: %s\n", i, strerror(error));
            goto join_started;
        }
        started++;
    }

join_started:
    for (i = 0; i < started; i++)
        pthread_join(threads[i], NULL);
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    if (started != worker_count)
        goto cleanup;

    for (i = 0; i < worker_count; i++)
        completed += workers[i].completed;
    final_total = bank_total(&bank);
    printf("initial=%ld final=%ld completed=%zu elapsed_ms=%ld\n",
        initial_total, final_total, completed, elapsed_ms(&start_time, &end_time));
    if (final_total != initial_total)
    {
        fprintf(stderr, "전체 잔액 불변식이 깨졌습니다\n");
        goto cleanup;
    }
    for (i = 0; i < account_count; i++)
    {
        if (bank.accounts[i].balance < 0)
        {
            fprintf(stderr, "음수 잔액이 발생했습니다\n");
            goto cleanup;
        }
    }
    result = EXIT_SUCCESS;

cleanup:
    free(threads);
    free(workers);
    bank_destroy(&bank);
    return result;
}
