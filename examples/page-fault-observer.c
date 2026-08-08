#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <unistd.h>

static long minor_faults(void)
{
    struct rusage usage;

    if (getrusage(RUSAGE_SELF, &usage) != 0)
        return -1L;
    return usage.ru_minflt;
}

int main(int argc, char **argv)
{
    long page_size;
    long pages;
    char *memory;
    long before;
    long after;
    long index;
    char *end;

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
    before = minor_faults();
    index = 0L;
    while (index < pages) {
        memory[index * page_size] = (char)(index & 0x7fL);
        index += 1L;
    }
    after = minor_faults();
    if (before < 0L || after < 0L) {
        perror("getrusage");
        free(memory);
        return 1;
    }
    printf("page_size=%ld touched_pages=%ld minor_fault_delta=%ld\n",
        page_size,
        pages,
        after - before);
    free(memory);
    return 0;
}
