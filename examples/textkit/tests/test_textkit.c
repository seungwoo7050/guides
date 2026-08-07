#include "textkit.h"

#include <stdio.h>

#define EXPECT(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "실패 %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return 1; \
    } \
} while (0)

int main(void)
{
    EXPECT(text_length("") == 0);
    EXPECT(text_length("hello") == 5);
    EXPECT(text_count_char("banana", 'a') == 3);
    EXPECT(text_count_char("banana", 'x') == 0);
    puts("textkit 단위 검사: 통과");
    return 0;
}
