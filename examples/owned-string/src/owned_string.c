#include "owned_string.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static int add_overflows(size_t left, size_t right)
{
    return left > SIZE_MAX - right;
}

static int reserve(struct owned_string *string, size_t needed)
{
    size_t capacity;
    char *next;

    if (needed <= string->capacity)
        return 0;
    capacity = string->capacity == 0 ? 16 : string->capacity;
    while (capacity < needed)
    {
        if (capacity > SIZE_MAX / 2)
        {
            capacity = needed;
            break;
        }
        capacity *= 2;
    }
    next = realloc(string->data, capacity);
    if (next == NULL)
        return -1;
    string->data = next;
    string->capacity = capacity;
    return 0;
}

void owned_string_init(struct owned_string *string)
{
    string->data = NULL;
    string->length = 0;
    string->capacity = 0;
}

void owned_string_destroy(struct owned_string *string)
{
    if (string == NULL)
        return;
    free(string->data);
    owned_string_init(string);
}

int owned_string_set(struct owned_string *string, const char *text)
{
    size_t length;
    char *copy;

    if (string == NULL || text == NULL)
        return -1;
    length = strlen(text);
    if (length == SIZE_MAX)
        return -1;
    copy = malloc(length + 1);
    if (copy == NULL)
        return -1;
    memcpy(copy, text, length + 1);
    free(string->data);
    string->data = copy;
    string->length = length;
    string->capacity = length + 1;
    return 0;
}

int owned_string_append(struct owned_string *string, const char *suffix)
{
    size_t suffix_length;
    size_t needed;

    if (string == NULL || suffix == NULL)
        return -1;
    suffix_length = strlen(suffix);
    if (add_overflows(string->length, suffix_length) ||
        add_overflows(string->length + suffix_length, 1))
        return -1;
    needed = string->length + suffix_length + 1;
    if (reserve(string, needed) != 0)
        return -1;
    memcpy(string->data + string->length, suffix, suffix_length + 1);
    string->length += suffix_length;
    return 0;
}

int owned_string_clone(const struct owned_string *source, struct owned_string *out)
{
    struct owned_string temporary;

    if (source == NULL || out == NULL)
        return -1;
    owned_string_init(&temporary);
    if (owned_string_set(&temporary, source->data != NULL ? source->data : "") != 0)
        return -1;
    owned_string_destroy(out);
    *out = temporary;
    return 0;
}

char *owned_string_release(struct owned_string *string)
{
    char *data;

    if (string == NULL)
        return NULL;
    data = string->data;
    owned_string_init(string);
    return data;
}
