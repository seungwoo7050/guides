#include "textkit.h"

#include <stdio.h>

#define CHECK(expression)                                                   \
    do                                                                      \
    {                                                                       \
        if (!(expression))                                                  \
        {                                                                   \
            fprintf(stderr, "%s:%d: check failed: %s\n",                  \
                    __FILE__, __LINE__, #expression);                       \
            return 1;                                                       \
        }                                                                   \
    } while (0)

int main(void)
{
    CHECK(textkit_length(NULL) == 0);
    CHECK(textkit_length("") == 0);
    CHECK(textkit_length("hello") == 5);
    CHECK(textkit_count_char(NULL, 'x') == 0);
    CHECK(textkit_count_char("banana", 'a') == 3);
    CHECK(textkit_count_char("banana", 'x') == 0);
    CHECK(textkit_count_char("aaa", 'a') == 3);
    CHECK(textkit_count_char("", '\0') == 0);
    CHECK(textkit_word_count(NULL) == 0);
    CHECK(textkit_word_count("") == 0);
    CHECK(textkit_word_count("   \t\n\r\v\f") == 0);
    CHECK(textkit_word_count("one") == 1);
    CHECK(textkit_word_count(" one  two\tthree\n") == 3);
    CHECK(textkit_word_count("a-b c_d") == 2);
    {
        const char high_bytes[] = {(char)0xff, 'x', '\0'};

        CHECK(textkit_length(high_bytes) == 2);
        CHECK(textkit_word_count(high_bytes) == 1);
    }
    puts("textkit tests passed");
    return 0;
}
