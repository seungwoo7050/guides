# 입력 오류와 디버깅: 실패를 분류하고 재현하기

프로그램이 실패했을 때 먼저 “어디가 틀렸는가”가 아니라 “어느 종류의 실패인가”를 나눕니다. 사용자가 잘못된 값을 준 경우와 프로그램이 유효하지 않은 메모리에 접근한 경우는 같은 오류 메시지로 처리할 문제가 아닙니다.

## 실패의 층

| 층 | 예 | 주된 대응 |
|---|---|---|
| 사용 계약 | 인자 누락, 숫자가 아닌 문자열 | 명확한 진단과 종료 상태 |
| 도메인 규칙 | 허용 범위 밖 값 | 입력 거부, 상태 보존 |
| 자원 실패 | 메모리·파일 열기 실패 | 부분 자원 정리와 오류 전파 |
| 코드 결함 | 범위 밖 접근, 잘못된 포인터 | 재현·디버거·sanitizer로 수정 |

코드 결함을 “입력이 잘못되었습니다”로 숨기지 않습니다.

## `strtol`로 숫자 전체 검증하기

`atoi`는 오류를 구분하기 어렵습니다. `strtol`은 변환 위치와 범위 오류를 확인할 수 있습니다.

```c
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>

int parse_long(const char *text, long *out_value)
{
    char *end;
    long value;

    if (text == NULL || out_value == NULL || *text == '\0' ||
        isspace((unsigned char)*text))
    {
        return -1;
    }
    errno = 0;
    end = NULL;
    value = strtol(text, &end, 10);
    if (errno == ERANGE || end == text || *end != '\0')
    {
        return -1;
    }
    *out_value = value;
    return 0;
}
```

확인 순서가 중요합니다.

1. 널 포인터, 빈 문자열과 앞 공백을 확인합니다.
2. `errno`를 0으로 초기화합니다.
3. 변환을 호출합니다.
4. 한 글자도 소비하지 않았는지 확인합니다.
5. 문자열 전체를 소비했는지 확인합니다.
6. 범위 오류인지 확인합니다.
7. 성공한 뒤에만 출력 매개변수를 변경합니다.

## 오류 메시지 계약

좋은 진단은 다음 질문에 답합니다.

- 어느 값이 문제였습니까?
- 기대 형식은 무엇입니까?
- 프로그램은 어떤 종료 상태로 끝났습니까?

```c
fprintf(stderr, "오류: 정수가 아닙니다: %s\n", argv[index]);
return 2;
```

자동 테스트가 정확한 문장 전체에 과도하게 결합되지 않도록, 안정된 핵심 단어나 접두사를 정할 수 있습니다.

## 최소 재현 만들기

오류를 고치기 전에 같은 실패를 반복해서 만들 수 있어야 합니다.

```text
실패한 명령
입력 파일 또는 인자
컴파일 옵션
실제 stdout·stderr·종료 상태
운영체제와 컴파일러
```

입력을 계속 줄여도 같은 실패가 나타나는지 확인합니다. 1000줄 입력이 필요하다고 생각했지만 실제 원인이 빈 마지막 줄 하나일 수 있습니다.

## 디버그 빌드

```sh
cc -std=c99 -Wall -Wextra -Wpedantic -g -O0 source.c -o program
```

- `-g`는 디버거가 소스 위치와 변수를 연결할 정보를 만듭니다.
- `-O0`은 처음 관찰할 때 코드 재배치를 줄입니다.
- 경고는 그대로 유지합니다.

최적화에서만 재현되는 결함도 있으므로, 문제를 해결한 뒤 원래 최적화 설정에서도 다시 확인합니다.

## 디버거의 최소 순환

GDB 예:

```sh
gdb ./program
(gdb) break main
(gdb) run 10 bad 30
(gdb) next
(gdb) print index
(gdb) print argv[index]
(gdb) backtrace
```

LLDB 예:

```sh
lldb ./program
(lldb) breakpoint set --name main
(lldb) run 10 bad 30
(lldb) next
(lldb) frame variable index
(lldb) bt
```

핵심 명령은 다음입니다.

- 실행 지점에 breakpoint를 둡니다.
- `next`로 현재 함수 안의 문장을 진행합니다.
- `step`으로 호출 함수 안에 들어갑니다.
- 변수를 출력합니다.
- `backtrace`로 현재 호출 경로를 확인합니다.

더 자세한 명령은 [디버거 부록](../90-appendix/01-debugger-reference.md)에 있습니다.

## sanitizer

```sh
cc -std=c99 -Wall -Wextra -Wpedantic -g \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    source.c -o program
ASAN_OPTIONS=detect_leaks=1 ./program
```

AddressSanitizer는 대표적으로 다음 결함을 찾습니다.

- heap·stack 범위 밖 접근
- 해제 뒤 사용
- 중복 해제
- 일부 메모리 누수

UndefinedBehaviorSanitizer는 정수, 정렬과 잘못된 연산의 일부를 찾습니다. 검사하지 않은 경로의 결함은 찾지 못하므로 테스트 입력이 필요합니다.

## 경고를 오류로 다루는 시점

학습 초기에는 경고 내용을 먼저 읽을 수 있어야 합니다. 연습문제와 자동 빌드에서는 `-Werror`를 사용해 새 경고가 누적되지 않게 합니다.

경고를 캐스트로 숨기기 전에 다음을 확인합니다.

- 타입 선택이 잘못되지 않았는가
- 부호 있는 값과 없는 값을 비교하지 않는가
- 형식 지정자와 인자 타입이 일치하는가
- 반환값을 실제로 확인해야 하지 않는가

## 실습의 완료 기준

[`number-report`](../../exercises/01-foundations/01-number-report/README.md)를 완성하고 다음을 확인합니다.

- 정상 숫자 여러 개
- 음수·0·같은 값
- 빈 인자와 숫자가 아닌 입력
- 공백이나 뒤 문자가 붙은 입력
- `long` 범위 밖 입력
- 합 오버플로
- stdout·stderr 분리
- 종료 상태
- sanitizer 실행

이 연습을 독립적으로 완료하면 Part 2로 넘어갈 최소 개발 순환을 갖춘 것입니다.
