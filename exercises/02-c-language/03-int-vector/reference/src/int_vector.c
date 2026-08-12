#include "int_vector.h"

#include <stdint.h>
#include <stdlib.h>

static void *default_resize(void *context, void *pointer, size_t size)
{
    (void)context;
    return realloc(pointer, size);
}

static void default_release(void *context, void *pointer)
{
    (void)context;
    free(pointer);
}

/* [Implementation 1] allocator와 빈 vector의 소유 상태를 초기화한다. */
void int_vector_init(
    struct int_vector *vector,
    const struct int_vector_allocator *allocator
)
{
    if (vector == NULL)
    {
        return;
    }
    vector->data = NULL;
    vector->size = 0;
    vector->capacity = 0;
    if (allocator != NULL)
    {
        vector->allocator = *allocator;
    }
    else
    {
        vector->allocator.context = NULL;
        vector->allocator.resize = default_resize;
        vector->allocator.release = default_release;
    }
}

/* [Implementation 2] buffer와 length/capacity의 shape 불변식을 확인한다. */
static int int_vector_has_valid_shape(const struct int_vector *vector)
{
    if (vector->capacity == 0)
    {
        return vector->data == NULL && vector->size == 0;
    }
    return vector->data != NULL && vector->size <= vector->capacity;
}

/* [Implementation 3] 크기를 선검증하고 resize 성공 뒤 원소를 commit한다. */
int int_vector_push(struct int_vector *vector, int value)
{
    if (vector == NULL || vector->allocator.resize == NULL ||
        vector->allocator.release == NULL ||
        !int_vector_has_valid_shape(vector))
    {
        return -1;
    }
    if (vector->size == vector->capacity)
    {
        size_t new_capacity;
        int *resized;

        if (vector->capacity == 0)
        {
            new_capacity = 4;
        }
        else
        {
            if (vector->capacity > SIZE_MAX / 2)
            {
                return -1;
            }
            new_capacity = vector->capacity * 2;
        }
        if (new_capacity > SIZE_MAX / sizeof *vector->data)
        {
            return -1;
        }
        resized = vector->allocator.resize(
            vector->allocator.context,
            vector->data,
            new_capacity * sizeof *vector->data
        );
        if (resized == NULL)
        {
            return -1;
        }
        vector->data = resized;
        vector->capacity = new_capacity;
    }
    vector->data[vector->size] = value;
    vector->size++;
    return 0;
}

/* [Implementation 4] 범위 검증이 끝난 뒤에만 조회 결과를 commit한다. */
int int_vector_get(const struct int_vector *vector, size_t index, int *out_value)
{
    if (vector == NULL || out_value == NULL ||
        !int_vector_has_valid_shape(vector) || index >= vector->size)
    {
        return -1;
    }
    *out_value = vector->data[index];
    return 0;
}

/* [Implementation 5] owned buffer를 해제하고 반복 정리 가능한 빈 상태로 만든다. */
void int_vector_destroy(struct int_vector *vector)
{
    if (vector == NULL)
    {
        return;
    }
    if (vector->allocator.release != NULL && vector->data != NULL)
    {
        vector->allocator.release(vector->allocator.context, vector->data);
    }
    vector->data = NULL;
    vector->size = 0;
    vector->capacity = 0;
}
