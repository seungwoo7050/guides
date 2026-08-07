#include "mini_format.h"

#include <limits.h>
#include <stdint.h>
#include <string.h>

struct output
{
    char *buffer;
    size_t capacity;
    size_t length;
    int failed;
};

static void emit_byte(struct output *out, unsigned char byte)
{
    if (out->length == SIZE_MAX)
    {
        out->failed = 1;
        return;
    }
    if (out->buffer != NULL && out->capacity > 0 && out->length + 1 < out->capacity)
        out->buffer[out->length] = (char)byte;
    out->length++;
}

static void emit_data(struct output *out, const char *data, size_t length)
{
    size_t i = 0;

    while (i < length && !out->failed)
    {
        emit_byte(out, (unsigned char)data[i]);
        i++;
    }
}

static void emit_unsigned(struct output *out, unsigned int value)
{
    char digits[sizeof(unsigned int) * CHAR_BIT];
    size_t length = 0;

    do
    {
        digits[length++] = (char)('0' + value % 10u);
        value /= 10u;
    }
    while (value != 0u);
    while (length > 0)
        emit_byte(out, (unsigned char)digits[--length]);
}

static void emit_int(struct output *out, int value)
{
    unsigned int magnitude;

    if (value < 0)
    {
        emit_byte(out, '-');
        magnitude = 0u - (unsigned int)value;
    }
    else
        magnitude = (unsigned int)value;
    emit_unsigned(out, magnitude);
}

static int render(struct output *out, const char *format, va_list args)
{
    size_t i = 0;

    while (format[i] != '\0' && !out->failed)
    {
        if (format[i] != '%')
        {
            emit_byte(out, (unsigned char)format[i++]);
            continue;
        }
        i++;
        if (format[i] == '\0')
            return -1;
        if (format[i] == '%')
            emit_byte(out, '%');
        else if (format[i] == 'c')
            emit_byte(out, (unsigned char)va_arg(args, int));
        else if (format[i] == 'd')
            emit_int(out, va_arg(args, int));
        else if (format[i] == 's')
        {
            const char *text = va_arg(args, const char *);
            if (text == NULL)
                text = "(null)";
            emit_data(out, text, strlen(text));
        }
        else
            return -1;
        i++;
    }
    return out->failed ? -1 : 0;
}

int mini_vsnprintf(char *buffer, size_t capacity, const char *format, va_list args)
{
    struct output measure = {NULL, 0, 0, 0};
    struct output write_out = {buffer, capacity, 0, 0};
    va_list measure_args;
    va_list write_args;
    int result = -1;

    if (format == NULL || (capacity > 0 && buffer == NULL))
        return -1;
    va_copy(measure_args, args);
    if (render(&measure, format, measure_args) != 0 || measure.length > (size_t)INT_MAX)
    {
        va_end(measure_args);
        if (buffer != NULL && capacity > 0)
            buffer[0] = '\0';
        return -1;
    }
    va_end(measure_args);

    va_copy(write_args, args);
    if (render(&write_out, format, write_args) == 0)
        result = (int)measure.length;
    va_end(write_args);

    if (buffer != NULL && capacity > 0)
    {
        size_t end = write_out.length < capacity ? write_out.length : capacity - 1;
        buffer[end] = '\0';
    }
    return result;
}

int mini_snprintf(char *buffer, size_t capacity, const char *format, ...)
{
    va_list args;
    int result;

    va_start(args, format);
    result = mini_vsnprintf(buffer, capacity, format, args);
    va_end(args);
    return result;
}
