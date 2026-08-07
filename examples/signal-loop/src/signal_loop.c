#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int wake_fd = -1;
static volatile sig_atomic_t usr1_pending;
static volatile sig_atomic_t stop_pending;

static void signal_handler(int signal_number)
{
    int saved_errno = errno;
    unsigned char wake = 1;

    if (signal_number == SIGUSR1)
        usr1_pending = 1;
    else if (signal_number == SIGTERM || signal_number == SIGINT)
        stop_pending = 1;
    if (wake_fd >= 0)
        (void)write(wake_fd, &wake, 1);
    errno = saved_errno;
}

static int set_nonblocking(int fd)
{
    int flags = fcntl(fd, F_GETFL);

    if (flags < 0)
        return -1;
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

static int install_handler(int signal_number)
{
    struct sigaction action;

    action.sa_handler = signal_handler;
    sigemptyset(&action.sa_mask);
    sigaddset(&action.sa_mask, SIGUSR1);
    sigaddset(&action.sa_mask, SIGTERM);
    sigaddset(&action.sa_mask, SIGINT);
    action.sa_flags = 0;
    return sigaction(signal_number, &action, NULL);
}

static void drain_pipe(int fd)
{
    unsigned char buffer[64];

    while (read(fd, buffer, sizeof buffer) > 0)
        ;
}

int main(void)
{
    int p[2];
    struct pollfd item;
    unsigned long usr1_events = 0;

    if (pipe(p) < 0)
    {
        perror("pipe");
        return EXIT_FAILURE;
    }
    if (set_nonblocking(p[0]) < 0 || set_nonblocking(p[1]) < 0)
    {
        perror("fcntl");
        close(p[0]);
        close(p[1]);
        return EXIT_FAILURE;
    }
    wake_fd = p[1];
    if (install_handler(SIGUSR1) < 0 || install_handler(SIGTERM) < 0 ||
        install_handler(SIGINT) < 0)
    {
        perror("sigaction");
        close(p[0]);
        close(p[1]);
        return EXIT_FAILURE;
    }

    printf("pid=%ld\n", (long)getpid());
    fflush(stdout);
    item.fd = p[0];
    item.events = POLLIN;
    item.revents = 0;

    while (!stop_pending)
    {
        int result = poll(&item, 1, -1);

        if (result < 0)
        {
            if (errno == EINTR)
                continue;
            perror("poll");
            close(p[0]);
            close(p[1]);
            return EXIT_FAILURE;
        }
        if ((item.revents & POLLIN) != 0)
            drain_pipe(p[0]);
        if (usr1_pending)
        {
            usr1_pending = 0;
            usr1_events++;
            printf("event=usr1 observed=%lu\n", usr1_events);
            fflush(stdout);
        }
    }

    printf("shutdown observed=%lu\n", usr1_events);
    fflush(stdout);
    wake_fd = -1;
    close(p[0]);
    close(p[1]);
    return EXIT_SUCCESS;
}
