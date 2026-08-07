#include "owned_string.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECT(expression) do { \
    if (!(expression)) { \
        fprintf(stderr, "실패 %s:%d: %s\n", \
            __FILE__, __LINE__, #expression); \
        return 1; \
    } \
} while (0)

static size_t allocation_calls;
static size_t fail_at;
static size_t live_allocations;

static void *system_malloc(size_t size)
{
    return malloc(size);
}

static void *system_realloc(void *pointer, size_t size)
{
    return realloc(pointer, size);
}

static void system_free(void *pointer)
{
    free(pointer);
}

static void *failing_malloc(size_t size)
{
    void *result;

    allocation_calls++;
    if (allocation_calls == fail_at)
        return NULL;
    result = system_malloc(size);
    if (result != NULL)
        live_allocations++;
    return result;
}

static void *failing_realloc(void *pointer, size_t size)
{
    void *result;

    allocation_calls++;
    if (allocation_calls == fail_at)
        return NULL;
    result = system_realloc(pointer, size);
    if (result != NULL && pointer == NULL)
        live_allocations++;
    return result;
}

static void failing_free(void *pointer)
{
    if (pointer != NULL)
        live_allocations--;
    system_free(pointer);
}

#define malloc failing_malloc
#define realloc failing_realloc
#define free failing_free
#include "../src/owned_string.c"
#undef malloc
#undef realloc
#undef free

static void fail_next_allocation(void)
{
    fail_at = allocation_calls + 1;
}

static void allow_allocations(void)
{
    fail_at = 0;
}

int main(void)
{
    struct owned_string source;
    struct owned_string target;
    char *source_pointer;
    char *target_pointer;

    owned_string_init(&source);
    owned_string_init(&target);
    EXPECT(owned_string_set(&source, "alpha") == 0);
    source_pointer = source.data;
    fail_next_allocation();
    EXPECT(owned_string_set(&source, "replacement") == -1);
    EXPECT(source.data == source_pointer);
    EXPECT(strcmp(source.data, "alpha") == 0);
    EXPECT(source.length == 5);

    fail_next_allocation();
    EXPECT(owned_string_append(&source, "-a-long-suffix") == -1);
    EXPECT(source.data == source_pointer);
    EXPECT(strcmp(source.data, "alpha") == 0);
    EXPECT(source.length == 5);

    allow_allocations();
    EXPECT(owned_string_set(&target, "keep") == 0);
    target_pointer = target.data;
    fail_next_allocation();
    EXPECT(owned_string_clone(&source, &target) == -1);
    EXPECT(target.data == target_pointer);
    EXPECT(strcmp(target.data, "keep") == 0);

    allow_allocations();
    EXPECT(owned_string_append(&source, "-beta") == 0);
    EXPECT(strcmp(source.data, "alpha-beta") == 0);
    owned_string_destroy(&target);
    owned_string_destroy(&source);
    EXPECT(live_allocations == 0);
    puts("owned-string 할당 실패 검사: 통과");
    return 0;
}
