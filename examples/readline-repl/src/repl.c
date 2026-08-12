#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifdef USE_READLINE
#include <readline/history.h>
#include <readline/readline.h>
#endif

/* [Implementation 1] plain 입력은 한 줄 할당과 EOF 판정을 소유하고 호출자에게 해제 책임을 넘깁니다. */
static char *plain_read_line(const char *prompt, int interactive)
{
    char *line = NULL;
    size_t capacity = 0;
    ssize_t length;

    if (interactive && prompt != NULL)
    {
        fputs(prompt, stderr);
        fflush(stderr);
    }
    length = getline(&line, &capacity, stdin);
    if (length < 0)
    {
        free(line);
        return NULL;
    }
    if (length > 0 && line[length - 1] == '\n')
    {
        line[length - 1] = '\0';
    }
    return line;
}

#ifdef USE_READLINE
/* [Implementation 2] completion 후보와 history 탐색은 선택적인 Readline backend 내부에만 둡니다. */
static const char *const commands[] = {"echo", "help", "history", "quit", NULL};

static char *command_generator(const char *text, int state)
{
    static size_t index;
    static size_t length;

    if (state == 0)
    {
        index = 0;
        length = strlen(text);
    }
    while (commands[index] != NULL)
    {
        const char *candidate = commands[index++];

        if (strncmp(candidate, text, length) == 0)
        {
            size_t candidate_length = strlen(candidate);
            char *copy = malloc(candidate_length + 1);

            if (copy != NULL)
            {
                memcpy(copy, candidate, candidate_length + 1);
            }
            return copy;
        }
    }
    return NULL;
}

static char **complete_command(const char *text, int start, int end)
{
    (void)end;
    if (start == 0)
    {
        return rl_completion_matches(text, command_generator);
    }
    return NULL;
}

static void print_history(void)
{
    int first = history_base;
    int last = history_base + history_length;

    for (int index = first; index < last; index++)
    {
        HIST_ENTRY *entry = history_get(index);

        if (entry != NULL)
        {
            printf("%d %s\n", index, entry->line);
        }
    }
}
#endif

/* [Implementation 3] 입력 어댑터가 TTY 여부로 backend를 고르되 항상 같은 owned-line 계약을 반환합니다. */
static char *read_command_line(const char *prompt, int interactive)
{
#ifdef USE_READLINE
    if (interactive)
    {
        char *line = readline(prompt != NULL ? prompt : "");

        if (line != NULL && line[0] != '\0')
        {
            add_history(line);
        }
        return line;
    }
#endif
    return plain_read_line(prompt, interactive);
}

/* [Implementation 4] 명령 정책은 입력 backend와 분리해 비대화형 검사에서도 같은 상태 전이를 사용합니다. */
static int handle_line(const char *line)
{
    if (strcmp(line, "quit") == 0)
    {
        return 1;
    }
    if (strcmp(line, "help") == 0)
    {
        puts("명령: echo 문자열, help, history, quit");
        return 0;
    }
#ifdef USE_READLINE
    if (strcmp(line, "history") == 0)
    {
        print_history();
        return 0;
    }
#else
    if (strcmp(line, "history") == 0)
    {
        fprintf(stderr, "history는 readline 빌드에서만 사용할 수 있습니다\n");
        return 0;
    }
#endif
    if (strncmp(line, "echo ", 5) == 0)
    {
        puts(line + 5);
        return 0;
    }
    if (line[0] != '\0')
    {
        fprintf(stderr, "알 수 없는 명령입니다: %s\n", line);
    }
    return 0;
}

/* [Implementation 5] REPL 루프는 입력 한 줄의 처리와 해제를 한 iteration의 수명으로 묶습니다. */
int main(void)
{
    int interactive = isatty(STDIN_FILENO) && isatty(STDERR_FILENO);

#ifdef USE_READLINE
    if (interactive)
    {
        rl_attempted_completion_function = complete_command;
    }
#endif
    while (1)
    {
        char *line = read_command_line("repl> ", interactive);
        int quit;

        if (line == NULL)
        {
            break;
        }
        quit = handle_line(line);
        free(line);
        if (quit)
        {
            break;
        }
    }
    return 0;
}
