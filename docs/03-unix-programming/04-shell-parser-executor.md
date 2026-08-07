# 셸 파서와 실행기: 입력 문법과 프로세스 책임 분리

작은 셸의 난점은 `fork` 호출 하나가 아니라 문자열을 어떤 규칙으로 해석하고, 중간 표현으로 보존하고, 실행 계획으로 바꾸는지입니다. 입력을 읽는 즉시 `open`, `dup2`, `fork`를 호출하면 문법 오류 뒤 일부 명령만 실행되거나 부분 할당과 자식 정리가 한 함수에 섞입니다.

핵심은 입력을 단계별 표현으로 바꾸는 것입니다.

```text
입력 줄
→ lexer: token과 인용 정보
→ parser: command·pipeline·redirection 구조
→ expansion: 환경과 상태를 문자열로 반영
→ validation: 실행 가능한 불변식 확인
→ executor: pipe·fork·dup2·exec·wait
→ shell-style 종료 상태
```

각 단계는 다음 단계가 다시 원문 문법을 추측하지 않아도 되는 계약을 만들어야 합니다.

## 입력 계층과 parser를 분리합니다

대화형 입력, 파일 입력과 테스트 문자열은 서로 다른 방식으로 줄을 얻을 수 있습니다.

```c
char *read_command_line(const char *prompt, int interactive);
```

이 함수는 한 줄의 소유 문자열 또는 EOF·오류 상태를 반환할 수 있습니다. lexer는 어디에서 입력을 얻었는지 몰라야 하며, executor도 prompt와 line editor를 알 필요가 없습니다.

이번 연습은 대화형 UI를 제외하고 명령 문자열 하나를 argv로 받습니다. 이 제한으로 lexer·parser·executor 계약에 집중합니다.

## lexer가 만드는 최소 token

전체 셸로 확장할 때의 대표 token은 다음과 같습니다.

```text
WORD
PIPE        |
REDIR_IN    <
REDIR_OUT   >
APPEND      >>
HEREDOC     <<
```

공백은 token이 아니라 인용되지 않은 문자의 구분자입니다. 따옴표 안의 공백과 `|`는 WORD 일부가 될 수 있습니다.

이번 연습은 `WORD`와 `PIPE`만 지원합니다. `<`, `>`, `>>`, `<<`를 일반 WORD로 조용히 오해하지 않고 **지원 범위 밖**으로 명시합니다.

## lexer의 인용 상태

최소 상태 머신:

```text
UNQUOTED
SINGLE_QUOTED
DOUBLE_QUOTED
ESCAPED
```

이번 연습 규칙:

- 인용되지 않은 공백은 인자를 나눕니다.
- 작은따옴표 안의 모든 문자는 그대로 WORD에 들어갑니다.
- 큰따옴표 안에서는 공백과 `|`도 WORD 일부입니다.
- 큰따옴표 안의 역슬래시는 다음 문자 하나를 literal로 만듭니다.
- 인용되지 않은 역슬래시도 다음 문자 하나를 literal로 만듭니다.
- 인용되지 않은 `|`는 PIPE token입니다.
- 붙어 있는 인용 조각은 하나의 WORD가 됩니다.
- `''`와 `""`는 길이 0인 인자를 만듭니다.

```text
print one 'two three' "" ab"cd" escaped\ space
```

WORD 결과:

```text
print
one
two three
빈 문자열
abcd
escaped space
```

따옴표 문자는 최종 argv에 남기지 않습니다. 입력 끝에서 열린 따옴표나 마지막 역슬래시가 남으면 전체 입력을 문법 오류로 반환합니다.

## 빈 단어와 “아직 시작하지 않은 단어”를 구분합니다

다음 둘은 다릅니다.

```text
공백만 있음    WORD 없음
""           길이 0인 WORD 하나
```

lexer가 현재 word buffer 길이만 보고 token 생성 여부를 판단하면 빈 인자를 잃습니다. 별도의 `word_started` 상태가 필요합니다.

```c
struct word_builder
{
    char *data;
    size_t length;
    size_t capacity;
    int started;
};
```

따옴표를 열었거나 escape로 문자를 시작했다면 길이가 0이어도 WORD가 존재할 수 있습니다.

## token과 문자열의 소유권

lexer는 입력 줄을 view로 참조하거나 token마다 새 문자열을 소유할 수 있습니다.

### view 방식

- 복사가 적습니다.
- 원본 줄이 모든 token보다 오래 살아야 합니다.
- 따옴표 제거와 escape 처리 결과를 별도로 저장해야 할 수 있습니다.

### 소유 문자열 방식

- token 정리가 명확합니다.
- 각 WORD의 완성 문자열을 바로 argv로 이동할 수 있습니다.
- 중간 할당 실패 정리 경로가 필요합니다.

이번 연습은 WORD가 완성된 문자열을 소유하고 parser가 그 소유권을 command argv로 이동하는 구조를 사용합니다. 이동 뒤 token 쪽 포인터를 NULL로 만들어 이중 해제를 막습니다.

## 확장까지 지원하면 인용 메타데이터가 필요합니다

이번 연습에는 변수 확장이 없지만 완전한 셸에서는 다음 입력의 인용 종류를 보존해야 합니다.

```text
pre"$HOME"'/$USER'
```

단일 완성 문자열만 남기면 어느 구간에서 확장을 허용해야 하는지 알 수 없습니다. WORD를 구간 목록으로 표현할 수 있습니다.

```c
enum quote_mode
{
    QUOTE_NONE,
    QUOTE_SINGLE,
    QUOTE_DOUBLE
};

struct word_part
{
    enum quote_mode mode;
    char *text;
    struct word_part *next;
};
```

```text
NONE:   pre
DOUBLE: $HOME
SINGLE: /$USER
```

확장기는 구간별 규칙을 적용한 뒤 최종 argv 문자열로 결합합니다. 기능 범위가 작은 단계에서는 이 표현을 미리 만들 필요가 없습니다.

## parser가 만드는 실행 전 구조

실행기는 원시 token 문자열을 직접 해석하지 않는 편이 좋습니다.

```c
struct command
{
    char **argv;
    size_t argc;
};

struct pipeline
{
    struct command *commands;
    size_t count;
};
```

redirection을 지원하면 argv와 분리합니다.

```c
struct redirection
{
    enum redirection_type type;
    char *target;
    struct redirection *next;
};
```

parser 성공 결과의 불변식 예:

- pipeline에 빈 command가 없습니다.
- 각 command의 `argc > 0`입니다.
- 각 `argv`는 널 포인터로 끝납니다.
- 따옴표와 escape 문자는 최종 데이터에만 반영됩니다.
- redirection 연산자와 대상은 argv에서 제거됩니다.
- 모든 redirection에는 target이 있습니다.
- executor가 token 문법을 다시 검사할 필요가 없습니다.

이번 연습은 정적 배열에 최대 command 두 개를 보관하지만, 같은 불변식을 유지합니다.

## 문법 오류는 자식 생성 전에 끝냅니다

다음 입력은 `fork` 전에 거부합니다.

```text
빈 입력
| x
x |
x || y
x | | y
닫히지 않은 따옴표
끝의 역슬래시
지원 범위를 넘는 두 개 이상의 pipe
```

문법 오류 계약:

```text
상태 2
stderr에 진단
stdout 변화 없음
자식 프로세스 생성 없음
파일 생성·작업 디렉터리 변경 같은 실행 부수효과 없음
부분 token·command 할당 모두 해제
```

입력 일부를 실행한 뒤 뒤쪽 문법 오류를 발견하면 전체 입력의 경계가 깨집니다.

## redirection은 argv가 아닙니다

전체 셸로 확장할 때 다음 입력을 생각합니다.

```text
grep word < input.txt > output.txt
```

실행 프로그램이 받는 argv:

```text
["grep", "word", NULL]
```

`<`, `input.txt`, `>`, `output.txt`는 command의 redirection 목록으로 이동합니다.

같은 종류의 redirection이 여러 번 나올 때 의미를 정해야 합니다. 실제 셸과 비슷하게 왼쪽부터 모두 열어 앞 파일의 생성·오류 효과도 관찰하고 마지막 성공 항목이 최종 FD를 결정할 수 있습니다. “마지막 항목만 보관”하는 축소 규칙을 택하면 앞 redirection의 의미가 달라짐을 문서화합니다.

## executor는 검증된 구조만 받습니다

명령 하나:

```text
fork
→ child exec
→ parent wait
→ 종료 상태 변환
```

명령 두 개:

```text
pipe 생성
→ 왼쪽 child 생성
→ 오른쪽 child 생성
→ 부모 pipe 끝 close
→ 두 child wait
→ 오른쪽 상태 반환
```

executor는 lexer의 인용 상태를 알 필요가 없고 parser는 파일 디스크립터 안무를 알 필요가 없습니다. 이 분리가 단위 테스트 경계를 만듭니다.

## 파이프와 redirection의 적용 순서

전체 셸에서는 command마다 다음 순서를 계획할 수 있습니다.

1. 필요한 pipe를 만듭니다.
2. `fork`합니다.
3. child에서 pipeline stdin/stdout을 연결합니다.
4. 명시적 redirection을 문법 순서로 적용합니다.
5. 불필요한 FD를 모두 닫습니다.
6. builtin 또는 `exec`를 실행합니다.
7. parent가 불필요한 FD를 닫습니다.
8. 모든 child를 회수합니다.

명시적 출력 redirection을 pipeline 연결 뒤에 적용하면 마지막 `dup2`가 우선합니다.

```text
producer > out.txt | consumer
```

이 경우 producer stdout이 파일로 향하고 pipe에는 데이터가 없을 수 있습니다. 우선순위는 executor의 임의 선택이 아니라 셸 문법 계약입니다.

## 문법 오류와 실행 오류를 구분합니다

### 문법 오류

- 입력만 보고 `fork` 전에 판정합니다.
- 실행 부수효과가 없습니다.
- 상태 2 같은 전용 결과를 사용합니다.

### 실행 오류

- 문법적으로 유효한 command를 실행하는 중 발생합니다.
- `pipe`, `fork`, `dup2`, `open`, `exec` 실패가 포함됩니다.
- 이미 일부 child가 시작됐을 수 있습니다.
- stderr와 child 상태 또는 parent API 오류로 관찰합니다.

“명령을 찾을 수 없음”은 lexer/parser 오류가 아니라 `exec` 단계의 실패입니다.

## 종료 상태 계약

이번 연습의 기본 상태:

```text
0~255   마지막 command의 상태
2       lexer/parser 또는 사용법 오류
126     명령을 찾았지만 실행할 수 없음
127     명령을 찾지 못함
128+N   signal N으로 종료
```

`execvp` 실패 직후 `errno`를 저장해 `ENOENT`는 127, 나머지 대표 실행 실패는 126으로 분류합니다. 실제 셸은 `ENOTDIR`, 권한과 directory 실행 같은 세부 조건을 더 구분할 수 있습니다.

pipeline의 공개 상태는 오른쪽 command의 상태를 사용하지만 왼쪽 child도 반드시 회수합니다.

## 변수 확장

전체 셸로 확장할 때 `$NAME`, `$?` 같은 항목을 문자열로 바꿉니다.

```text
작은따옴표     확장하지 않음
큰따옴표       변수 확장, 일반적인 field splitting은 제한
인용 없음      변수 확장 뒤 splitting과 glob 규칙이 추가될 수 있음
```

확장 결과가 빈 문자열일 때 argv 항목을 유지할지 제거할지도 인용 상태에 따라 다릅니다. 환경 변수는 내부 map이나 `KEY=VALUE` 목록으로 관리하고 외부 명령 실행 직전에 널 종료 `char **envp`로 직렬화할 수 있습니다.

POSIX 셸 전체의 parameter expansion, command substitution, field splitting과 pathname expansion은 별도의 언어 처리 범위입니다. 축소 구현은 지원하지 않는 문법을 명시적으로 거부하거나 제한해야 합니다.

## builtin은 부모 상태를 바꿀 수 있습니다

`cd`, 환경 변경과 셸 종료 요청은 현재 셸 프로세스 상태에 영향을 줍니다. 항상 child에서 실행하면 변경이 parent에 남지 않습니다.

```text
단일 command이며 pipeline 밖의 상태 변경 builtin
→ parent에서 실행

pipeline 안의 builtin
→ child에서 실행 가능, 상태 변경은 parent에 남지 않음
```

parent에서 redirection을 적용한다면 원래 stdin/stdout을 저장하고 모든 성공·실패 경로에서 복구합니다.

```text
원본 FD dup
→ redirection 적용
→ builtin 실행
→ 원본 FD 복구
→ 임시 FD close
```

이번 연습은 외부 명령만 지원해 이 복잡도를 의도적으로 제외합니다.

## heredoc의 별도 생명주기

heredoc은 delimiter까지 여러 줄을 읽어 command stdin으로 제공합니다.

설계 질문:

- body를 parsing 중 읽을지 실행 직전 읽을지
- delimiter 인용이 expansion 정책에 어떤 영향을 주는지
- 메모리, pipe, 임시 파일 중 어디에 저장할지
- 큰 입력에서 writer가 block하지 않는지
- `SIGINT`로 취소할 때 부분 body와 임시 자원을 어떻게 정리할지
- 여러 heredoc을 어느 순서로 읽을지

간단한 구현은 실행 전에 모든 body를 임시 파일에 기록하고 읽기 FD를 command에 연결할 수 있습니다. pipe를 사용하면 큰 body를 child reader가 시작하기 전에 전부 쓰다가 block할 수 있으므로 실행 순서가 중요합니다.

## 대화형 입력과 Readline

대화형 UI는 parser와 독립된 adapter로 둡니다.

```text
Readline 또는 단순 stdin reader
→ 소유 문자열 또는 EOF/오류
→ 같은 lexer/parser API
```

parent는 prompt 대기 중 `SIGINT`를 받아 현재 줄을 취소할 수 있지만, 실행 child는 기본 `SIGINT` 정책으로 종료되게 할 수 있습니다. Readline callback, history와 signal policy는 [Readline 부록](../90-appendix/02-readline-integration.md)에서 다룹니다.

## 메모리 소유권 그래프

입력 처리에는 여러 할당 계층이 생깁니다.

```text
입력 줄
→ token 배열과 WORD 문자열
→ 인용 구간
→ 확장 결과
→ argv 배열
→ command / pipeline
```

각 단계가 이전 할당을 빌리는지, 복제하는지, 이동받는지 정합니다.

```c
void token_list_destroy(struct token_list *tokens);
void pipeline_destroy(struct pipeline *pipeline);
```

상위 객체가 소유한 하위 객체를 한 함수에서 모두 정리하면 부분 실패 경로가 단순해집니다. parser가 token 문자열의 소유권을 이동받았다면 원래 token 포인터를 비워 두 destroy 함수가 같은 메모리를 두 번 해제하지 않게 합니다.

## 동적 builder와 overflow

WORD와 argv는 입력 길이에 따라 성장합니다.

```text
필요 길이 덧셈 overflow 검사
→ capacity 성장 계산
→ realloc 결과를 임시 포인터에 받음
→ 성공 뒤 상태 교체
```

`argc + 2`는 새 인자 하나와 마지막 NULL 슬롯을 포함합니다. 바이트 크기를 계산할 때 `SIZE_MAX / sizeof(pointer)` 경계를 확인합니다.

입력 길이가 현실적으로 작다고 overflow 검사를 생략하면 parser의 공개 계약이 입력 크기에 따라 UB를 허용하게 됩니다.

## pipeline 생성 중 실패

N단 pipeline의 k번째 `fork`가 실패하면 이미 시작한 child가 있습니다.

- parent가 가진 모든 pipe FD를 닫습니다.
- 이미 시작한 child에 종료 정책을 적용합니다.
- 생성한 child만 `waitpid`합니다.
- PID 배열과 실행 계획을 해제합니다.
- parent 표준 FD를 바꿨다면 복구합니다.

fork 실패를 “아무 일도 없었던 상태”로 되돌릴 수는 없습니다. 실패 계약은 정리 가능한 범위를 정확히 말해야 합니다.

## 구현 순서

한 번에 완전한 셸을 만들지 않습니다.

1. WORD만 있는 단일 외부 명령
2. lexer token dump
3. 작은따옴표·큰따옴표·escape
4. 빈 인자와 붙은 인용 조각
5. 두 명령 pipeline
6. N단 pipeline
7. `<`, `>`, `>>` redirection
8. 변수 확장
9. 상태 변경 builtin
10. heredoc
11. 대화형 입력과 시그널
12. process group과 job control

각 단계는 이전 테스트를 유지한 채 확장합니다. 표현이 다음 기능의 의미를 보존하지 못한다면 기능을 억지로 추가하기 전에 중간 구조를 바꿉니다.

## 테스트를 계층별로 나눕니다

### lexer·parser 테스트

실제 프로세스를 만들지 않고 token 또는 구조를 검사합니다.

- 인용 제거와 단어 경계
- 빈 인자
- 붙은 인용 조각
- 열린 인용과 마지막 escape 거부
- 빈 pipeline 쪽과 pipe 개수 제한
- 부분 결과 누수 없음

### executor 테스트

검증된 구조를 직접 실행합니다.

- argv 전달
- pipeline의 큰 데이터
- 126·127과 signal 상태
- 마지막 command 상태 선택
- 모든 child 회수와 FD 정리

### 통합 테스트

입력 줄부터 실제 stdout·stderr·상태까지 확인합니다. host shell과 결과를 비교할 때는 지원 문법과 인용 규칙이 정확히 같은 사례만 사용합니다.

문법 오류의 “무효과”를 확인하려면 자식이 실행되면 파일을 만드는 helper를 준비하고, 잘못된 입력에서는 파일이 생기지 않는지 검사할 수 있습니다.

## 실습

[command-runner](../../exercises/03-unix-programming/04-command-runner/README.md)는 명령 문자열 하나를 받아 다음 범위만 구현합니다.

```text
WORD
작은따옴표·큰따옴표
escape
빈 인자와 붙은 인용 조각
인용되지 않은 pipe 최대 하나
외부 명령 실행
```

검증 항목:

- helper가 관찰한 실제 `argc`, 각 argv와 빈 문자열
- 열린 따옴표·마지막 escape·빈 command·두 개 이상 pipe 거부
- 문법 오류가 child 효과를 만들지 않음
- 없는 명령 127과 실행 불가 126
- signal 종료의 shell-style 상태
- pipeline의 마지막 command 상태
- 4 MiB pipeline과 timeout
- 반복 실행 뒤 독립 상태

대화형 prompt, redirection, 환경 확장, builtin, heredoc과 job control은 범위 밖입니다. 이 축소 문법은 인용되지 않은 `<`, `>`, `;`, `&`를 명시적으로 거부하고, 인용하거나 escape한 경우에만 일반 문자로 전달합니다. 범위 밖 문법을 구현된 것처럼 받아들이지 않습니다.

## 다음 단계

여러 command가 아니라 여러 thread가 같은 메모리를 공유하면 잠금과 시간 계약이 필요합니다. [스레드·동기화·시간](../04-concurrency/01-threads-time.md)에서 이어집니다.
