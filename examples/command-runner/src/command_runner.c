#define _POSIX_C_SOURCE 200809L

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

enum token_type
{
    TOK_WORD,
    TOK_PIPE,
    TOK_IN,
    TOK_OUT,
    TOK_APPEND
};

struct token
{
    enum token_type type;
    char *text;
};

struct token_list
{
    struct token *items;
    size_t length;
    size_t capacity;
};

struct string_buffer
{
    char *data;
    size_t length;
    size_t capacity;
};

struct command
{
    char **argv;
    size_t argc;
    size_t capacity;
    char *in_path;
    char *out_path;
    int append;
};

struct pipeline
{
    struct command *commands;
    size_t length;
    size_t capacity;
};

static volatile sig_atomic_t received_signal;
static volatile sig_atomic_t active_pipeline;

static void forward_signal(int signal_number)
{
    received_signal = signal_number;
    if (active_pipeline > 0)
        (void)kill(-(pid_t)active_pipeline, signal_number);
}

static int install_signal_handlers(void)
{
    struct sigaction action;

    memset(&action, 0, sizeof action);
    action.sa_handler = forward_signal;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGINT, &action, NULL) != 0)
        return -1;
    if (sigaction(SIGTERM, &action, NULL) != 0)
        return -1;
    return 0;
}

static void restore_child_signals(const sigset_t *parent_mask)
{
    struct sigaction action;

    memset(&action, 0, sizeof action);
    action.sa_handler = SIG_DFL;
    sigemptyset(&action.sa_mask);
    (void)sigaction(SIGINT, &action, NULL);
    (void)sigaction(SIGTERM, &action, NULL);
    (void)sigprocmask(SIG_SETMASK, parent_mask, NULL);
}

static char *duplicate_text(const char *text)
{
    size_t length = strlen(text);
    char *copy = malloc(length + 1);

    if (copy != NULL)
        memcpy(copy, text, length + 1);
    return copy;
}

static int grow_array(void **data, size_t *capacity, size_t item_size, size_t needed)
{
    size_t next_capacity;
    void *next;

    if (needed <= *capacity)
        return 0;
    next_capacity = *capacity == 0 ? 4 : *capacity;
    while (next_capacity < needed)
    {
        if (next_capacity > (size_t)-1 / 2)
            return -1;
        next_capacity *= 2;
    }
    if (next_capacity > (size_t)-1 / item_size)
        return -1;
    next = realloc(*data, next_capacity * item_size);
    if (next == NULL)
        return -1;
    *data = next;
    *capacity = next_capacity;
    return 0;
}

static void string_buffer_destroy(struct string_buffer *buffer)
{
    free(buffer->data);
    buffer->data = NULL;
    buffer->length = 0;
    buffer->capacity = 0;
}

static int string_buffer_push(struct string_buffer *buffer, char value)
{
    if (grow_array(
            (void **)&buffer->data,
            &buffer->capacity,
            sizeof buffer->data[0],
            buffer->length + 2) != 0)
        return -1;
    buffer->data[buffer->length++] = value;
    buffer->data[buffer->length] = '\0';
    return 0;
}

static int token_push(
    struct token_list *tokens,
    enum token_type type,
    char *owned_text
)
{
    if (grow_array(
            (void **)&tokens->items,
            &tokens->capacity,
            sizeof tokens->items[0],
            tokens->length + 1) != 0)
        return -1;
    tokens->items[tokens->length].type = type;
    tokens->items[tokens->length].text = owned_text;
    tokens->length++;
    return 0;
}

static void token_list_destroy(struct token_list *tokens)
{
    size_t i;

    for (i = 0; i < tokens->length; i++)
        free(tokens->items[i].text);
    free(tokens->items);
    tokens->items = NULL;
    tokens->length = 0;
    tokens->capacity = 0;
}

static int operator_at(const char *line, size_t index)
{
    return line[index] == '|' || line[index] == '<' || line[index] == '>';
}

static int tokenize_word(
    const char *line,
    size_t *index,
    struct token_list *tokens,
    const char **error
)
{
    struct string_buffer word = {NULL, 0, 0};
    int has_part = 0;

    while (line[*index] != '\0' &&
        !isspace((unsigned char)line[*index]) &&
        !operator_at(line, *index))
    {
        char quote = 0;

        if (line[*index] == '\'' || line[*index] == '"')
        {
            quote = line[*index];
            (*index)++;
            has_part = 1;
            while (line[*index] != '\0' && line[*index] != quote)
            {
                if (string_buffer_push(&word, line[*index]) != 0)
                    goto no_memory;
                (*index)++;
            }
            if (line[*index] != quote)
            {
                *error = "따옴표가 닫히지 않았습니다";
                string_buffer_destroy(&word);
                return -1;
            }
            (*index)++;
        }
        else
        {
            has_part = 1;
            if (string_buffer_push(&word, line[*index]) != 0)
                goto no_memory;
            (*index)++;
        }
    }
    if (!has_part)
    {
        *error = "단어가 필요합니다";
        return -1;
    }
    if (word.data == NULL)
    {
        word.data = duplicate_text("");
        if (word.data == NULL)
            goto no_memory;
    }
    if (token_push(tokens, TOK_WORD, word.data) != 0)
        goto no_memory_owned;
    return 0;

no_memory:
    *error = "메모리가 부족합니다";
    string_buffer_destroy(&word);
    return -1;
no_memory_owned:
    *error = "메모리가 부족합니다";
    free(word.data);
    return -1;
}

static int tokenize(const char *line, struct token_list *tokens, const char **error)
{
    size_t i = 0;

    while (line[i] != '\0')
    {
        while (isspace((unsigned char)line[i]))
            i++;
        if (line[i] == '\0')
            break;
        if (line[i] == '|')
        {
            if (token_push(tokens, TOK_PIPE, NULL) != 0)
                goto no_memory;
            i++;
        }
        else if (line[i] == '<')
        {
            if (token_push(tokens, TOK_IN, NULL) != 0)
                goto no_memory;
            i++;
        }
        else if (line[i] == '>')
        {
            enum token_type type = TOK_OUT;

            i++;
            if (line[i] == '>')
            {
                type = TOK_APPEND;
                i++;
            }
            if (token_push(tokens, type, NULL) != 0)
                goto no_memory;
        }
        else if (tokenize_word(line, &i, tokens, error) != 0)
            return -1;
    }
    return 0;

no_memory:
    *error = "메모리가 부족합니다";
    return -1;
}

static void command_init(struct command *command)
{
    command->argv = NULL;
    command->argc = 0;
    command->capacity = 0;
    command->in_path = NULL;
    command->out_path = NULL;
    command->append = 0;
}

static void command_destroy(struct command *command)
{
    size_t i;

    for (i = 0; i < command->argc; i++)
        free(command->argv[i]);
    free(command->argv);
    free(command->in_path);
    free(command->out_path);
    command_init(command);
}

static void pipeline_destroy(struct pipeline *pipeline)
{
    size_t i;

    for (i = 0; i < pipeline->length; i++)
        command_destroy(&pipeline->commands[i]);
    free(pipeline->commands);
    pipeline->commands = NULL;
    pipeline->length = 0;
    pipeline->capacity = 0;
}

static int pipeline_add_command(struct pipeline *pipeline)
{
    if (grow_array(
            (void **)&pipeline->commands,
            &pipeline->capacity,
            sizeof pipeline->commands[0],
            pipeline->length + 1) != 0)
        return -1;
    command_init(&pipeline->commands[pipeline->length]);
    pipeline->length++;
    return 0;
}

static int command_add_arg(struct command *command, const char *text)
{
    char *copy;

    if (grow_array(
            (void **)&command->argv,
            &command->capacity,
            sizeof command->argv[0],
            command->argc + 2) != 0)
        return -1;
    copy = duplicate_text(text);
    if (copy == NULL)
        return -1;
    command->argv[command->argc++] = copy;
    command->argv[command->argc] = NULL;
    return 0;
}

static int replace_path(char **slot, const char *text)
{
    char *copy = duplicate_text(text);

    if (copy == NULL)
        return -1;
    free(*slot);
    *slot = copy;
    return 0;
}

static int parse(
    const struct token_list *tokens,
    struct pipeline *pipeline,
    const char **error
)
{
    size_t i = 0;

    if (pipeline_add_command(pipeline) != 0)
        goto no_memory;
    while (i < tokens->length)
    {
        struct command *command = &pipeline->commands[pipeline->length - 1];
        enum token_type type = tokens->items[i].type;

        if (type == TOK_WORD)
        {
            if (command_add_arg(command, tokens->items[i].text) != 0)
                goto no_memory;
        }
        else if (type == TOK_PIPE)
        {
            if (command->argc == 0)
            {
                *error = "파이프 앞의 명령이 비어 있습니다";
                return -1;
            }
            if (pipeline_add_command(pipeline) != 0)
                goto no_memory;
        }
        else
        {
            if (i + 1 >= tokens->length || tokens->items[i + 1].type != TOK_WORD)
            {
                *error = "리다이렉션 대상이 없습니다";
                return -1;
            }
            if (type == TOK_IN)
            {
                if (replace_path(&command->in_path, tokens->items[i + 1].text) != 0)
                    goto no_memory;
            }
            else
            {
                if (replace_path(&command->out_path, tokens->items[i + 1].text) != 0)
                    goto no_memory;
                command->append = type == TOK_APPEND;
            }
            i++;
        }
        i++;
    }
    if (pipeline->commands[pipeline->length - 1].argc == 0)
    {
        *error = tokens->length == 0
            ? "입력이 비어 있습니다"
            : "파이프 뒤의 명령이 비어 있습니다";
        return -1;
    }
    return 0;

no_memory:
    *error = "메모리가 부족합니다";
    return -1;
}

static int build_pipeline(const char *line, struct pipeline *pipeline, const char **error)
{
    struct token_list tokens = {NULL, 0, 0};
    int result;

    result = tokenize(line, &tokens, error);
    if (result == 0)
        result = parse(&tokens, pipeline, error);
    token_list_destroy(&tokens);
    if (result != 0)
        pipeline_destroy(pipeline);
    return result;
}

static void dump_pipeline(const struct pipeline *pipeline)
{
    size_t i;

    printf("파이프라인 길이=%zu\n", pipeline->length);
    for (i = 0; i < pipeline->length; i++)
    {
        const struct command *command = &pipeline->commands[i];
        size_t j;

        printf("명령 %zu\n", i);
        for (j = 0; j < command->argc; j++)
            printf("  argv[%zu]=<%s>\n", j, command->argv[j]);
        printf("  표준 입력=<%s>\n",
            command->in_path != NULL ? command->in_path : "-");
        if (command->out_path == NULL)
            printf("  표준 출력=<->\n");
        else
            printf("  표준 출력=<%s> 모드=%s\n", command->out_path,
                command->append ? "추가" : "덮어쓰기");
    }
}

static int wait_status(pid_t pid)
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
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    if (WIFSIGNALED(status))
        return 128 + WTERMSIG(status);
    return 1;
}

static void child_die(const char *message, int status)
{
    perror(message);
    _exit(status);
}

static void apply_redirections(const struct command *command)
{
    int fd;
    int flags;

    if (command->in_path != NULL)
    {
        fd = open(command->in_path, O_RDONLY);
        if (fd < 0)
            child_die(command->in_path, 126);
        if (dup2(fd, STDIN_FILENO) < 0)
            child_die("dup2", 126);
        close(fd);
    }
    if (command->out_path != NULL)
    {
        flags = O_WRONLY | O_CREAT | (command->append ? O_APPEND : O_TRUNC);
        fd = open(command->out_path, flags, 0644);
        if (fd < 0)
            child_die(command->out_path, 126);
        if (dup2(fd, STDOUT_FILENO) < 0)
            child_die("dup2", 126);
        close(fd);
    }
}

static void exec_command(
    const struct command *command,
    int previous_read,
    int next_pipe[2],
    int has_next
)
{
    int error_number;

    if (previous_read >= 0 && dup2(previous_read, STDIN_FILENO) < 0)
        child_die("dup2", 126);
    if (has_next && dup2(next_pipe[1], STDOUT_FILENO) < 0)
        child_die("dup2", 126);
    if (previous_read >= 0)
        close(previous_read);
    if (has_next)
    {
        close(next_pipe[0]);
        close(next_pipe[1]);
    }
    apply_redirections(command);
    execvp(command->argv[0], command->argv);
    error_number = errno;
    fprintf(stderr, "%s: %s\n", command->argv[0], strerror(error_number));
    _exit(error_number == ENOENT ? 127 : 126);
}

static int execute_pipeline(const struct pipeline *pipeline)
{
    pid_t *pids = calloc(pipeline->length, sizeof *pids);
    size_t started = 0;
    int previous_read = -1;
    size_t i;
    int final_status = 1;
    pid_t group = 0;
    sigset_t blocked_signals;
    sigset_t parent_mask;
    int signals_blocked = 0;

    if (pids == NULL)
        return 1;
    sigemptyset(&blocked_signals);
    sigaddset(&blocked_signals, SIGINT);
    sigaddset(&blocked_signals, SIGTERM);
    if (sigprocmask(SIG_BLOCK, &blocked_signals, &parent_mask) != 0)
    {
        free(pids);
        return 1;
    }
    signals_blocked = 1;
    active_pipeline = 0;
    if (received_signal != 0)
    {
        (void)sigprocmask(SIG_SETMASK, &parent_mask, NULL);
        free(pids);
        return 128 + received_signal;
    }
    for (i = 0; i < pipeline->length; i++)
    {
        int next_pipe[2] = {-1, -1};
        int has_next = i + 1 < pipeline->length;
        pid_t pid;

        if (has_next && pipe(next_pipe) < 0)
            goto fail;
        pid = fork();
        if (pid < 0)
        {
            if (has_next)
            {
                close(next_pipe[0]);
                close(next_pipe[1]);
            }
            goto fail;
        }
        if (pid == 0)
        {
            if (setpgid(0, group == 0 ? 0 : group) != 0)
                child_die("setpgid", 126);
            restore_child_signals(&parent_mask);
            exec_command(&pipeline->commands[i], previous_read, next_pipe, has_next);
        }
        pids[started++] = pid;
        if (group == 0)
        {
            group = pid;
            active_pipeline = (sig_atomic_t)group;
        }
        if (setpgid(pid, group) != 0 && errno != EACCES && errno != ESRCH)
        {
            if (has_next)
            {
                close(next_pipe[0]);
                close(next_pipe[1]);
            }
            goto fail;
        }
        if (previous_read >= 0)
            close(previous_read);
        if (has_next)
        {
            close(next_pipe[1]);
            previous_read = next_pipe[0];
        }
        else
            previous_read = -1;
    }
    if (sigprocmask(SIG_SETMASK, &parent_mask, NULL) != 0)
        goto fail;
    signals_blocked = 0;
    for (i = 0; i < started; i++)
    {
        int status = wait_status(pids[i]);
        if (i + 1 == started)
            final_status = status;
    }
    active_pipeline = 0;
    free(pids);
    if (received_signal != 0)
        return 128 + received_signal;
    return final_status;

fail:
    if (previous_read >= 0)
        close(previous_read);
    if (group > 0)
        kill(-group, SIGTERM);
    for (i = 0; i < started; i++)
        kill(pids[i], SIGTERM);
    for (i = 0; i < started; i++)
        (void)wait_status(pids[i]);
    active_pipeline = 0;
    if (signals_blocked)
        (void)sigprocmask(SIG_SETMASK, &parent_mask, NULL);
    free(pids);
    if (received_signal != 0)
        return 128 + received_signal;
    return 1;
}

static void usage(const char *program)
{
    fprintf(stderr, "사용법: %s [--dump] <명령줄>\n", program);
}

int main(int argc, char **argv)
{
    struct pipeline pipeline = {NULL, 0, 0};
    const char *error = NULL;
    const char *line;
    int dump = 0;
    int result;

    if (install_signal_handlers() != 0)
    {
        perror("sigaction");
        return 1;
    }
    if (argc == 3 && strcmp(argv[1], "--dump") == 0)
    {
        dump = 1;
        line = argv[2];
    }
    else if (argc == 2)
        line = argv[1];
    else
    {
        usage(argv[0]);
        return 2;
    }
    if (build_pipeline(line, &pipeline, &error) != 0)
    {
        fprintf(stderr, "문법 오류: %s\n",
            error != NULL ? error : "잘못된 입력입니다");
        return 2;
    }
    if (dump)
    {
        dump_pipeline(&pipeline);
        result = 0;
    }
    else
        result = execute_pipeline(&pipeline);
    pipeline_destroy(&pipeline);
    return result;
}
