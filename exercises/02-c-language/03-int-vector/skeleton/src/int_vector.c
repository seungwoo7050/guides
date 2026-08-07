#include "int_vector.h"

void int_vector_init(
    struct int_vector *vector,
    const struct int_vector_allocator *allocator
)
{
    (void)allocator;
    if (vector != NULL)
    {
        vector->data = NULL;
        vector->size = 0;
        vector->capacity = 0;
        vector->allocator.context = NULL;
        vector->allocator.resize = NULL;
        vector->allocator.release = NULL;
    }
}

int int_vector_push(struct int_vector *vector, int value)
{
    (void)vector;
    (void)value;
    return -1;
}

int int_vector_get(const struct int_vector *vector, size_t index, int *out_value)
{
    (void)vector;
    (void)index;
    (void)out_value;
    return -1;
}

void int_vector_destroy(struct int_vector *vector)
{
    (void)vector;
}
