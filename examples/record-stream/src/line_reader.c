#include "line_reader.h"

#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void reset_storage(struct line_reader *reader)
{
    reader->begin = 0;
    reader->scan = 0;
    reader->end = 0;
}

static enum line_status fail_terminal(
    struct line_reader *reader,
    enum line_status status
)
{
    free(reader->buffer);
    reader->buffer = NULL;
    reader->capacity = 0;
    reset_storage(reader);
    reader->terminal = status;
    return status;
}

static int compact(struct line_reader *reader)
{
    size_t remaining;

    if (reader->begin == 0)
        return 0;
    remaining = reader->end - reader->begin;
    memmove(reader->buffer, reader->buffer + reader->begin, remaining);
    reader->scan -= reader->begin;
    reader->begin = 0;
    reader->end = remaining;
    return 0;
}

static enum line_status reserve_tail(struct line_reader *reader, size_t extra)
{
    size_t needed;
    size_t capacity;
    unsigned char *next;

    if (reader->capacity - reader->end >= extra)
        return LINE_OK;
    compact(reader);
    if (reader->capacity - reader->end >= extra)
        return LINE_OK;
    if (reader->end > SIZE_MAX - extra)
        return fail_terminal(reader, LINE_OVERFLOW);
    needed = reader->end + extra;
    capacity = reader->capacity == 0 ? reader->chunk_size : reader->capacity;
    while (capacity < needed)
    {
        if (capacity > SIZE_MAX / 2)
        {
            capacity = needed;
            break;
        }
        capacity *= 2;
    }
    next = realloc(reader->buffer, capacity);
    if (next == NULL)
        return fail_terminal(reader, LINE_NO_MEMORY);
    reader->buffer = next;
    reader->capacity = capacity;
    return LINE_OK;
}

static enum line_status make_line(
    struct line_reader *reader,
    size_t finish,
    struct line *out
)
{
    size_t length = finish - reader->begin;
    unsigned char *data;

    if (length == SIZE_MAX)
        return fail_terminal(reader, LINE_OVERFLOW);
    data = malloc(length + 1);
    if (data == NULL)
        return fail_terminal(reader, LINE_NO_MEMORY);
    memcpy(data, reader->buffer + reader->begin, length);
    data[length] = '\0';
    out->data = data;
    out->length = length;
    reader->begin = finish;
    reader->scan = finish;
    if (reader->begin == reader->end)
        reset_storage(reader);
    return LINE_OK;
}

int line_reader_init(struct line_reader *reader, int fd, size_t chunk_size)
{
    if (reader == NULL || fd < 0 || chunk_size == 0)
        return -1;
    reader->fd = fd;
    reader->buffer = NULL;
    reader->begin = 0;
    reader->scan = 0;
    reader->end = 0;
    reader->capacity = 0;
    reader->chunk_size = chunk_size;
    reader->eof_seen = 0;
    reader->terminal = LINE_OK;
    return 0;
}

void line_reader_destroy(struct line_reader *reader)
{
    if (reader == NULL)
        return;
    free(reader->buffer);
    reader->buffer = NULL;
    reader->capacity = 0;
    reset_storage(reader);
    reader->terminal = LINE_EOF;
}

void line_destroy(struct line *line)
{
    if (line == NULL)
        return;
    free(line->data);
    line->data = NULL;
    line->length = 0;
}

enum line_status line_reader_next(struct line_reader *reader, struct line *out)
{
    enum line_status status;

    if (reader == NULL || out == NULL)
        return LINE_INVALID;
    out->data = NULL;
    out->length = 0;
    if (reader->terminal != LINE_OK)
        return reader->terminal;
    while (1)
    {
        while (reader->scan < reader->end)
        {
            if (reader->buffer[reader->scan] == '\n')
                return make_line(reader, reader->scan + 1, out);
            reader->scan++;
        }
        if (reader->eof_seen)
        {
            if (reader->begin < reader->end)
                return make_line(reader, reader->end, out);
            reader->terminal = LINE_EOF;
            return LINE_EOF;
        }
        status = reserve_tail(reader, reader->chunk_size);
        if (status != LINE_OK)
            return status;
        while (1)
        {
            ssize_t n = read(
                reader->fd,
                reader->buffer + reader->end,
                reader->chunk_size
            );

            if (n > 0)
            {
                reader->end += (size_t)n;
                break;
            }
            if (n == 0)
            {
                reader->eof_seen = 1;
                break;
            }
            if (errno != EINTR)
                return fail_terminal(reader, LINE_IO_ERROR);
        }
    }
}
