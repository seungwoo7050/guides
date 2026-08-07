#include "owned_string.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECT(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "실패 %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return 1; \
    } \
} while (0)

static int valid(const struct owned_string *s)
{
    if (s->data == NULL)
        return s->length == 0 && s->capacity == 0;
    return s->length < s->capacity && s->data[s->length] == '\0';
}

int main(void)
{
    struct owned_string a;
    struct owned_string b;
    char *released;

    owned_string_init(&a);
    owned_string_init(&b);
    EXPECT(valid(&a));
    EXPECT(owned_string_set(&a, "alpha") == 0);
    EXPECT(owned_string_append(&a, "-beta") == 0);
    EXPECT(strcmp(a.data, "alpha-beta") == 0);
    EXPECT(a.length == strlen("alpha-beta"));
    EXPECT(valid(&a));

    EXPECT(owned_string_clone(&a, &b) == 0);
    EXPECT(strcmp(a.data, b.data) == 0);
    EXPECT(a.data != b.data);
    EXPECT(owned_string_set(&a, "changed") == 0);
    EXPECT(strcmp(b.data, "alpha-beta") == 0);

    released = owned_string_release(&b);
    EXPECT(released != NULL);
    EXPECT(valid(&b));
    EXPECT(strcmp(released, "alpha-beta") == 0);
    free(released);

    owned_string_destroy(&a);
    owned_string_destroy(&a);
    owned_string_destroy(&b);
    puts("owned-string 검사: 통과");
    return 0;
}
