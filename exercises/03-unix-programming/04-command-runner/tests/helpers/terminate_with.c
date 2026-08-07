#include <errno.h>
#include <signal.h>
#include <stdlib.h>

int main(int argc, char *argv[])
{
    char *end = NULL;
    long value;

    if (argc != 2)
    {
        return 2;
    }
    errno = 0;
    value = strtol(argv[1], &end, 10);
    if (errno != 0 || end == argv[1] || *end != '\0' || value <= 0 || value > 127)
    {
        return 2;
    }
    if (raise((int)value) != 0)
    {
        return 125;
    }
    return 125;
}
