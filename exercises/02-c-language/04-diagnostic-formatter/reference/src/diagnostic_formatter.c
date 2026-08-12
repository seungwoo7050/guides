#include "diagnostic_formatter.h"

#include <limits.h>
#include <stdint.h>

/* [Implementation 1] 논리 길이와 실제 기록 위치를 하나의 출력 상태가 소유한다. */
struct output
{
    char *buffer;
    size_t capacity;
    size_t length;
    int failed;
};

static void output_char(struct output *output, char value)
{
    if (output->failed)
    {
        return;
    }
    if (output->length == SIZE_MAX)
    {
        output->failed = 1;
        return;
    }
    if (output->capacity > 0 && output->length < output->capacity - 1)
    {
        output->buffer[output->length] = value;
    }
    output->length++;
}

/* [Implementation 2] 문자열과 정수를 동일한 단일 문자 출력 경계로 보낸다. */
static void output_text(struct output *output, const char *text)
{
    if (text == NULL)
    {
        text = "(null)";
    }
    while (*text != '\0')
    {
        output_char(output, *text);
        text++;
    }
}

static void output_unsigned(struct output *output, unsigned int value)
{
    char digits[sizeof value * CHAR_BIT];
    size_t count = 0;

    do
    {
        digits[count++] = (char)('0' + value % 10u);
        value /= 10u;
    } while (value != 0u);
    while (count > 0)
    {
        output_char(output, digits[--count]);
    }
}

static void output_int(struct output *output, int value)
{
    unsigned int magnitude;

    if (value < 0)
    {
        output_char(output, '-');
        magnitude = 0u - (unsigned int)value;
    }
    else
    {
        magnitude = (unsigned int)value;
    }
    output_unsigned(output, magnitude);
}

/* [Implementation 3] capacity 안에서 가능한 마지막 위치에 NUL을 확정한다. */
static void finish_output(struct output *output)
{
    size_t index;

    if (output->capacity == 0 || output->buffer == NULL)
    {
        return;
    }
    index = output->length;
    if (index >= output->capacity)
    {
        index = output->capacity - 1;
    }
    output->buffer[index] = '\0';
}

/* [Implementation 4] 복사한 va_list로 형식을 해석하고 실패도 한곳에서 끝낸다. */
int diagnostic_vformat(
    char *buffer,
    size_t capacity,
    const char *format,
    va_list arguments
)
{
    struct output output = {buffer, capacity, 0, 0};
    va_list copy;

    if (format == NULL || (capacity > 0 && buffer == NULL))
    {
        return -1;
    }
    va_copy(copy, arguments);
    while (*format != '\0' && !output.failed)
    {
        if (*format != '%')
        {
            output_char(&output, *format++);
            continue;
        }
        format++;
        if (*format == '%')
        {
            output_char(&output, '%');
        }
        else if (*format == 's')
        {
            output_text(&output, va_arg(copy, const char *));
        }
        else if (*format == 'd')
        {
            output_int(&output, va_arg(copy, int));
        }
        else
        {
            output.failed = 1;
            break;
        }
        format++;
    }
    va_end(copy);
    finish_output(&output);
    if (output.failed || output.length > (size_t)INT_MAX)
    {
        return -1;
    }
    return (int)output.length;
}

/* [Implementation 5] variadic wrapper가 va_list의 시작과 종료를 소유한다. */
int diagnostic_format(
    char *buffer,
    size_t capacity,
    const char *format,
    ...
)
{
    int result;
    va_list arguments;

    va_start(arguments, format);
    result = diagnostic_vformat(buffer, capacity, format, arguments);
    va_end(arguments);
    return result;
}
