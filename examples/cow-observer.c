#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void)
{
    int *value;
    pid_t child;
    int status;

    value = malloc(sizeof(*value));
    if (value == NULL) {
        perror("malloc");
        return 1;
    }
    *value = 41;
    printf("before fork pid=%ld address=%p value=%d\n", (long)getpid(), (void *)value, *value);
    if (fflush(stdout) == EOF) {
        free(value);
        return 1;
    }
    child = fork();
    if (child < 0) {
        perror("fork");
        free(value);
        return 1;
    }
    if (child == 0) {
        *value = 99;
        printf("child pid=%ld address=%p value=%d\n", (long)getpid(), (void *)value, *value);
        if (fflush(stdout) == EOF)
            _exit(1);
        free(value);
        _exit(0);
    }
    for (;;) {
        if (waitpid(child, &status, 0) >= 0)
            break;
        if (errno != EINTR) {
            perror("waitpid");
            free(value);
            return 1;
        }
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        fprintf(stderr, "자식 프로세스가 실패했습니다.\n");
        free(value);
        return 1;
    }
    {
        int unchanged;

        unchanged = *value == 41;
        printf("parent pid=%ld address=%p value=%d unchanged=%s\n",
            (long)getpid(),
            (void *)value,
            *value,
            unchanged != 0 ? "yes" : "no");
        free(value);
        return unchanged != 0 ? 0 : 1;
    }
}
