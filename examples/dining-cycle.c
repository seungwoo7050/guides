#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

enum { DINER_COUNT = 5 };

typedef struct s_table {
    pthread_mutex_t forks[DINER_COUNT];
    pthread_mutex_t start_mutex;
    pthread_cond_t start_condition;
    int start;
    int abort;
    unsigned long meals[DINER_COUNT];
    unsigned long rounds;
} t_table;

typedef struct s_diner {
    t_table *table;
    int id;
} t_diner;

static int wait_for_start(t_table *table)
{
    int should_abort;

    if (pthread_mutex_lock(&table->start_mutex) != 0)
        return -1;
    while (table->start == 0 && table->abort == 0) {
        if (pthread_cond_wait(&table->start_condition, &table->start_mutex) != 0) {
            (void)pthread_mutex_unlock(&table->start_mutex);
            return -1;
        }
    }
    should_abort = table->abort;
    if (pthread_mutex_unlock(&table->start_mutex) != 0)
        return -1;
    return should_abort != 0 ? 1 : 0;
}

static void *diner_main(void *argument)
{
    t_diner *diner;
    t_table *table;
    int left;
    int right;
    int first;
    int second;
    unsigned long round;
    int start_status;

    diner = argument;
    table = diner->table;
    start_status = wait_for_start(table);
    if (start_status != 0)
        return start_status > 0 ? NULL : (void *)1;
    left = diner->id;
    right = (diner->id + 1) % DINER_COUNT;
    first = left < right ? left : right;
    second = left < right ? right : left;
    round = 0UL;
    while (round < table->rounds) {
        if (pthread_mutex_lock(&table->forks[first]) != 0)
            return (void *)1;
        if (pthread_mutex_lock(&table->forks[second]) != 0) {
            (void)pthread_mutex_unlock(&table->forks[first]);
            return (void *)1;
        }
        table->meals[diner->id] += 1UL;
        (void)pthread_mutex_unlock(&table->forks[second]);
        (void)pthread_mutex_unlock(&table->forks[first]);
        round += 1UL;
    }
    return NULL;
}

static int table_init(t_table *table, unsigned long rounds)
{
    int index;

    table->start = 0;
    table->abort = 0;
    table->rounds = rounds;
    index = 0;
    while (index < DINER_COUNT) {
        table->meals[index] = 0UL;
        if (pthread_mutex_init(&table->forks[index], NULL) != 0) {
            while (--index >= 0)
                (void)pthread_mutex_destroy(&table->forks[index]);
            return -1;
        }
        index += 1;
    }
    if (pthread_mutex_init(&table->start_mutex, NULL) != 0) {
        index = 0;
        while (index < DINER_COUNT) {
            (void)pthread_mutex_destroy(&table->forks[index]);
            index += 1;
        }
        return -1;
    }
    if (pthread_cond_init(&table->start_condition, NULL) != 0) {
        (void)pthread_mutex_destroy(&table->start_mutex);
        index = 0;
        while (index < DINER_COUNT) {
            (void)pthread_mutex_destroy(&table->forks[index]);
            index += 1;
        }
        return -1;
    }
    return 0;
}

static void table_destroy(t_table *table)
{
    int index;

    (void)pthread_cond_destroy(&table->start_condition);
    (void)pthread_mutex_destroy(&table->start_mutex);
    index = 0;
    while (index < DINER_COUNT) {
        (void)pthread_mutex_destroy(&table->forks[index]);
        index += 1;
    }
}

static int release_start(t_table *table, int abort)
{
    if (pthread_mutex_lock(&table->start_mutex) != 0)
        return -1;
    table->abort = abort;
    table->start = 1;
    (void)pthread_cond_broadcast(&table->start_condition);
    return pthread_mutex_unlock(&table->start_mutex) == 0 ? 0 : -1;
}

static int parse_rounds(const char *text, unsigned long *value)
{
    char *end;
    unsigned long parsed;

    end = NULL;
    parsed = strtoul(text, &end, 10);
    if (text[0] == '\0' || end == NULL || *end != '\0' || parsed == 0UL || parsed > 1000000UL)
        return -1;
    *value = parsed;
    return 0;
}

int main(int argc, char **argv)
{
    t_table table;
    t_diner diners[DINER_COUNT];
    pthread_t threads[DINER_COUNT];
    unsigned long rounds;
    int created;
    int index;
    int result;
    void *status;

    rounds = 1000UL;
    if (argc > 1 && parse_rounds(argv[1], &rounds) != 0) {
        fprintf(stderr, "사용법: %s [rounds:1..1000000]\n", argv[0]);
        return 2;
    }
    if (table_init(&table, rounds) != 0) {
        fprintf(stderr, "테이블 초기화에 실패했습니다.\n");
        return 1;
    }
    created = 0;
    while (created < DINER_COUNT) {
        diners[created].table = &table;
        diners[created].id = created;
        if (pthread_create(&threads[created], NULL, diner_main, &diners[created]) != 0)
            break;
        created += 1;
    }
    if (created != DINER_COUNT) {
        (void)release_start(&table, 1);
        index = 0;
        while (index < created) {
            (void)pthread_join(threads[index], NULL);
            index += 1;
        }
        table_destroy(&table);
        fprintf(stderr, "스레드를 만들지 못했습니다.\n");
        return 1;
    }
    if (release_start(&table, 0) != 0) {
        table_destroy(&table);
        fprintf(stderr, "시작 게이트 동기화에 실패했습니다.\n");
        return 1;
    }
    result = 0;
    index = 0;
    while (index < DINER_COUNT) {
        status = NULL;
        if (pthread_join(threads[index], &status) != 0 || status != NULL)
            result = 1;
        index += 1;
    }
    index = 0;
    while (index < DINER_COUNT) {
        if (table.meals[index] != rounds)
            result = 1;
        index += 1;
    }
    printf("diners=%d rounds=%lu all_completed=%s lock_order=lower-first\n",
        DINER_COUNT,
        rounds,
        result == 0 ? "yes" : "no");
    table_destroy(&table);
    return result;
}
