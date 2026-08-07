#include "owned_string.h"

void owned_string_init(
    struct owned_string *string,
    const struct owned_string_allocator *allocator
)
{
    (void)allocator;
    if (string != NULL)
    {
        string->data = NULL;
        string->length = 0;
        string->capacity = 0;
        string->allocator.context = NULL;
        string->allocator.resize = NULL;
        string->allocator.release = NULL;
    }
}

int owned_string_append(struct owned_string *string, const char *source)
{
    (void)string;
    (void)source;
    return -1;
}

void owned_string_destroy(struct owned_string *string)
{
    (void)string;
}
