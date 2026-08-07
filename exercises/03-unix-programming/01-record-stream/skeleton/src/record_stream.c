#include "record_stream.h"

void record_reader_init(
    struct record_reader *reader,
    int fd,
    const struct record_reader_allocator *allocator
)
{
    (void)allocator;
    if (reader != NULL)
    {
        reader->fd = fd;
        reader->pending = NULL;
        reader->length = 0;
        reader->capacity = 0;
        reader->eof = 0;
        reader->failed = 0;
        reader->allocator.context = NULL;
        reader->allocator.resize = NULL;
        reader->allocator.release = NULL;
    }
}

int record_reader_next(
    struct record_reader *reader,
    char **out_record,
    size_t *out_length
)
{
    (void)reader;
    (void)out_record;
    (void)out_length;
    return -1;
}

void record_reader_destroy(struct record_reader *reader)
{
    (void)reader;
}
