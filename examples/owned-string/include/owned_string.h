#ifndef OWNED_STRING_H
#define OWNED_STRING_H

#include <stddef.h>

struct owned_string
{
    char *data;
    size_t length;
    size_t capacity;
};

void owned_string_init(struct owned_string *string);
void owned_string_destroy(struct owned_string *string);
int owned_string_set(struct owned_string *string, const char *text);
int owned_string_append(struct owned_string *string, const char *suffix);
int owned_string_clone(const struct owned_string *source, struct owned_string *out);
char *owned_string_release(struct owned_string *string);

#endif
