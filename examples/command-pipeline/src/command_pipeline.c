#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int shell_status(int status)
{
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    if (WIFSIGNALED(status))
        return 128 + WTERMSIG(status);
    return 1;
}

static int wait_one(pid_t pid)
{
    int status;
    pid_t result;

    do
    {
        result = waitpid(pid, &status, 0);
    }
    while (result < 0 && errno == EINTR);
    if (result < 0)
        return 1;
    return shell_status(status);
}

static void child_exec(char *const argv[])
{
    int error_number;

    execvp(argv[0], argv);
    error_number = errno;
    fprintf(stderr, "%s: %s\n", argv[0], strerror(error_number));
    _exit(error_number == ENOENT ? 127 : 126);
}

static int run_command(char *const argv[])
{
    pid_t pid = fork();

    if (pid < 0)
    {
        perror("fork");
        return 1;
    }
    if (pid == 0)
        child_exec(argv);
    return wait_one(pid);
}

static int run_redirect(char *const argv[], const char *path, int append)
{
    int flags = O_WRONLY | O_CREAT | (append ? O_APPEND : O_TRUNC);
    int fd = open(path, flags, 0644);
    pid_t pid;

    if (fd < 0)
    {
        perror(path);
        return 1;
    }
    pid = fork();
    if (pid < 0)
    {
        perror("fork");
        close(fd);
        return 1;
    }
    if (pid == 0)
    {
        if (dup2(fd, STDOUT_FILENO) < 0)
        {
            perror("dup2");
            _exit(126);
        }
        close(fd);
        child_exec(argv);
    }
    close(fd);
    return wait_one(pid);
}

static int run_two(char *const left[], char *const right[])
{
    int p[2];
    pid_t left_pid;
    pid_t right_pid;
    int right_status;

    if (pipe(p) < 0)
    {
        perror("pipe");
        return 1;
    }
    left_pid = fork();
    if (left_pid < 0)
    {
        perror("fork");
        close(p[0]);
        close(p[1]);
        return 1;
    }
    if (left_pid == 0)
    {
        if (dup2(p[1], STDOUT_FILENO) < 0)
        {
            perror("dup2");
            _exit(126);
        }
        close(p[0]);
        close(p[1]);
        child_exec(left);
    }
    right_pid = fork();
    if (right_pid < 0)
    {
        perror("fork");
        close(p[0]);
        close(p[1]);
        kill(left_pid, SIGTERM);
        (void)wait_one(left_pid);
        return 1;
    }
    if (right_pid == 0)
    {
        if (dup2(p[0], STDIN_FILENO) < 0)
        {
            perror("dup2");
            _exit(126);
        }
        close(p[0]);
        close(p[1]);
        child_exec(right);
    }
    close(p[0]);
    close(p[1]);
    (void)wait_one(left_pid);
    right_status = wait_one(right_pid);
    return right_status;
}

static int count_open_fds(void)
{
    int count = 0;
    int fd;

    for (fd = 0; fd < 1024; fd++)
    {
        if (fcntl(fd, F_GETFD) >= 0 || errno != EBADF)
            count++;
    }
    return count;
}

static int repeat_pipeline(void)
{
    char *left[] = {"printf", "data", NULL};
    char *right[] = {"sh", "-c", "cat >/dev/null", NULL};
    int before = count_open_fds();
    int i;

    for (i = 0; i < 40; i++)
    {
        if (run_two(left, right) != 0)
            return 1;
    }
    if (count_open_fds() != before)
    {
        fprintf(stderr, "열린 파일 디스크립터 수가 달라졌습니다\n");
        return 1;
    }
    return 0;
}

static void usage(const char *program)
{
    fprintf(stderr,
        "사용법: %s spawn|missing|redirect 경로|append 경로|pipeline|pipeline-status|repeat\n",
        program);
}

int main(int argc, char **argv)
{
    char *spawn_argv[] = {"printf", "child-ok\n", NULL};
    char *missing_argv[] = {"command-that-does-not-exist-c-guide", NULL};
    char *file_argv[] = {"printf", "alpha\n", NULL};
    char *producer[] = {"printf", "alpha\nbeta\n", NULL};
    char *consumer[] = {"cat", NULL};
    char *status_consumer[] = {"sh", "-c", "cat >/dev/null; exit 7", NULL};

    if (argc < 2)
    {
        usage(argv[0]);
        return 2;
    }
    if (strcmp(argv[1], "spawn") == 0 && argc == 2)
        return run_command(spawn_argv);
    if (strcmp(argv[1], "missing") == 0 && argc == 2)
        return run_command(missing_argv);
    if (strcmp(argv[1], "redirect") == 0 && argc == 3)
        return run_redirect(file_argv, argv[2], 0);
    if (strcmp(argv[1], "append") == 0 && argc == 3)
        return run_redirect(file_argv, argv[2], 1);
    if (strcmp(argv[1], "pipeline") == 0 && argc == 2)
        return run_two(producer, consumer);
    if (strcmp(argv[1], "pipeline-status") == 0 && argc == 2)
        return run_two(producer, status_consumer);
    if (strcmp(argv[1], "repeat") == 0 && argc == 2)
        return repeat_pipeline();
    usage(argv[0]);
    return 2;
}
