#ifndef LINE_READER_H
#define LINE_READER_H

#include <stddef.h>

enum line_status
{
    LINE_OK,
    LINE_EOF,
    LINE_IO_ERROR,
    LINE_NO_MEMORY,
    LINE_OVERFLOW,
    LINE_INVALID
};

struct line
{
    unsigned char *data;
    size_t length;
};

struct line_reader
{
    int fd;
    unsigned char *buffer;
    size_t begin;
    size_t scan;
    size_t end;
    size_t capacity;
    size_t chunk_size;
    int eof_seen;
    enum line_status terminal;
};

int line_reader_init(struct line_reader *reader, int fd, size_t chunk_size);
void line_reader_destroy(struct line_reader *reader);
enum line_status line_reader_next(struct line_reader *reader, struct line *out);
void line_destroy(struct line *line);

#endif
