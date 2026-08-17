#include "textkit.h"

#include <stdio.h>

/* [Implementation 5] CLI composition */
int main(int argc, char *argv[])
{
    if (argc != 2)
    {
        fprintf(stderr, "Usage: %s <text>\n", argv[0]);
        return 2;
    }
    printf("length=%zu\n", textkit_length(argv[1]));
    printf("words=%zu\n", textkit_word_count(argv[1]));
    return 0;
}
