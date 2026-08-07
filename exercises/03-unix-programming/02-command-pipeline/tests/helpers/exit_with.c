#include <errno.h>
#include <stdlib.h>

int main(int argc, char *argv[])
{
    char *end;
    long value;

    if (argc != 2)
    {
        return 2;
    }
    errno = 0;
    value = strtol(argv[1], &end, 10);
    if (errno != 0 || *argv[1] == '\0' || *end != '\0' || value < 0 || value > 255)
    {
        return 2;
    }
    return (int)value;
}
