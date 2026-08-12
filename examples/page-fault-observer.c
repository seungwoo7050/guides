#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <unistd.h>

/* [Implementation 1] getrusage의 process 통계는 관찰 경계일 뿐, 어떤 접근이 fault를 만들었는지 자체로 증명하지 않습니다. */
static long minor_faults(void)
{
    struct rusage usage;

    if (getrusage(RUSAGE_SELF, &usage) != 0)
        return -1L;
    return usage.ru_minflt;
}

/* [Implementation 2] 입력 상한, page 크기와 곱셈 overflow를 먼저 고정해 allocation의 크기와 회수 책임을 명확히 합니다. */
int main(int argc, char **argv)
{
    long page_size;
    long pages;
    char *memory;
    long before;
    long after;
    long index;
    char *end;
    volatile unsigned char *memory_view;
    uint64_t touch_checksum;

    pages = 4096L;
    if (argc > 1) {
        end = NULL;
        pages = strtol(argv[1], &end, 10);
        if (argv[1][0] == '\0' || end == NULL || *end != '\0' || pages <= 0L || pages > 1000000L) {
            fprintf(stderr, "사용법: %s [pages:1..1000000]\n", argv[0]);
            return 2;
        }
    }
    page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0L) {
        fprintf(stderr, "페이지 크기를 확인할 수 없습니다.\n");
        return 1;
    }
    if ((unsigned long)pages > (unsigned long)(SIZE_MAX / (size_t)page_size)) {
        fprintf(stderr, "요청한 매핑이 너무 큽니다.\n");
        return 1;
    }
    memory = calloc((size_t)pages, (size_t)page_size);
    if (memory == NULL) {
        perror("calloc");
        return 1;
    }

    /* [Implementation 3] volatile page view는 page별 첫 write가 -O2에서도 실제 접근으로 남게 하며 checksum은 그 접근을 출력 계약에 연결합니다. */
    memory_view = (volatile unsigned char *)memory;
    before = minor_faults();
    index = 0L;
    touch_checksum = 0U;
    while (index < pages) {
        unsigned char value;

        value = (unsigned char)((index % 251L) + 1L);
        memory_view[index * page_size] = value;
        touch_checksum += memory_view[index * page_size];
        index += 1L;
    }
    after = minor_faults();
    if (before < 0L || after < 0L) {
        perror("getrusage");
        free(memory);
        return 1;
    }
    printf("page_size=%ld touched_pages=%ld touch_checksum=%" PRIu64
        " minor_fault_delta=%ld\n",
        page_size,
        pages,
        touch_checksum,
        after - before);
    free(memory);
    return 0;
}
