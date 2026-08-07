#include "line_reader.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define EXPECT(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "실패 %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return 1; \
    } \
} while (0)

static int write_all(int fd, const unsigned char *data, size_t length)
{
    size_t offset = 0;

    while (offset < length)
    {
        ssize_t n = write(fd, data + offset, length - offset);
        if (n <= 0)
            return -1;
        offset += (size_t)n;
    }
    return 0;
}

static int pipe_with_data(const unsigned char *data, size_t length, int *read_fd)
{
    int fds[2];

    if (pipe(fds) != 0)
        return -1;
    if (write_all(fds[1], data, length) != 0)
    {
        close(fds[0]);
        close(fds[1]);
        return -1;
    }
    close(fds[1]);
    *read_fd = fds[0];
    return 0;
}

static int expect_line(
    struct line_reader *reader,
    const unsigned char *data,
    size_t length
)
{
    struct line line;
    enum line_status status = line_reader_next(reader, &line);

    EXPECT(status == LINE_OK);
    EXPECT(line.length == length);
    EXPECT(memcmp(line.data, data, length) == 0);
    line_destroy(&line);
    return 0;
}

static int basic_cases(void)
{
    static const unsigned char input[] = "a\nbb\nlast";
    struct line_reader reader;
    struct line first;
    struct line second;
    int fd;

    EXPECT(pipe_with_data(input, sizeof input - 1, &fd) == 0);
    EXPECT(line_reader_init(&reader, fd, 2) == 0);
    EXPECT(line_reader_next(&reader, &first) == LINE_OK);
    EXPECT(first.length == 2 && memcmp(first.data, "a\n", 2) == 0);
    EXPECT(line_reader_next(&reader, &second) == LINE_OK);
    EXPECT(second.length == 3 && memcmp(second.data, "bb\n", 3) == 0);
    EXPECT(memcmp(first.data, "a\n", 2) == 0);
    line_destroy(&second);
    line_destroy(&first);
    EXPECT(expect_line(&reader, (const unsigned char *)"last", 4) == 0);
    EXPECT(line_reader_next(&reader, &first) == LINE_EOF);
    EXPECT(line_reader_next(&reader, &first) == LINE_EOF);
    line_reader_destroy(&reader);
    close(fd);
    return 0;
}

static int empty_and_newlines(void)
{
    struct line_reader reader;
    struct line line;
    int fd;

    EXPECT(pipe_with_data((const unsigned char *)"", 0, &fd) == 0);
    EXPECT(line_reader_init(&reader, fd, 8) == 0);
    EXPECT(line_reader_next(&reader, &line) == LINE_EOF);
    line_reader_destroy(&reader);
    close(fd);

    EXPECT(pipe_with_data((const unsigned char *)"\n\n", 2, &fd) == 0);
    EXPECT(line_reader_init(&reader, fd, 8) == 0);
    EXPECT(expect_line(&reader, (const unsigned char *)"\n", 1) == 0);
    EXPECT(expect_line(&reader, (const unsigned char *)"\n", 1) == 0);
    EXPECT(line_reader_next(&reader, &line) == LINE_EOF);
    line_reader_destroy(&reader);
    close(fd);
    return 0;
}

static int embedded_nul(void)
{
    static const unsigned char input[] = {'A', 0, 'B', '\n'};
    struct line_reader reader;
    int fd;

    EXPECT(pipe_with_data(input, sizeof input, &fd) == 0);
    EXPECT(line_reader_init(&reader, fd, 3) == 0);
    EXPECT(expect_line(&reader, input, sizeof input) == 0);
    line_reader_destroy(&reader);
    close(fd);
    return 0;
}

static int independent_readers(void)
{
    struct line_reader left;
    struct line_reader right;
    int left_fd;
    int right_fd;

    EXPECT(pipe_with_data((const unsigned char *)"L1\nL2", 5, &left_fd) == 0);
    EXPECT(pipe_with_data((const unsigned char *)"R1\nR2", 5, &right_fd) == 0);
    EXPECT(line_reader_init(&left, left_fd, 8) == 0);
    EXPECT(line_reader_init(&right, right_fd, 8) == 0);
    EXPECT(expect_line(&left, (const unsigned char *)"L1\n", 3) == 0);
    EXPECT(expect_line(&right, (const unsigned char *)"R1\n", 3) == 0);
    EXPECT(expect_line(&left, (const unsigned char *)"L2", 2) == 0);
    EXPECT(expect_line(&right, (const unsigned char *)"R2", 2) == 0);
    line_reader_destroy(&left);
    line_reader_destroy(&right);
    close(left_fd);
    close(right_fd);
    return 0;
}

static int io_error(void)
{
    struct line_reader reader;
    struct line line;
    int fds[2];

    EXPECT(pipe(fds) == 0);
    close(fds[1]);
    EXPECT(line_reader_init(&reader, fds[0], 4) == 0);
    close(fds[0]);
    EXPECT(line_reader_next(&reader, &line) == LINE_IO_ERROR);
    EXPECT(line_reader_next(&reader, &line) == LINE_IO_ERROR);
    line_reader_destroy(&reader);
    return 0;
}

int main(void)
{
    EXPECT(basic_cases() == 0);
    EXPECT(empty_and_newlines() == 0);
    EXPECT(embedded_nul() == 0);
    EXPECT(independent_readers() == 0);
    EXPECT(io_error() == 0);
    puts("record-stream 검사: 통과");
    return 0;
}
