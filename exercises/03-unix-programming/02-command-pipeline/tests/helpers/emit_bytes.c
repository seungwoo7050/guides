#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char *argv[])
{
    unsigned long long remaining;
    char *end;
    char buffer[4096];

    if (argc != 2)
    {
        return 2;
    }
    errno = 0;
    remaining = strtoull(argv[1], &end, 10);
    if (errno != 0 || *argv[1] == '\0' || *end != '\0')
    {
        return 2;
    }
    memset(buffer, 'x', sizeof buffer);
    while (remaining > 0)
    {
        size_t amount = remaining < sizeof buffer ? (size_t)remaining : sizeof buffer;
        ssize_t count = write(STDOUT_FILENO, buffer, amount);

        if (count > 0)
        {
            remaining -= (unsigned long long)count;
        }
        else if (count == -1 && errno == EINTR)
        {
            continue;
        }
        else
        {
            return 1;
        }
    }
    return 0;
}
