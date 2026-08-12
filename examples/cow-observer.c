#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

/* [Implementation 1] fork 전에 heap 상태와 출력 buffer를 확정해 부모·자식 관찰이 중복 buffering에 오염되지 않게 합니다. */
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
    /* [Implementation 2] fork 뒤 자식은 같은 가상 주소의 private 값을 바꾸고 stdio cleanup을 중복하지 않도록 _exit 경계를 사용합니다. */
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
    /* [Implementation 3] 부모는 EINTR를 견디며 자식을 회수한 뒤 값 분리만 증명하고 physical frame 동일성은 주장하지 않습니다. */
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
