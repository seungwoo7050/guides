#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

/* [Implementation 1] CLI mode를 파일 생성 정책으로만 번역해 이후 수명 코드가 플래그 조합을 추측하지 않게 합니다. */
static int output_flags(const char *mode, int *out_flags)
{
    if (strcmp(mode, "truncate") == 0)
        *out_flags = O_WRONLY | O_CREAT | O_TRUNC;
    else if (strcmp(mode, "append") == 0)
        *out_flags = O_WRONLY | O_CREAT | O_APPEND;
    else
        return -1;
    return 0;
}

/* [Implementation 2] waitpid 재시도와 셸 형태의 종료 상태 변환을 부모의 단일 책임으로 고정합니다. */
static int public_status(int status)
{
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    if (WIFSIGNALED(status))
        return 128 + WTERMSIG(status);
    return 1;
}

static int wait_child(pid_t child)
{
    int status;
    pid_t result;

    do
        result = waitpid(child, &status, 0);
    while (result < 0 && errno == EINTR);
    return result < 0 ? 1 : public_status(status);
}

/* [Implementation 3] 자식은 stdout 연결을 완성한 뒤 원본 FD를 닫고, exec 실패를 126/127로 외부화합니다. */
static void child_redirect_and_exec(int output_fd, char *const command[])
{
    int error_number;

    if (output_fd != STDOUT_FILENO)
    {
        if (dup2(output_fd, STDOUT_FILENO) < 0)
        {
            perror("dup2");
            _exit(126);
        }
        close(output_fd);
    }
    execvp(command[0], command);
    error_number = errno;
    fprintf(stderr, "%s: %s\n", command[0], strerror(error_number));
    _exit(error_number == ENOENT ? 127 : 126);
}

/* [Implementation 4] 부모가 open한 FD는 fork 양쪽에서 정확히 한 번 정리하고, 공개 결과는 회수한 자식 상태로 결정합니다. */
int main(int argc, char *argv[])
{
    int flags;
    int output_fd;
    pid_t child;

    if (argc < 4 || output_flags(argv[1], &flags) != 0)
    {
        fprintf(stderr, "사용법: %s truncate|append 출력-파일 명령 [인자 ...]\n", argv[0]);
        return 2;
    }
    output_fd = open(argv[2], flags, 0644);
    if (output_fd < 0)
    {
        perror(argv[2]);
        return 1;
    }
    child = fork();
    if (child < 0)
    {
        perror("fork");
        close(output_fd);
        return 1;
    }
    if (child == 0)
        child_redirect_and_exec(output_fd, &argv[3]);
    close(output_fd);
    return wait_child(child);
}
