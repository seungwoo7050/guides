#include "textkit.h"

#include <ctype.h>

/* [Implementation 1] NULL을 빈 입력으로 취급하는 길이 탐색 경계를 먼저 고정한다. */
size_t textkit_length(const char *text)
{
    size_t length = 0;

    if (text == NULL)
    {
        return 0;
    }
    while (text[length] != '\0')
    {
        length++;
    }
    return length;
}

/* [Implementation 2] 같은 순회 정책으로 요청한 byte의 출현 수를 센다. */
size_t textkit_count_char(const char *text, char needle)
{
    size_t count = 0;

    if (text == NULL)
    {
        return 0;
    }
    while (*text != '\0')
    {
        if (*text == needle)
        {
            count++;
        }
        text++;
    }
    return count;
}

/* [Implementation 3] 공백 경계에서만 단어 상태를 전환해 논리 단위를 센다. */
size_t textkit_word_count(const char *text)
{
    size_t count = 0;
    int inside_word = 0;

    if (text == NULL)
    {
        return 0;
    }
    while (*text != '\0')
    {
        int separator = isspace((unsigned char)*text);

        if (!separator && !inside_word)
        {
            count++;
            inside_word = 1;
        }
        else if (separator)
        {
            inside_word = 0;
        }
        text++;
    }
    return count;
}
