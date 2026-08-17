# GNU Readline을 활용한 대화형 입력 설계

대화형 프로그램에서 한 줄을 읽는 것과 사용자가 편집할 수 있는 입력 환경을 제공하는 것은 서로 다른 문제입니다. 화살표 키 이동, 명령 기록, 검색과 자동 완성을 직접 구현하려면 터미널 모드와 이스케이프 시퀀스까지 다뤄야 합니다. GNU Readline은 이러한 사용자 인터페이스 계층을 선택적으로 제공합니다.

Readline이 렉서, 파서와 실행기의 역할까지 대신하는 것은 아닙니다. 대화형 입력 어댑터를 핵심 로직과 분리해야 파일·파이프 입력과 자동 테스트에서도 같은 파서 경로를 사용할 수 있습니다.

## 핵심 API와 소유권

```c
#include <readline/history.h>
#include <readline/readline.h>
#include <stdlib.h>
```

```c
char *line = readline("mini> ");
```

`readline`은 프롬프트를 표시하고 사용자가 편집할 수 있는 한 줄을 읽습니다. 일반적으로 줄바꿈 문자를 제외한 새 문자열을 할당해 반환하며, EOF에서는 `NULL`을 반환합니다.

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

반환된 문자열은 호출자가 `free`해야 합니다. 빈 문자열 `""`과 EOF를 나타내는 `NULL`은 서로 다른 상태입니다.

## 가장 단순한 반복 구조

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

`process_line`이 문자열을 빌려서 사용하는 구조라면 함수가 반환되기 전에 모든 처리를 마쳐야 합니다.

파서가 문자열 일부를 뷰 형태로 보관한다면 `line`을 먼저 해제해서는 안 됩니다. 필요한 내용을 복제하거나 문자열 소유권 자체를 넘기는 API라면 그 사실을 인터페이스 계약에 명시합니다.

## 입력 계층에 책임 위임하기

직접 한 줄 입력기를 구현하면 프로그램이 버퍼 확장, 줄바꿈 처리와 EOF 처리를 모두 담당합니다. 반면 Readline을 호출하면 함수가 반환될 때까지 터미널 제어와 편집 처리를 라이브러리에 맡깁니다.

```text
프로그램 → readline(prompt)
          터미널 모드와 키 입력 처리
          history·자동 완성 처리
프로그램 ← 호출자가 해제할 문자열
```

파일이나 파이프 입력에는 편집할 사용자가 없으며 프롬프트가 출력 계약을 오염시킬 수도 있습니다. 따라서 대화형 여부에 따라 입력 어댑터를 선택합니다.

## 대화형 여부 판단하기

가장 기본적인 기준은 표준 입력이 터미널인지 확인하는 것입니다.

```c
int interactive = isatty(STDIN_FILENO);
```

프롬프트를 출력할 스트림도 프로그램의 계약에 맞게 정해야 합니다. GNU Readline은 `rl_outstream`을 사용하며 기본값은 환경과 구현 설정에서 확인해야 합니다. 정상 출력과 프롬프트를 분리하려면 대화형 초기화 단계에서 출력 스트림을 명시적으로 지정할 수 있습니다.

```c
rl_outstream = stderr;
```

이 경우에는 표준 오류도 터미널인지 확인하는 정책을 사용할 수 있습니다.

```c
int interactive =
    isatty(STDIN_FILENO) && isatty(STDERR_FILENO);
```

실제 조건은 프로그램의 입출력 계약에 따라 달라집니다.

```text
stdin이 tty       사용자가 직접 키를 입력하고 편집할 수 있음
stdin이 pipe/file 자동 입력이므로 프롬프트와 Readline을 우회
```

프롬프트를 표준 출력에 쓰면 파이프라인의 정상 출력에 섞일 수 있습니다. 대화형 UI 출력과 프로그램의 정상 결과 출력을 구분해야 합니다.

## 같은 API 뒤에 대체 입력기 두기

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

호출부는 Readline 사용 여부를 알 필요가 없습니다.

두 입력 경로가 같은 외부 계약을 제공하면 파서도 단순하게 유지할 수 있습니다.

```text
성공    호출자가 free할 문자열
EOF     NULL
개행    결과 문자열에서는 제거
빈 줄   길이 0인 문자열
```

포인터 하나만으로 EOF와 I/O 오류를 구분해야 하는 요구를 충족할 수 없다면 상태 열거형과 출력 매개변수를 사용하는 어댑터로 확장할 수 있습니다.

## UI·파서·실행기의 경계

```text
Readline/plain adapter
  입력 한 줄, EOF 또는 오류 제공

lexer/parser
  문자열을 command 구조로 변환

executor
  검증된 구조를 실행하고 상태 반환
```

다음과 같은 의존 관계는 피합니다.

```text
parser가 Readline 전역 상태를 직접 변경
executor가 프롬프트를 출력
시그널 핸들러가 parser의 할당을 해제
```

`command-runner`처럼 문자열 인자를 직접 받는 비대화형 진입점을 유지하면 파서와 실행기를 의사 터미널 없이 자동으로 검증할 수 있습니다.

## 선택적 의존성과 빌드

기본 빌드는 외부 라이브러리 없이 유지하고 대화형 기능만 기능 플래그로 활성화할 수 있습니다.

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

전처리 매크로만 활성화하고 라이브러리를 링크하지 않으면 미정의 심볼 오류가 발생합니다.

반대로 라이브러리만 링크하고 매크로를 활성화하지 않으면 Readline을 사용하는 코드 경로 자체가 빌드되지 않습니다.

이 저장소의 `prepare.sh`는 실제 탐지용 프로그램을 컴파일해 Readline을 사용할 수 있는지 확인하고 필요한 플래그를 기록합니다. `verify.sh`는 확인된 환경에서만 선택적인 Readline 빌드를 실행합니다.

## 설치 경로를 소스 코드에 고정하지 않습니다

운영체제나 패키지 관리자에 따라 헤더와 라이브러리의 설치 경로가 달라집니다.

```sh
pkg-config --cflags readline
pkg-config --libs readline
```

`pkg-config` 메타데이터가 제공되지 않는 환경도 있으므로 다음 경로를 순서대로 고려합니다.

- 컴파일러의 기본 헤더·라이브러리 검색 경로
- `pkg-config`가 제공하는 플래그
- 사용자가 전달하는 `READLINE_CPPFLAGS`, `READLINE_LDFLAGS`, `READLINE_LDLIBS`
- 패키지 관리자가 제공하는 prefix
- Readline이 없는 환경에서 사용할 일반 입력기

공개 소스 코드나 Makefile에 특정 시스템의 절대 경로를 고정해서는 안 됩니다.

## Readline과 시그널

Readline은 터미널과 라이브러리의 전역 상태를 관리합니다.

일반 시그널 핸들러에서 `readline`, `printf`, `malloc`이나 임의의 Readline API를 호출해서는 안 됩니다.

GNU Readline은 자체 시그널 처리 기능을 제공할 수 있습니다. 이 기능을 사용할지, 비활성화하고 애플리케이션이 직접 시그널과 터미널 상태를 관리할지를 먼저 정해야 합니다. 두 정책을 불완전하게 섞으면 터미널 복원과 핸들러 설치 상태가 충돌할 수 있습니다.

대화형 셸에서는 다음과 같은 정책을 둘 수 있습니다.

```text
프롬프트 대기 중 SIGINT
  현재 줄 취소
  새 프롬프트 표시
  부모 셸은 계속 실행

외부 명령 실행 중 SIGINT
  포그라운드 자식이 기본 동작으로 종료
  부모는 자식 상태를 회수한 뒤 새 프롬프트 표시

SIGQUIT
  프롬프트에서는 무시하거나 별도 정책 적용
  자식에서는 기본 동작
```

애플리케이션이 시그널 정책을 직접 관리한다면 기본 구조는 다음과 같습니다.

1. 핸들러에서는 `sig_atomic_t` 플래그를 설정하거나 self-pipe를 깨웁니다.
2. 일반 제어 흐름에서 현재 입력을 취소하고 화면을 다시 표시합니다.
3. `fork`한 자식 프로세스는 `exec` 전에 필요한 시그널 동작을 `SIG_DFL`로 복원합니다.

어느 계층이 시그널과 터미널 상태를 책임지는지 명확하게 정해야 합니다.

## 블로킹 API와 콜백 API

작은 프로그램이라면 블로킹 방식의 `readline()`만으로 충분합니다.

하나의 이벤트 루프에서 소켓, self-pipe와 터미널 입력을 함께 감시해야 할 때만 콜백 API를 고려합니다.

```text
Readline 콜백 설치
→ 이벤트 루프에서 stdin readable 상태 감지
→ Readline에 한 단계 입력 처리 요청
→ 완성된 줄을 콜백으로 전달
→ 콜백 제거와 터미널 상태 복원
```

콜백 API는 전역 상태와 Readline 버전의 세부 동작에 더 많이 의존합니다. 단순한 셸에 처음부터 도입할 필요는 없습니다.

## 현재 입력 줄 취소와 다시 표시하기

Ctrl-C를 입력한 뒤 현재 편집 중인 줄을 버리고 새 프롬프트를 표시하려면 Readline의 줄 초기화·다시 표시 API가 필요할 수 있습니다.

이 API를 시그널 핸들러 안에서 직접 조합하기보다 일반 제어 흐름이나 공식 콜백·이벤트 훅에서 처리합니다.

다음 상태를 확인합니다.

- 편집 중인 버퍼의 소유자는 누구인가?
- 취소한 줄을 히스토리에 추가할 것인가?
- 터미널 모드가 정상적으로 복원되었는가?
- 프롬프트가 중복해서 출력되지 않는가?
- 비대화형 입력에서 같은 시그널은 어떤 의미를 갖는가?

## 히스토리 정책

```c
if (line[0] != '\0')
{
    add_history(line);
}
```

단순히 `add_history`를 호출하는 것보다 어떤 입력을 기록할지 정하는 애플리케이션 정책이 더 중요합니다.

- 빈 줄도 저장할 것인가?
- 연속된 중복 입력을 제거할 것인가?
- 앞쪽 공백으로 시작한 줄은 민감한 명령으로 간주해 제외할 것인가?
- 최대 보관 개수를 제한할 것인가?
- 프로그램 종료 시 파일에 저장할 것인가?
- 여러 인스턴스가 만든 히스토리를 어떻게 병합할 것인가?
- 비밀번호·토큰·개인정보를 기록하지 않을 방법이 있는가?

히스토리 파일을 사용한다면 저장 경로, 파일 권한, 심볼릭 링크와 쓰기 실패까지 처리해야 합니다.

민감한 정보를 무조건 영구 저장해서는 안 됩니다.

GNU Readline과 일부 호환 구현에서 공통으로 사용할 수 있는 비교적 좁은 순회 방식으로 `history_get`을 사용할 수 있습니다.

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

반환된 `HIST_ENTRY`와 내부 문자열은 히스토리 라이브러리가 관리합니다. 호출자가 임의로 해제하거나 라이브러리 상태를 정리한 뒤 계속 보관해서는 안 됩니다.

## 자동 완성

Readline에는 사용자 정의 자동 완성 함수를 등록할 수 있습니다.

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

생성 함수는 같은 `text`를 대상으로 `state == 0, 1, 2, ...` 순서로 호출됩니다.

각 호출에서는 일치하는 후보를 새로 할당한 문자열로 반환하고, 더 이상 후보가 없으면 `NULL`을 반환합니다. 후보 문자열은 Readline의 완성 계약에 따라 라이브러리가 관리할 수 있도록 반환해야 합니다.

자동 완성 후보가 외부 레지스트리나 환경 목록의 데이터를 빌려 사용한다면 완성 과정이 끝날 때까지 해당 데이터가 유효해야 합니다.

다른 스레드가 동시에 후보 목록을 수정할 수 있다면 별도의 동기화도 필요합니다.

자동 완성은 파서와 같은 문법 정보를 알아야 할 수 있습니다.

```text
명령 위치           실행 파일·내장 명령 후보
리다이렉션 대상     파일 후보
환경 변수 위치      변수 이름 후보
인용 상태           이스케이프와 삽입 정책 변경
```

단순히 공백 앞의 문자열만 기준으로 처리하면 따옴표나 이스케이프가 포함된 입력에서 잘못된 후보를 삽입할 수 있습니다.

## GNU Readline과 libedit

일부 시스템에서는 Readline 호환 헤더를 libedit에 연결해 제공합니다.

`readline`, `add_history`, `history_get` 같은 기본 API를 사용할 수 있더라도 다음 세부 사항은 달라질 수 있습니다.

- 자동 완성 콜백의 세부 동작
- 제공되는 히스토리 확장 API
- 시그널과 터미널 처리 방식
- 사용할 수 있는 전역 변수
- 라이선스

예제에서는 호환 범위를 넓히기 위해 `history_list()` 같은 구현별 확장보다 `history_get`, `history_base`, `history_length`를 사용합니다.

특정 GNU 확장이 반드시 필요하다면 구성 또는 탐지 단계에서 해당 API 자체를 사용할 수 있는지 확인해야 합니다.

최종 기준은 실제 설치된 헤더와 해당 버전의 공식 문서입니다.

## 메모리와 종료 정리

프로세스가 종료될 때 운영체제가 메모리를 회수하더라도 반복적으로 사용할 수 있는 라이브러리 코드에서는 객체의 수명을 끝까지 명확하게 정리합니다.

- `readline`이 반환한 문자열을 매 반복마다 `free`
- 파서 실패와 실행 성공 경로 모두에서 입력 문자열 정리
- 콜백 모드를 사용했다면 콜백 핸들러 제거
- 변경한 시그널 동작과 터미널 상태 복원
- 히스토리를 영구 저장한다면 쓰기 결과 확인

파서가 `line`의 소유권을 넘겨받았다면 호출자가 다시 `free(line)`을 호출하지 않도록 소유권 경계를 명확히 해야 합니다.

## 자동 테스트의 경계

비대화형 입력 경로는 일반적인 프로세스 테스트로 비교적 쉽게 검증할 수 있습니다.

```sh
printf 'echo hello\nquit\n' | ./repl
```

다음 사항을 확인합니다.

- 프롬프트가 `stdout`에 섞이지 않는가?
- EOF에서 정상적으로 종료하는가?
- 빈 줄이 파서 오류로 처리되지 않는가?
- 일반 입력기와 Readline 경로가 같은 파서 결과를 만드는가?
- 각 입력 줄에 할당된 메모리를 정상적으로 정리하는가?

`readline-check`에서는 Readline 경로가 현재 헤더와 라이브러리 조합으로 실제 컴파일·링크되는지도 확인합니다.

그러나 파이프 입력에서는 일반 입력기를 사용하므로 화살표 키 편집이나 자동 완성까지 검증하는 것은 아닙니다.

화살표 키 편집, Ctrl-R, Tab 자동 완성, Ctrl-C 이후 프롬프트 복원과 같은 기능은 의사 터미널 통합 테스트나 수동 검사가 필요합니다.

이 검사는 터미널 크기, 로캘과 타이밍의 영향을 받으므로 핵심 파서 테스트를 대체해서는 안 됩니다. 좁은 범위의 UI 계약만 별도로 확인합니다.

## 수동 검사와 의사 터미널 검사

수동 검사에서는 다음 항목을 확인할 수 있습니다.

```text
왼쪽·오른쪽 화살표 이동
Home/End 또는 이에 해당하는 키 동작
위·아래 히스토리 탐색
Ctrl-R 검색
Tab 자동 완성
Ctrl-C로 현재 줄 취소
빈 줄에서 Ctrl-D 입력 시 EOF 처리
긴 줄과 다중 바이트 문자
터미널 크기 변경 뒤 프롬프트 표시
```

의사 터미널 테스트에서는 자식 프로세스 그룹을 만들고 제한 시간이 초과되었을 때 전체 그룹을 정리해야 합니다.

Ctrl-C를 단순히 `kill(pid, SIGINT)`로 전달하는 것과 터미널의 포그라운드 프로세스 그룹에 제어 문자를 입력하는 것은 작업 제어 관점에서 같은 동작이 아닐 수 있습니다.

## 기존 예제와 연결하기

[`examples/readline-repl`](../../examples/readline-repl/README.md)은 다음 내용을 보여 줍니다.

- TTY에서는 Readline 사용
- 파이프 입력에서는 일반 입력기 사용
- 비어 있지 않은 줄을 히스토리에 추가
- EOF 처리와 반환 문자열 해제
- 첫 번째 단어에 대한 명령 자동 완성
- 공통 히스토리 API를 이용한 목록 출력
- `USE_READLINE`을 이용한 조건부 빌드
- 설치 경로를 외부 플래그로 전달하는 방식

```sh
./prepare.sh
make readline-check
make -C examples/readline-repl run-readline
```

Readline 개발 파일이 없는 환경에서도 기본 문서, 예제와 실습은 계속 빌드되어야 합니다.

`verify.sh`는 해당 검사만 건너뛰고, `VERIFY_REQUIRE_OPTIONAL=1`이 설정된 경우에는 선택 기능을 사용할 수 없어 검사를 건너뛴 상황도 실패로 처리합니다.

## 점검 질문

1. `readline`이 반환한 문자열은 누가 해제합니까?
2. 빈 문자열과 EOF를 구분해야 하는 이유는 무엇입니까?
3. 파이프 입력에서 Readline과 프롬프트를 우회해야 하는 이유는 무엇입니까?
4. Readline 경로와 일반 입력기가 같은 반환 계약을 제공해야 하는 이유는 무엇입니까?
5. 전처리 매크로와 링크 옵션을 함께 설정해야 하는 이유는 무엇입니까?
6. 시그널 핸들러에서 일반 Readline API를 직접 호출하면 왜 위험합니까?
7. 자식 프로세스의 시그널 동작을 `exec` 전에 복원해야 하는 이유는 무엇입니까?
8. 자동 완성 생성 함수가 반환한 문자열은 어떤 계약에 따라 관리됩니까?
9. 히스토리 영속화가 보안과 개인정보 문제를 일으킬 수 있는 이유는 무엇입니까?
10. `history_get` 같은 공통 API와 구현별 확장을 구분해야 하는 이유는 무엇입니까?
11. 파서 테스트와 의사 터미널 UI 테스트를 분리해야 하는 이유는 무엇입니까?
