#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static volatile sig_atomic_t active_group;
static volatile sig_atomic_t received_signal;

/* [Implementation 1] handler는 이미 공개된 process group에 같은 사건을 전달하고 관찰 상태만 남깁니다. */
static void forward_signal(int signal_number)
{
    received_signal = signal_number;
    if (active_group > 0)
        (void)kill(-(pid_t)active_group, signal_number);
}

/* [Implementation 2] 부모의 회수 루프는 handler의 EINTR과 자식의 공개 상태 계산을 한 경계에서 처리합니다. */
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

/* [Implementation 3] 자식은 새 그룹에 참여한 뒤 부모의 handler와 block mask를 상속하지 않고 exec합니다. */
static void child_exec(char *const command[], const sigset_t *parent_mask)
{
    struct sigaction action;
    int error_number;

    memset(&action, 0, sizeof action);
    action.sa_handler = SIG_DFL;
    sigemptyset(&action.sa_mask);
    (void)sigaction(SIGINT, &action, NULL);
    (void)sigaction(SIGTERM, &action, NULL);
    (void)sigprocmask(SIG_SETMASK, parent_mask, NULL);
    execvp(command[0], command);
    error_number = errno;
    fprintf(stderr, "%s: %s\n", command[0], strerror(error_number));
    _exit(error_number == ENOENT ? 127 : 126);
}

int main(int argc, char *argv[])
{
    struct sigaction action;
    struct sigaction old_int;
    struct sigaction old_term;
    sigset_t blocked;
    sigset_t parent_mask;
    pid_t child = -1;
    int result = 1;
    int mask_ready = 0;
    int mask_blocked = 0;
    int int_handler_installed = 0;
    int term_handler_installed = 0;
    int group_ready = 0;

    if (argc < 2)
    {
        fprintf(stderr, "사용법: %s 명령 [인자 ...]\n", argv[0]);
        return 2;
    }

    /* [Implementation 4] fork와 group ID 공개가 끝날 때까지 전달 대상 시그널을 막아 handler가 부분 상태를 보지 않게 합니다. */
    memset(&action, 0, sizeof action);
    action.sa_handler = forward_signal;
    sigemptyset(&action.sa_mask);
    sigaddset(&action.sa_mask, SIGINT);
    sigaddset(&action.sa_mask, SIGTERM);
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGINT);
    sigaddset(&blocked, SIGTERM);
    if (sigprocmask(SIG_BLOCK, &blocked, &parent_mask) != 0)
    {
        perror("sigprocmask");
        return 1;
    }
    mask_ready = 1;
    mask_blocked = 1;
    if (sigaction(SIGINT, &action, &old_int) != 0)
    {
        perror("sigaction");
        goto cleanup;
    }
    int_handler_installed = 1;
    if (sigaction(SIGTERM, &action, &old_term) != 0)
    {
        perror("sigaction");
        goto cleanup;
    }
    term_handler_installed = 1;
    child = fork();
    if (child < 0)
    {
        perror("fork");
        goto cleanup;
    }
    if (child == 0)
    {
        if (setpgid(0, 0) != 0)
            _exit(126);
        child_exec(&argv[1], &parent_mask);
    }
    if (setpgid(child, child) != 0 && errno != EACCES && errno != ESRCH)
    {
        perror("setpgid");
        goto cleanup;
    }
    group_ready = 1;
    active_group = (sig_atomic_t)child;
    if (sigprocmask(SIG_SETMASK, &parent_mask, NULL) != 0)
    {
        perror("sigprocmask");
        (void)kill(-child, SIGTERM);
    }
    else
    {
        mask_blocked = 0;
    }

    /* [Implementation 5] 회수 뒤에는 전달 대상을 먼저 숨기고 이전 signal 상태를 역순으로 복구합니다. */
    result = wait_child(child);
    child = -1;
    if (received_signal != 0)
        result = 128 + received_signal;

cleanup:
    if (mask_ready && !mask_blocked)
    {
        if (sigprocmask(SIG_BLOCK, &blocked, NULL) != 0)
            result = 1;
        else
            mask_blocked = 1;
    }
    active_group = 0;
    if (child > 0)
    {
        if (group_ready)
            (void)kill(-child, SIGTERM);
        (void)kill(child, SIGTERM);
        (void)wait_child(child);
    }
    if (term_handler_installed && sigaction(SIGTERM, &old_term, NULL) != 0)
        result = 1;
    if (int_handler_installed && sigaction(SIGINT, &old_int, NULL) != 0)
        result = 1;
    if (mask_ready && sigprocmask(SIG_SETMASK, &parent_mask, NULL) != 0)
        result = 1;
    return result;
}
