# GNU Readline과 대화형 입력 통합

대화형 프로그램에서 한 줄을 읽는 일과 편집 가능한 입력 환경을 제공하는 일은 다릅니다. 화살표 이동, history, 검색과 자동 완성을 직접 구현하려면 터미널 모드와 escape sequence를 함께 다뤄야 합니다. GNU Readline은 이 사용자 인터페이스 계층을 선택적으로 제공합니다.

Readline은 lexer, parser와 executor를 대신하지 않습니다. 대화형 입력 adapter를 핵심 로직과 분리해야 파일·파이프 입력과 자동 테스트가 같은 parser 경로를 사용할 수 있습니다.

## 핵심 API와 소유권

```c
#include <readline/history.h>
#include <readline/readline.h>
#include <stdlib.h>
```

```c
char *line = readline("mini> ");
```

`readline`은 프롬프트를 표시하고 편집 가능한 한 줄을 읽습니다. 일반적으로 개행을 제외한 새 할당을 반환하고 EOF에서는 `NULL`을 반환합니다.

```c
if (line == NULL)
{
    /* Ctrl-D 또는 입력 종료 */
}
else
{
    process_line(line);
    free(line);
}
```

반환 문자열은 호출자가 `free`합니다. 빈 문자열 `""`과 EOF `NULL`은 서로 다른 상태입니다.

## 가장 작은 반복 구조

```c
for (;;)
{
    char *line = readline("mini> ");

    if (line == NULL)
    {
        break;
    }
    if (line[0] != '\0')
    {
        add_history(line);
    }
    process_line(line);
    free(line);
}
```

`process_line`이 문자열을 빌려 사용한다면 반환 전에 모든 처리를 끝내야 합니다. parser가 문자열 일부를 view로 보관한다면 `line`을 먼저 해제할 수 없습니다. 필요한 내용을 복제하거나 소유권을 넘기는 API라면 그 사실을 계약에 드러냅니다.

## 입력 책임의 위임

직접 줄 reader를 사용하면 프로그램이 버퍼 성장, 개행과 EOF를 처리합니다. Readline을 호출하면 반환할 때까지 터미널 제어와 편집을 라이브러리에 위임합니다.

```text
프로그램 → readline(prompt)
          터미널 모드와 키 처리
          history·완성 처리
프로그램 ← 호출자가 해제할 문자열
```

파일이나 파이프 입력에는 편집할 사용자가 없고 prompt가 출력 계약을 오염시킬 수 있습니다. 대화형 여부에 따라 adapter를 선택합니다.

## 대화형 여부

```c
int interactive = isatty(STDIN_FILENO) && isatty(STDERR_FILENO);
```

stdin이 터미널인지가 가장 일반적인 기준입니다. 예제가 stderr까지 확인하는 이유는 prompt가 stderr에 표시되는 계약을 사용하기 때문입니다. 프로그램의 입출력 계약에 따라 조건은 달라질 수 있습니다.

```text
stdin이 tty       사용자가 키를 입력하고 편집 가능
stdin이 pipe/file 자동 입력, prompt와 Readline을 우회
```

prompt를 stdout에 쓰면 pipeline 결과에 섞일 수 있습니다. 대화형 UI 출력과 프로그램의 정상 결과를 구분합니다.

## 같은 API 뒤에 fallback을 둡니다

```c
char *read_command_line(const char *prompt, int interactive)
{
#ifdef USE_READLINE
    if (interactive)
    {
        return readline(prompt != NULL ? prompt : "");
    }
#endif
    return read_plain_line(prompt, interactive);
}
```

호출부는 Readline 사용 여부를 몰라도 됩니다. 두 경로가 같은 외부 계약을 반환해야 parser가 단순해집니다.

```text
성공    호출자가 free할 문자열
EOF     NULL
개행    결과 문자열에서 제거
빈 줄   길이 0인 문자열
```

포인터 하나만으로 EOF와 I/O 오류를 구분할 수 없다면 상태 enum과 출력 매개변수를 사용하는 adapter로 확장합니다.

## UI·parser·executor 경계

```text
Readline/plain adapter
  입력 한 줄, EOF 또는 오류 제공

lexer/parser
  문자열을 command 구조로 변환

executor
  검증된 구조를 실행하고 상태 반환
```

다음 의존 방향을 피합니다.

```text
parser가 Readline 전역 상태를 직접 변경
executor가 prompt를 출력
signal handler가 parser 할당을 해제
```

`command-runner`처럼 문자열 인자를 받는 비대화형 진입점을 유지하면 parser와 executor를 pseudo-terminal 없이 자동 검증할 수 있습니다.

## 선택적 의존성과 빌드

기본 빌드는 외부 라이브러리 없이 유지하고, 대화형 기능을 feature flag로 켤 수 있습니다.

```make
USE_READLINE ?= 0
READLINE_CPPFLAGS ?=
READLINE_LDFLAGS ?=
READLINE_LDLIBS ?= -lreadline

ifeq ($(USE_READLINE),1)
CPPFLAGS += -DUSE_READLINE $(READLINE_CPPFLAGS)
LDFLAGS += $(READLINE_LDFLAGS)
LDLIBS += $(READLINE_LDLIBS)
endif
```

```c
#ifdef USE_READLINE
#include <readline/history.h>
#include <readline/readline.h>
#endif
```

전처리 매크로만 켜고 라이브러리를 링크하지 않으면 undefined symbol이 생깁니다. 라이브러리만 링크하고 매크로를 켜지 않으면 Readline 경로가 빌드되지 않습니다.

이 저장소의 `prepare.sh`는 실제 probe 프로그램을 컴파일해 Readline 사용 가능 여부와 필요한 플래그를 기록합니다. `verify.sh`는 확인된 환경에서만 선택적 Readline 빌드를 실행합니다.

## 설치 경로를 소스에 하드코딩하지 않습니다

운영체제나 package manager에 따라 header와 library 경로가 다릅니다.

```sh
pkg-config --cflags readline
pkg-config --libs readline
```

`pkg-config` metadata가 없는 환경도 있으므로 다음 경로를 순서대로 고려합니다.

- 컴파일러의 기본 header·library 검색 경로
- `pkg-config`가 제공하는 플래그
- 사용자가 넘기는 `READLINE_CPPFLAGS`, `READLINE_LDFLAGS`, `READLINE_LDLIBS`
- package manager가 제공하는 prefix
- Readline이 없는 환경의 plain-reader fallback

절대 경로를 공개 소스나 Makefile에 고정하지 않습니다.

## Readline과 시그널

Readline은 터미널과 전역 라이브러리 상태를 관리합니다. 일반 signal handler에서 `readline`, `printf`, `malloc` 또는 임의의 Readline API를 호출하지 않습니다.

대화형 셸의 정책 예:

```text
prompt 대기 중 SIGINT
  현재 줄 취소
  새 prompt 표시
  부모 셸은 계속

외부 command 실행 중 SIGINT
  foreground child가 기본 동작으로 종료
  부모는 child 상태를 회수하고 새 prompt 표시

SIGQUIT
  prompt에서는 무시 또는 별도 정책
  child에서는 기본 동작
```

안전한 기본 구조는 다음과 같습니다.

1. handler는 `sig_atomic_t` flag를 설정하거나 self-pipe를 깨웁니다.
2. 정상 제어 흐름이 현재 입력 취소와 UI 갱신을 수행합니다.
3. fork한 child는 exec 전에 필요한 signal disposition을 `SIG_DFL`로 복원합니다.

Readline 자체의 signal 처리와 애플리케이션 정책을 반쯤 섞으면 terminal 상태 복원이 충돌할 수 있습니다. 어느 계층이 책임지는지 명시합니다.

## 블로킹 API와 callback API

가장 작은 프로그램은 블로킹 `readline()`으로 충분합니다. 하나의 event loop가 socket, self-pipe와 terminal을 함께 감시해야 할 때만 callback API를 고려합니다.

```text
Readline callback 설치
→ event loop가 stdin readable 관찰
→ Readline에 한 단계 입력 처리 요청
→ 완성된 줄 callback
→ callback 제거와 terminal 상태 복원
```

callback API는 전역 상태와 라이브러리 버전에 더 의존합니다. 단순 셸에 미리 도입하지 않습니다.

## 현재 줄 취소와 다시 표시

Ctrl-C 뒤 현재 line buffer를 버리고 새 prompt를 표시하려면 Readline의 line reset·redisplay API가 필요할 수 있습니다. 이를 signal handler 안에서 직접 조합하지 말고 정상 흐름 또는 공식 callback/event hook에서 수행합니다.

확인할 상태:

- 편집 중인 buffer를 누가 소유합니까?
- 취소한 줄을 history에 추가합니까?
- terminal mode가 복원됐습니까?
- prompt가 중복 출력되지 않습니까?
- 비대화형 입력에서 같은 signal은 어떤 의미입니까?

## history 정책

```c
if (line[0] != '\0')
{
    add_history(line);
}
```

라이브러리 호출보다 애플리케이션 정책이 중요합니다.

- 빈 줄을 저장합니까?
- 연속 중복을 제거합니까?
- 앞 공백으로 시작한 줄을 민감한 명령으로 보고 제외합니까?
- 최대 개수를 제한합니까?
- 종료할 때 파일에 저장합니까?
- 여러 인스턴스의 history를 어떻게 병합합니까?
- 비밀번호·token·개인정보를 저장하지 않을 방법이 있습니까?

history 파일을 사용하면 경로, 권한, symlink와 쓰기 실패를 처리합니다. 민감한 값을 무조건 영속화하면 안 됩니다.

GNU Readline과 일부 호환 구현에서 공통으로 사용할 수 있는 좁은 순회 방식은 `history_get`입니다.

```c
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
```

반환된 `HIST_ENTRY`와 문자열은 history 라이브러리가 관리합니다. 임의로 해제하거나 라이브러리 정리 뒤 보관하지 않습니다.

## 자동 완성

Readline은 사용자 완성 함수를 등록할 수 있습니다.

```c
rl_attempted_completion_function = complete_command;
```

```c
static char **complete_command(
    const char *text,
    int start,
    int end
)
{
    (void)end;
    if (start != 0)
    {
        return NULL;
    }
    return rl_completion_matches(text, command_generator);
}
```

generator는 같은 `text`에 대해 `state == 0, 1, 2, ...`로 호출됩니다. 각 일치 후보를 새 할당으로 반환하고 끝나면 `NULL`을 반환합니다. 후보 문자열의 소유권은 Readline 계약에 따라 라이브러리로 넘어갑니다.

완성 후보가 외부 registry나 환경 목록을 빌린다면 완성 호출 동안 해당 데이터가 살아 있어야 합니다. 다른 스레드가 동시에 후보 목록을 변경한다면 synchronization이 필요합니다.

완성은 parser와 같은 문법을 알아야 할 수 있습니다.

```text
command 위치       실행 파일·builtin 후보
redirection target 파일 후보
환경 변수 위치     변수 이름 후보
인용 상태           escape와 삽입 정책 변경
```

단순히 공백 앞 문자열만 보면 따옴표와 escape가 있는 입력에서 잘못된 후보를 삽입할 수 있습니다.

## GNU Readline과 libedit

일부 시스템은 Readline 호환 header를 libedit에 연결합니다. `readline`, `add_history`, `history_get` 같은 기본 API는 제공될 수 있지만 다음은 다를 수 있습니다.

- 자동 완성 callback 세부 동작
- 제공되는 history 확장 API
- signal·terminal 처리
- 사용할 수 있는 전역 변수
- 라이선스

예제는 호환 범위를 넓히기 위해 `history_list()` 같은 구현별 확장보다 `history_get`, `history_base`, `history_length`를 사용합니다. 특정 GNU 확장이 필요하다면 `configure` 또는 probe 단계에서 그 API 자체를 확인해야 합니다. 설치된 header와 해당 버전의 공식 문서가 최종 기준입니다.

## memory와 종료 정리

프로세스 종료가 메모리를 운영체제에 반환하더라도 반복 가능한 library code에서는 수명을 끝까지 정리합니다.

- `readline` 반환 문자열을 매 반복 `free`
- parser 실패와 실행 성공 모두에서 line 정리
- callback mode라면 callback handler 제거
- 변경한 signal disposition과 terminal 상태 복원
- history 영속화를 사용한다면 write 결과 확인

`free(line)`을 parser가 소유권을 가져간 뒤 중복 호출하지 않도록 경계를 명확히 합니다.

## 자동 테스트 경계

비대화형 경로는 일반 process test로 검증하기 쉽습니다.

```sh
printf 'echo hello\nquit\n' | ./repl
```

확인할 것:

- prompt가 stdout에 섞이지 않습니다.
- EOF에서 정상 종료합니다.
- 빈 줄이 parser 오류가 되지 않습니다.
- plain reader와 Readline 경로가 같은 parser 결과를 만듭니다.
- 각 입력 줄 할당을 정리합니다.

`readline-check`는 Readline 경로가 현재 header와 library 조합으로 컴파일·링크되는지도 확인합니다. 그러나 pipe 입력에서는 plain reader를 사용하므로 화살표 편집과 완성 동작까지 증명하지는 않습니다.

화살표 편집, Ctrl-R, Tab 완성, Ctrl-C 뒤 prompt 복원은 pseudo-terminal 통합 테스트나 수동 검사가 필요합니다. 이 검사는 terminal size, locale와 timing에 영향을 받으므로 핵심 parser 검사를 대체하지 않고 좁은 UI 계약만 확인합니다.

## 수동 검사와 pseudo-terminal 검사

수동 체크리스트 예:

```text
왼쪽·오른쪽 화살표 이동
Home/End 또는 동등 키
위·아래 history
Ctrl-R 검색
Tab 완성
Ctrl-C 현재 줄 취소
Ctrl-D 빈 줄에서 EOF
긴 줄과 다중 바이트 문자
terminal resize 뒤 prompt
```

pseudo-terminal 테스트는 자식 process group을 만들고 timeout 뒤 전체 그룹을 회수해야 합니다. Ctrl-C를 단순히 `kill(pid, SIGINT)`로 보내는 것과 terminal foreground group에 제어 문자를 입력하는 것은 job-control 관점에서 같지 않을 수 있습니다.

## 기존 예제와 연결

`examples/readline-repl`은 다음을 보여 줍니다.

- tty에서 Readline 사용
- pipe 입력에서 일반 reader 사용
- 비어 있지 않은 줄의 history 추가
- EOF 처리와 반환 문자열 해제
- 첫 단어 command 자동 완성
- 공통 history API를 사용한 목록 출력
- `USE_READLINE` 조건부 빌드
- 설치 경로를 외부 플래그로 주입하는 방식

```sh
./prepare.sh
make readline-check
make -C examples/readline-repl run-readline
```

Readline 개발 파일이 없는 환경에서는 기본 문서·예제와 exercise가 계속 빌드되어야 합니다. `verify.sh`는 해당 검사만 skip하고, `VERIFY_REQUIRE_OPTIONAL=1`일 때는 skip을 실패로 취급합니다.

## 점검 질문

1. `readline` 반환 문자열은 누가 해제합니까?
2. 빈 문자열과 EOF를 왜 구분해야 합니까?
3. pipe 입력에서 Readline과 prompt를 우회해야 하는 이유는 무엇입니까?
4. Readline 경로와 plain reader의 반환 계약을 같게 해야 하는 이유는 무엇입니까?
5. 전처리 매크로와 링크 옵션을 함께 설정해야 하는 이유는 무엇입니까?
6. signal handler에서 일반 Readline API를 직접 호출하면 왜 위험합니까?
7. child의 signal disposition을 exec 전에 복원해야 하는 이유는 무엇입니까?
8. 자동 완성 generator가 반환한 문자열의 소유권은 어디로 갑니까?
9. history 영속화가 보안과 개인정보 문제를 만들 수 있는 이유는 무엇입니까?
10. `history_get` 같은 공통 API와 구현별 확장을 구분해야 하는 이유는 무엇입니까?
11. parser test와 pseudo-terminal UI test를 분리해야 하는 이유는 무엇입니까?
