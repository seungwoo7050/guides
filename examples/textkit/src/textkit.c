#include "textkit.h"

size_t text_length(const char *text)
{
    size_t length = 0;

    while (text[length] != '\0')
        length++;
    return length;
}

size_t text_count_char(const char *text, char target)
{
    size_t count = 0;
    size_t index = 0;

    while (text[index] != '\0')
    {
        if (text[index] == target)
            count++;
        index++;
    }
    return count;
}
