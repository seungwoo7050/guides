#include "textkit.h"

#include <ctype.h>

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
