#include "textkit.h"

#include <stdio.h>

int main(int argc, char *argv[])
{
    if (argc != 2)
    {
        fprintf(stderr, "사용법: %s <텍스트>\n", argv[0]);
        return 2;
    }
    printf("length=%zu\n", textkit_length(argv[1]));
    printf("words=%zu\n", textkit_word_count(argv[1]));
    return 0;
}
