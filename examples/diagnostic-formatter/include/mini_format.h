#ifndef MINI_FORMAT_H
#define MINI_FORMAT_H

#include <stdarg.h>
#include <stddef.h>

int mini_vsnprintf(char *buffer, size_t capacity, const char *format, va_list args);
int mini_snprintf(char *buffer, size_t capacity, const char *format, ...);

#endif
