#include "textkit.h"

#include <stdio.h>
#include <stdlib.h>

static void usage(const char *program)
{
    fprintf(stderr, "사용법: %s <문자열> [문자]\n", program);
}

int main(int argc, char **argv)
{
    if (argc < 2 || argc > 3)
    {
        usage(argv[0]);
        return EXIT_FAILURE;
    }
    if (argc == 3 && (argv[2][0] == '\0' || argv[2][1] != '\0'))
    {
        fprintf(stderr, "오류: 문자는 한 바이트여야 합니다\n");
        return EXIT_FAILURE;
    }
    printf("length: %zu\n", text_length(argv[1]));
    if (argc == 3)
        printf("count: %zu\n", text_count_char(argv[1], argv[2][0]));
    return EXIT_SUCCESS;
}
