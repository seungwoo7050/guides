# 빌드·링크·테스트: 반복 가능한 개발 환경

빌드 도구를 배우는 목적은 Makefile 문법을 외우는 것이 아닙니다. 어떤 입력이 어떤 결과를 만들고, 무엇이 바뀌었을 때 어느 단계만 다시 실행해야 하는지 명시하는 것입니다.

## 직접 명령에서 시작하기

```sh
cc -Iinclude -std=c99 -Wall -Wextra -Wpedantic -c src/textkit.c -o textkit.o
ar rcs libtextkit.a textkit.o
cc -Iinclude app/main.c libtextkit.a -o textstat
cc -Iinclude tests/test_textkit.c libtextkit.a -o test_textkit
./test_textkit
```

먼저 이 명령을 직접 이해한 뒤 반복을 Makefile로 옮깁니다.

## 산출물 그래프와 단계별 옵션

빌드는 명령 목록이 아니라 의존 그래프입니다.

```text
src/textkit.c + include/textkit.h → build/textkit.o
src/main.c    + include/textkit.h → build/main.o
build/textkit.o                  → build/libtextkit.a
build/main.o + build/libtextkit.a → build/textstat
tests/test_textkit.c + build/libtextkit.a → build/test_textkit
```

각 화살표는 어떤 입력이 바뀌면 어떤 산출물을 다시 만들어야 하는지 말합니다.

컴파일 옵션은 각 번역 단위의 진단과 코드 생성에 영향을 줍니다. 링크 옵션은 최종 파일 조립, 라이브러리 탐색과 런타임 연결에 영향을 줍니다. 특별한 이유가 없다면 `ld`를 직접 호출하지 않고 C compiler driver를 사용합니다. driver가 시작 코드와 기본 라이브러리를 올바른 순서로 연결합니다.

## 오브젝트 파일과 심볼

오브젝트 파일은 자신이 정의한 이름과 아직 필요한 이름을 기록합니다.

```text
main.o
  defines: main
  needs:   textkit_length, printf

textkit.o
  defines: textkit_length
```

대표적인 링크 실패는 다음 두 종류입니다.

- 미정의 심볼: 필요한 정의가 최종 링크에 없음
- 중복 정의: 외부 링크 이름을 둘 이상의 번역 단위가 정의함

헤더의 선언은 컴파일러가 호출을 검사하게 할 뿐 최종 정의를 만들지 않습니다. 변경 가능한 전역 객체는 헤더에서 `extern`으로 선언하고 정확히 한 `.c` 파일에서 정의합니다.

```c
/* counter.h */
extern unsigned long global_count;

/* counter.c */
unsigned long global_count = 0;
```

산출물을 직접 관찰하면 링크 오류를 좁히기 쉽습니다.

```sh
nm build/main.o
nm build/textkit.o
ar t build/libtextkit.a
nm build/libtextkit.a
```

명령과 심볼 표기는 플랫폼마다 다를 수 있지만 “누가 정의하고 누가 필요로 하는가”라는 질문은 같습니다.

## archive와 링크 순서

`.a`는 일반 압축 파일이 아니라 오브젝트 멤버와 심볼 인덱스를 가진 archive입니다.

```sh
ar rcs libtextkit.a build/textkit.o build/parse.o
```

- `r`: 같은 이름의 멤버를 추가하거나 교체
- `c`: archive가 없으면 생성
- `s`: 심볼 인덱스 생성

소스 목록에서 오브젝트를 제거했는데 기존 archive를 그대로 갱신하면 오래된 멤버가 남을 수 있습니다. 깨끗하게 다시 만들거나 산출물 정리 정책을 둡니다.

많은 Unix linker는 왼쪽에서 오른쪽으로 현재 미해결 심볼을 처리합니다.

```sh
cc build/main.o libtextkit.a -o textstat
```

상호 순환하는 정적 라이브러리는 링크 순서를 복잡하게 만듭니다. 반복 나열이나 linker group보다 먼저 의존 방향을 단순화할 수 있는지 검토합니다.

정적 라이브러리를 쓴다는 말과 시스템 라이브러리까지 모두 정적으로 연결한다는 말은 다릅니다. 동적 라이브러리는 실행 시 loader가 별도 파일을 찾으므로 배포와 ABI라는 추가 계약이 생깁니다.

## target·prerequisite·recipe

```make
build/textkit.o: src/textkit.c include/textkit.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

- target은 만들어야 할 결과입니다.
- prerequisite는 결과가 의존하는 입력입니다.
- recipe는 결과를 만드는 명령입니다.

탭은 recipe의 문법입니다. 문서 들여쓰기와 섞지 않습니다.

## 변수와 기본 옵션

```make
CC ?= cc
CPPFLAGS := -Iinclude
CFLAGS ?= -std=c99 -Wall -Wextra -Wpedantic -Werror -g
```

- `CPPFLAGS`에는 include 경로와 전처리 정의를 둡니다.
- `CFLAGS`에는 C 컴파일 옵션을 둡니다.
- `LDFLAGS`는 링크 단계 옵션입니다.
- `LDLIBS`에는 `-lm`, `-pthread` 같은 라이브러리를 둡니다.

환경에서 `CC`, `CFLAGS`를 바꿀 수 있게 `?=`를 사용할 수 있지만, 프로젝트 필수 경고를 완전히 잃지 않도록 정책을 정해야 합니다.

## 디렉터리와 자동 변수

```make
BUILD := build

$(BUILD):
	mkdir -p $@

$(BUILD)/textkit.o: src/textkit.c include/textkit.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

- `$@`: 현재 target
- `$<`: 첫 prerequisite
- `$^`: 모든 prerequisite
- `| $(BUILD)`는 order-only prerequisite로, 디렉터리 timestamp 때문에 오브젝트를 불필요하게 다시 만들지 않게 합니다.

## 헤더 의존성

소스가 포함하는 헤더가 바뀌면 오브젝트를 다시 만들어야 합니다. 작은 연습에서는 헤더를 prerequisite에 직접 적을 수 있습니다. 큰 프로젝트에서는 컴파일러가 dependency 파일을 생성하게 합니다.

```make
DEPFLAGS := -MMD -MP

$(CC) $(CPPFLAGS) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
-include $(OBJECTS:.o=.d)
```

헤더를 바꾼 뒤 필요한 파일이 다시 컴파일되는지 실제로 확인합니다.

## 정적 라이브러리와 링크 순서

```make
build/libtextkit.a: build/textkit.o
	$(AR) rcs $@ $^

build/textstat: app/main.c build/libtextkit.a
	$(CC) $(CPPFLAGS) $(CFLAGS) app/main.c build/libtextkit.a -o $@
```

정적 라이브러리는 이를 사용하는 오브젝트 뒤에 둡니다. 링크 오류가 나면 라이브러리를 무작정 여러 번 추가하기보다 필요한 심볼을 누가 정의하고 어느 순서로 검색되는지 확인합니다.

## phony target

```make
.PHONY: all check clean sanitize
```

`check`라는 파일이 우연히 있어도 recipe가 실행되도록 실제 파일이 아닌 명령 target을 표시합니다.

## 정확한 증분 빌드

증분 빌드가 정확한지 다음 변화를 직접 실험합니다.

- 소스 하나 변경: 관련 오브젝트와 최종 산출물만 재생성
- 헤더 변경: 그 헤더를 포함한 번역 단위 재생성
- 소스 삭제: 오래된 오브젝트와 archive 멤버가 결과에 남지 않음
- recipe 실패: 부분 산출물을 최신 결과로 오인하지 않음
- 병렬 빌드: 디렉터리 생성과 파일 생성이 경쟁하지 않음

```sh
make -j4 check
```

컴파일 옵션이나 Makefile 자체의 변경을 timestamp만으로 완전히 추적하지 못할 수 있습니다. 작은 프로젝트는 `clean` 재빌드를 정책으로 삼을 수 있고, 큰 프로젝트는 명령 fingerprint나 별도 build directory를 사용할 수 있습니다. 빌드가 보장하는 범위를 과장하지 않습니다.

## 작은 C 테스트 하네스

외부 framework 없이도 공개 API를 검사할 수 있습니다.

```c
#define CHECK(expression) do { \
    if (!(expression)) \
    { \
        fprintf(stderr, "%s:%d: 실패: %s\n", \
                __FILE__, __LINE__, #expression); \
        return 1; \
    } \
} while (0)
```

`do { } while (0)`은 여러 문장 macro를 하나의 문장처럼 사용하게 합니다. macro 인자를 두 번 평가하면 부작용이 중복될 수 있으므로 `expression`은 한 번만 평가합니다.

테스트는 구현 `.c` 파일을 직접 include하지 않고 공개 헤더를 통해 실제 라이브러리와 링크하는 편이 좋습니다. 그래야 선언, 심볼과 사용자의 호출 경계를 함께 검사합니다.

## 출력과 프로세스 결과 검사

CLI는 stdout만 맞으면 완료된 것이 아닙니다.

```text
stdout      정상 결과
stderr      진단
exit status 성공·오류 분류
filesystem  생성·변경된 파일
process     종료와 남은 자식
```

텍스트는 `diff`, 임의 바이트는 길이와 `cmp` 또는 `memcmp`로 검사합니다. FD나 버퍼를 매개변수로 받도록 설계하면 단위 테스트가 쉬워집니다. stdout을 `pipe`와 `dup2`로 캡처할 때는 출력이 pipe 용량을 넘으면 writer와 reader를 동시에 진행시켜야 한다는 점을 고려합니다.

## 테스트 층

```text
unit        작은 순수 함수와 불변식
integration 여러 모듈·파일·프로세스 경계
system      사용자 관점의 CLI 계약
failure     할당·시스템 호출·부분 성공
sanitizer   실행한 경로의 메모리·UB 관찰
```

한 종류의 테스트가 다른 종류를 대체하지 않습니다.

## shell 테스트의 안전한 기본

```sh
#!/bin/sh
set -eu

actual=$(mktemp)
trap 'rm -f "$actual"' EXIT HUP INT TERM

./program input >"$actual"
printf '%s\n' expected | diff -u - "$actual"
```

임시 파일을 정리하고, 변수를 인용하며, stdout·stderr·종료 상태를 별도로 확인합니다. Unix 텍스트 검사 패턴은 [부록](../90-appendix/03-unix-text-testing.md)에 있습니다.

## sanitizer target

```make
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer

sanitize: clean
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) ... -o build/test
	ASAN_OPTIONS=detect_leaks=1 ./build/test
```

sanitizer와 일반 오브젝트를 섞지 않도록 깨끗이 다시 빌드합니다. 지원하지 않는 플랫폼에서는 실패를 성공으로 숨기지 말고 조건을 문서화합니다.

## 재현 가능한 완료 조건

좋은 빌드는 다음 질문에 답합니다.

- 깨끗한 checkout에서 필요한 도구가 무엇입니까?
- 한 명령으로 기준 검사를 실행할 수 있습니까?
- 실패한 명령과 출력이 보입니까?
- `clean` 뒤 생성물이 남지 않습니까?
- 헤더 변경이 올바른 target을 다시 만듭니까?
- Debug와 sanitizer 결과를 구분할 수 있습니까?

## 실습

[textkit](../../exercises/02-c-language/01-textkit/README.md)의 Makefile을 직접 완성하거나 수정해 다음을 확인합니다.

1. 소스 하나를 정적 라이브러리로 만듭니다.
2. CLI와 테스트가 같은 라이브러리를 링크합니다.
3. `make` 두 번째 실행은 불필요하게 컴파일하지 않습니다.
4. 헤더를 수정하면 필요한 오브젝트를 다시 만듭니다.
5. `make clean`, `make reference-test`, `make sanitize`가 독립적으로 동작합니다.
