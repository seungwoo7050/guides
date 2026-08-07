#include "diagnostic_formatter.h"

int diagnostic_vformat(
    char *buffer,
    size_t capacity,
    const char *format,
    va_list arguments
)
{
    (void)buffer;
    (void)capacity;
    (void)format;
    (void)arguments;
    return -1;
}

int diagnostic_format(
    char *buffer,
    size_t capacity,
    const char *format,
    ...
)
{
    (void)buffer;
    (void)capacity;
    (void)format;
    return -1;
}
