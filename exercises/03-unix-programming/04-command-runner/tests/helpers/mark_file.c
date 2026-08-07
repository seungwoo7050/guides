#include <errno.h>
#include <fcntl.h>
#include <unistd.h>

int main(int argc, char *argv[])
{
    static const char marker[] = "executed\n";
    int fd;
    size_t offset = 0;

    if (argc != 2)
    {
        return 2;
    }
    fd = open(argv[1], O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd == -1)
    {
        return 3;
    }
    while (offset < sizeof marker - 1)
    {
        ssize_t written = write(fd, marker + offset, sizeof marker - 1 - offset);

        if (written > 0)
        {
            offset += (size_t)written;
        }
        else if (written == -1 && errno == EINTR)
        {
            continue;
        }
        else
        {
            (void)close(fd);
            return 4;
        }
    }
    return close(fd) == 0 ? 0 : 5;
}
