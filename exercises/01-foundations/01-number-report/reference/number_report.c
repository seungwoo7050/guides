#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

struct statistics
{
    size_t count;
    long minimum;
    long maximum;
    long sum;
    size_t even_count;
    size_t odd_count;
};

static int parse_long(const char *text, long *out_value)
{
    char *end;
    long value;

    if (text == NULL || out_value == NULL || *text == '\0' ||
        isspace((unsigned char)*text))
    {
        return -1;
    }
    errno = 0;
    end = NULL;
    value = strtol(text, &end, 10);
    if (errno == ERANGE || end == text || *end != '\0')
    {
        return -1;
    }
    *out_value = value;
    return 0;
}

static void statistics_init(struct statistics *stats)
{
    stats->count = 0;
    stats->minimum = 0;
    stats->maximum = 0;
    stats->sum = 0;
    stats->even_count = 0;
    stats->odd_count = 0;
}

static int sum_would_overflow(long sum, long value)
{
    return (value > 0 && sum > LONG_MAX - value) ||
           (value < 0 && sum < LONG_MIN - value);
}

static int statistics_add(struct statistics *stats, long value)
{
    if (sum_would_overflow(stats->sum, value))
    {
        return -1;
    }
    if (stats->count == 0)
    {
        stats->minimum = value;
        stats->maximum = value;
    }
    else
    {
        if (value < stats->minimum)
        {
            stats->minimum = value;
        }
        if (value > stats->maximum)
        {
            stats->maximum = value;
        }
    }
    stats->sum += value;
    stats->count++;
    if (value % 2 == 0)
    {
        stats->even_count++;
    }
    else
    {
        stats->odd_count++;
    }
    return 0;
}

static void print_report(const struct statistics *stats)
{
    double average = (double)stats->sum / (double)stats->count;

    printf("count=%zu\n", stats->count);
    printf("minimum=%ld\n", stats->minimum);
    printf("maximum=%ld\n", stats->maximum);
    printf("sum=%ld\n", stats->sum);
    printf("average=%.2f\n", average);
    printf("even=%zu\n", stats->even_count);
    printf("odd=%zu\n", stats->odd_count);
}

static void print_usage(const char *program)
{
    fprintf(stderr, "사용법: %s <정수> [정수 ...]\n", program);
}

int main(int argc, char *argv[])
{
    struct statistics stats;

    if (argc < 2)
    {
        print_usage(argv[0]);
        return 2;
    }
    statistics_init(&stats);
    for (int index = 1; index < argc; index++)
    {
        long value;

        if (parse_long(argv[index], &value) != 0)
        {
            fprintf(stderr, "오류: 정수가 아닙니다: %s\n", argv[index]);
            return 2;
        }
        if (statistics_add(&stats, value) != 0)
        {
            fprintf(stderr, "오류: 합이 long 범위를 넘습니다: %s\n", argv[index]);
            return 3;
        }
    }
    print_report(&stats);
    return 0;
}
