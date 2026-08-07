#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[])
{
    unsigned long long expected;
    unsigned long long actual = 0;
    char *end;
    char buffer[4096];

    if (argc != 2)
    {
        return 2;
    }
    errno = 0;
    expected = strtoull(argv[1], &end, 10);
    if (errno != 0 || *argv[1] == '\0' || *end != '\0')
    {
        return 2;
    }
    for (;;)
    {
        ssize_t count = read(STDIN_FILENO, buffer, sizeof buffer);

        if (count > 0)
        {
            actual += (unsigned long long)count;
        }
        else if (count == 0)
        {
            break;
        }
        else if (errno != EINTR)
        {
            return 1;
        }
    }
    return actual == expected ? 0 : 3;
}
