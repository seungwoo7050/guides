# 빌드·링크·테스트: 반복 가능한 빌드와 검증

빌드 도구를 배우는 목적은 Makefile 문법을 외우는 데 있지 않습니다. 어떤 입력으로 어떤 산출물을 만들며, 입력이 바뀌었을 때 무엇을 다시 만들어야 하는지 명확하게 표현하는 것이 핵심입니다.

테스트 역시 별개의 작업이 아닙니다. 같은 소스와 같은 조건에서 빌드하고, 정해진 검증을 반복해서 실행할 수 있어야 변경으로 인한 문제를 빠르게 확인할 수 있습니다.

## 직접 명령에서 시작하기

자동화하기 전에 실제로 어떤 명령이 필요한지 먼저 이해합니다.

```sh
cc -Iinclude -std=c99 -Wall -Wextra -Wpedantic -c src/textkit.c -o textkit.o
ar rcs libtextkit.a textkit.o
cc -Iinclude app/main.c libtextkit.a -o textstat
cc -Iinclude tests/test_textkit.c libtextkit.a -o test_textkit
./test_textkit
```

이 과정에는 다음 작업이 포함됩니다.

```text
소스 컴파일
→ 오브젝트 파일 생성
→ 정적 라이브러리 생성
→ 프로그램 링크
→ 테스트 프로그램 링크
→ 테스트 실행
```

먼저 각 명령이 어떤 입력을 사용하고 어떤 결과를 만드는지 이해한 뒤, 반복되는 작업을 Makefile로 옮깁니다.

## 빌드는 의존 그래프다

빌드는 단순한 명령 목록이 아니라 입력과 산출물 사이의 의존 관계를 나타내는 그래프입니다.

```text
src/textkit.c + include/textkit.h
    → build/textkit.o

app/main.c + include/textkit.h
    → build/main.o

build/textkit.o
    → build/libtextkit.a

build/main.o + build/libtextkit.a
    → build/textstat

tests/test_textkit.c + build/libtextkit.a
    → build/test_textkit
```

각 화살표는 왼쪽의 입력이 바뀌면 오른쪽의 산출물을 다시 만들어야 한다는 뜻입니다.

이 관계를 정확하게 표현하면 전체 프로젝트를 매번 처음부터 빌드하지 않고 필요한 부분만 다시 만들 수 있습니다.

## 컴파일과 링크 옵션 구분하기

컴파일 옵션과 링크 옵션은 적용되는 단계가 다릅니다.

컴파일 옵션은 각 번역 단위의 전처리, 진단과 코드 생성에 영향을 줍니다.

```sh
cc -Iinclude -std=c99 -Wall -Wextra -Wpedantic -c src/textkit.c -o textkit.o
```

링크 옵션은 최종 실행 파일을 만들 때 라이브러리 검색 경로, 라이브러리 선택과 링커 동작 등에 영향을 줍니다.

```sh
cc main.o -Lbuild -ltextkit -o textstat
```

특별한 이유가 없다면 `ld`를 직접 호출하지 않고 C 컴파일러 드라이버를 통해 링크합니다.

컴파일러 드라이버는 대상 플랫폼에 필요한 시작 코드, 기본 라이브러리와 여러 링크 옵션을 적절하게 구성해 링커를 호출합니다. 이를 직접 재현하려고 하면 플랫폼과 도구체인에 종속된 세부 사항까지 관리해야 합니다.

## 오브젝트 파일과 심볼

오브젝트 파일에는 자신이 정의한 심볼과 다른 오브젝트 파일에서 제공받아야 하는 심볼에 대한 정보가 들어 있습니다.

개념적으로 다음과 같이 볼 수 있습니다.

```text
main.o
  defines: main
  needs:   textkit_length, printf

textkit.o
  defines: textkit_length
```

대표적인 링크 오류는 두 종류입니다.

* **미정의 심볼**: 참조하는 이름의 정의가 최종 링크 입력에 없음
* **중복 정의**: 하나여야 할 외부 정의가 여러 번역 단위에 존재함

헤더에 함수가 선언되어 있다는 사실은 컴파일러가 호출의 타입을 검사할 수 있게 할 뿐, 실제 함수 정의를 만들어 주지는 않습니다.

변경 가능한 전역 객체를 여러 번역 단위에서 공유한다면 헤더에는 선언을 두고 정확히 한 `.c` 파일에 정의를 둡니다.

```c
/* counter.h */
extern unsigned long global_count;
```

```c
/* counter.c */
unsigned long global_count = 0;
```

링크 오류가 발생했을 때는 소스만 읽으며 추측하기보다 실제 산출물을 확인하는 편이 빠릅니다.

```sh
nm build/main.o
nm build/textkit.o
ar t build/libtextkit.a
nm build/libtextkit.a
```

출력 형식과 심볼 표기는 플랫폼마다 다를 수 있지만 확인할 질문은 같습니다.

```text
이 심볼을 누가 정의하는가?
이 심볼을 누가 필요로 하는가?
최종 링크 입력에 그 정의가 실제로 포함되어 있는가?
```

## archive와 링크 순서

`.a` 파일은 일반적인 압축 파일이라기보다 여러 오브젝트 파일을 하나로 묶어 보관하는 archive입니다.

```sh
ar rcs libtextkit.a build/textkit.o build/parse.o
```

일반적인 `ar`에서 각 옵션은 다음 의미를 가집니다.

* `r`: 같은 이름의 멤버를 추가하거나 교체
* `c`: archive가 없으면 생성
* `s`: 심볼 인덱스를 생성하거나 갱신

주의할 점은 기존 archive를 갱신한다고 해서 새 명령에 포함되지 않은 오래된 멤버가 자동으로 삭제되는 것은 아니라는 것입니다.

예를 들어 이전에는 `old.o`가 라이브러리에 포함되어 있었지만 이후 소스 목록에서 제거했다고 가정합니다. 기존 archive에 필요한 멤버만 다시 `ar rcs`한다고 해서 `old.o`가 반드시 사라지는 것은 아닙니다.

따라서 라이브러리를 깨끗하게 다시 만들거나, 제거된 오브젝트가 archive에 남지 않도록 별도의 정리 정책을 둡니다.

많은 Unix 계열 정적 링크 환경에서는 링커가 입력을 대체로 왼쪽에서 오른쪽으로 처리하면서 현재 해결해야 할 심볼을 기준으로 정적 라이브러리의 멤버를 선택합니다.

따라서 일반적으로 다음 순서로 둡니다.

```sh
cc build/main.o build/libtextkit.a -o textstat
```

즉, 라이브러리를 그 라이브러리의 심볼을 사용하는 오브젝트 뒤에 배치합니다.

상호 의존하는 여러 정적 라이브러리 때문에 순환 참조가 생기면 같은 라이브러리를 반복해서 나열하거나 링커의 group 기능을 사용할 수도 있습니다.

하지만 그런 방법을 적용하기 전에 라이브러리 사이의 의존 방향 자체를 단순화할 수 없는지 먼저 확인하는 편이 좋습니다.

또한 **정적 라이브러리를 사용한다는 것**과 **프로그램의 모든 라이브러리를 정적으로 링크한다는 것**은 서로 다른 의미입니다.

동적 라이브러리를 사용하면 실행 시점에 로더가 별도의 라이브러리 파일을 찾아 적재하므로 배포 위치, 버전과 ABI 호환성 같은 추가 계약이 생깁니다.

## target·prerequisite·recipe

Makefile의 기본 규칙은 다음 세 요소로 읽을 수 있습니다.

```make
build/textkit.o: src/textkit.c include/textkit.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

* **target**: 만들어야 할 결과
* **prerequisite**: target이 의존하는 입력
* **recipe**: target을 만드는 명령

여기서 중요한 것은 recipe 자체보다 target과 prerequisite 사이의 관계입니다.

```text
src/textkit.c가 바뀜
        ↓
build/textkit.o를 다시 만들어야 함
```

전통적인 Make 문법에서는 recipe 명령 앞에 탭을 사용합니다. 일반적인 문서 들여쓰기와 혼동하지 않도록 주의합니다.

## 변수와 옵션 분리

대표적인 변수는 다음과 같이 나눌 수 있습니다.

```make
CC ?= cc

CPPFLAGS := -Iinclude
CFLAGS := -std=c99 -Wall -Wextra -Wpedantic -g

LDFLAGS :=
LDLIBS :=
```

일반적인 역할은 다음과 같습니다.

* `CPPFLAGS`: include 경로와 `-D` 같은 전처리 옵션
* `CFLAGS`: C 컴파일 단계에 사용하는 옵션
* `LDFLAGS`: 링커의 동작이나 검색 경로에 영향을 주는 옵션
* `LDLIBS`: 링크할 라이브러리를 지정하는 옵션

예를 들어 다음처럼 사용할 수 있습니다.

```make
LDLIBS += -lm
```

일부 옵션은 한 단계에만 속하지 않습니다. 대표적으로 `-pthread`는 도구체인에 따라 컴파일과 링크 양쪽에 영향을 줄 수 있으므로 단순히 `LDLIBS`에만 넣는다고 가정하지 말고 사용하는 플랫폼의 컴파일러 규칙에 맞춰 적용합니다.

사용자가 다음처럼 옵션을 바꿀 수 있게 만드는 것도 가능합니다.

```sh
make CC=clang CFLAGS="-O2 -Wall -Wextra"
```

다만 외부에서 `CFLAGS`를 완전히 교체할 수 있게 하면 프로젝트에서 반드시 사용하려던 진단 옵션까지 사라질 수 있습니다.

필수 옵션과 사용자가 덧붙일 옵션을 어떻게 구분할지는 프로젝트 정책으로 정합니다.

## 디렉터리와 자동 변수

산출물을 별도 디렉터리에 모을 수 있습니다.

```make
BUILD := build

$(BUILD):
	mkdir -p $@

$(BUILD)/textkit.o: src/textkit.c include/textkit.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
```

자주 사용하는 자동 변수는 다음과 같습니다.

* `$@`: 현재 target
* `$<`: 첫 번째 prerequisite
* `$^`: 중복을 제거한 모든 일반 prerequisite

여기서 다음 부분은 order-only prerequisite입니다.

```make
| $(BUILD)
```

`build/textkit.o`를 만들기 전에 `build` 디렉터리가 존재해야 한다는 의존 관계는 필요합니다.

그러나 디렉터리의 timestamp가 바뀌었다는 이유만으로 오브젝트 파일을 다시 컴파일할 필요는 없습니다.

order-only prerequisite를 사용하면 이 두 의미를 분리할 수 있습니다.

## 헤더 의존성

`.c` 파일이 포함하는 헤더가 바뀌면 해당 번역 단위도 다시 컴파일해야 합니다.

작은 프로젝트에서는 필요한 헤더를 직접 prerequisite에 적을 수 있습니다.

```make
build/textkit.o: src/textkit.c include/textkit.h
```

하지만 include 관계가 많아지면 수동 관리에서 누락이 생기기 쉽습니다.

GCC와 Clang 계열 컴파일러에서는 dependency 파일을 생성하게 할 수 있습니다.

```make
DEPFLAGS := -MMD -MP

$(BUILD)/%.o: src/%.c | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

-include $(OBJECTS:.o=.d)
```

이 방식에서는 실제 `#include` 관계에 따라 `.d` 파일이 생성되고 Make가 이를 다음 빌드에서 읽습니다.

설정을 추가한 것만으로 끝내지 말고 실제로 헤더를 수정한 뒤 그 헤더를 사용하는 번역 단위만 다시 컴파일되는지 확인합니다.

## 정적 라이브러리와 최종 링크

정적 라이브러리도 하나의 target으로 표현할 수 있습니다.

```make
build/libtextkit.a: build/textkit.o
	$(AR) rcs $@ $^
```

실행 파일은 자신의 오브젝트 파일과 라이브러리에 의존합니다.

```make
build/textstat: build/main.o build/libtextkit.a
	$(CC) $(LDFLAGS) build/main.o build/libtextkit.a $(LDLIBS) -o $@
```

정적 라이브러리는 일반적으로 그 라이브러리를 사용하는 오브젝트 뒤에 둡니다.

링크 오류가 발생했다고 같은 라이브러리를 무작정 여러 번 추가하기보다 다음 순서로 확인하는 편이 좋습니다.

```text
어떤 심볼이 해결되지 않았는가
→ 누가 그 심볼을 참조하는가
→ 어느 오브젝트나 라이브러리가 정의하는가
→ 그 입력이 실제 링크 명령에 포함되어 있는가
→ 정적 라이브러리의 검색 순서가 적절한가
```

## phony target

`check`, `clean`처럼 실제 파일을 만드는 것이 목적이 아닌 target은 `.PHONY`로 선언합니다.

```make
.PHONY: all check clean sanitize
```

그렇지 않으면 작업 디렉터리에 우연히 `check`라는 파일이 생겼을 때 Make가 target이 이미 존재한다고 판단해 recipe를 실행하지 않을 수 있습니다.

예를 들어 다음과 같이 사용할 수 있습니다.

```make
check: build/test_textkit
	./build/test_textkit
```

이제 `make check`는 특정 파일을 만드는 요청이 아니라 검증 작업을 실행하는 명령으로 취급됩니다.

## 정확한 증분 빌드

증분 빌드가 올바른지는 실제 변경을 만들어 확인해야 합니다.

다음 상황을 각각 실험해 봅니다.

* 소스 파일 하나 변경 → 관련 오브젝트와 이를 사용하는 최종 산출물만 다시 생성
* 헤더 변경 → 그 헤더에 의존하는 모든 번역 단위 다시 컴파일
* 소스 삭제 → 오래된 오브젝트와 archive 멤버가 최종 결과에 남지 않음
* recipe 실패 → 불완전한 산출물을 정상적인 최신 결과로 취급하지 않음
* 병렬 빌드 → 디렉터리 생성과 파일 생성 사이에 경쟁 조건이 없음

병렬 빌드는 다음처럼 확인할 수 있습니다.

```sh
make -j4 check
```

recipe가 target 파일을 일부 작성한 뒤 실패하면 불완전한 파일이 디스크에 남을 수 있습니다.

GNU Make를 사용하는 프로젝트라면 필요에 따라 다음과 같은 정책을 사용할 수 있습니다.

```make
.DELETE_ON_ERROR:
```

그러면 recipe 실패 시 생성 중이던 target을 제거해 다음 빌드에서 불완전한 파일을 정상 산출물로 오인할 가능성을 줄일 수 있습니다.

다만 이 역시 사용하는 Make 구현에 따른 기능이므로 프로젝트의 도구 요구 사항과 함께 정해야 합니다.

## timestamp 기반 빌드의 한계

전통적인 Make는 주로 파일의 timestamp를 비교해 target을 다시 만들지 결정합니다.

따라서 다음과 같은 변경은 단순한 파일 의존 관계만으로 항상 완벽하게 추적되지 않을 수 있습니다.

* `CFLAGS` 변경
* 컴파일러 자체의 변경
* 환경 변수 변경
* 외부 도구 버전 변경
* 빌드 명령의 일부 변경

Makefile이 바뀌었다고 모든 기존 오브젝트가 자동으로 무효화되는 것도 아닙니다.

작은 프로젝트라면 이런 조건이 바뀌었을 때 다음처럼 깨끗하게 다시 빌드하는 정책으로 충분할 수 있습니다.

```sh
make clean
make check
```

규모가 커지면 빌드 설정별 디렉터리를 분리하거나 실제 컴파일 명령과 설정의 fingerprint를 추적하는 빌드 시스템을 사용할 수 있습니다.

중요한 것은 사용하는 빌드 시스템이 무엇을 자동으로 추적하고 무엇을 추적하지 못하는지 알고 있는 것입니다.

## 작은 C 테스트 하네스

외부 테스트 프레임워크가 없어도 공개 API의 기본 계약을 검사할 수 있습니다.

```c
#define CHECK(expression)                                      \
    do                                                         \
    {                                                          \
        if (!(expression))                                     \
        {                                                      \
            fprintf(stderr, "%s:%d: 실패: %s\n",               \
                    __FILE__, __LINE__, #expression);           \
            return 1;                                          \
        }                                                      \
    } while (0)
```

`do { ... } while (0)` 형태를 사용하면 여러 문장으로 구성된 매크로를 호출부에서 하나의 문장처럼 사용할 수 있습니다.

```c
if (ready)
    CHECK(result == 0);
else
    handle_error();
```

매크로 인자를 여러 번 평가하면 부작용도 여러 번 발생할 수 있습니다.

따라서 위 `CHECK`는 `expression`을 조건식에서 한 번만 평가하도록 작성합니다.

예를 들어 다음과 같은 형태는 피해야 합니다.

```c
#define BAD_CHECK(x) ((x) ? 0 : report_failure(x))
```

`x`에 `i++`나 함수 호출처럼 부작용이 있다면 예상하지 못한 결과가 생길 수 있습니다.

## 테스트는 공개 경계를 사용한다

일반적인 API 테스트에서는 구현 `.c` 파일을 테스트 코드에 직접 포함하지 않는 편이 좋습니다.

```c
#include "textkit.c" /* 일반적인 공개 API 테스트에서는 피함 */
```

대신 실제 사용자와 같은 방식으로 공개 헤더를 포함하고 빌드된 라이브러리에 링크합니다.

```c
#include "textkit.h"
```

```sh
cc tests/test_textkit.c build/libtextkit.a -o build/test_textkit
```

이 방식은 함수의 내부 동작뿐 아니라 다음 경계도 함께 검사합니다.

* 공개 헤더에 필요한 선언이 존재하는가
* 선언과 실제 정의가 일치하는가
* 필요한 심볼이 라이브러리에 포함되어 있는가
* 호출자가 실제로 사용할 수 있는 인터페이스인가

내부 함수를 따로 검사해야 한다면 공개 API 테스트와 구분된 별도의 테스트 전략을 사용합니다.

## 출력과 프로세스 결과 검사

CLI 프로그램의 결과는 stdout만으로 정의되지 않습니다.

외부에서 관찰할 수 있는 결과에는 다음과 같은 항목이 있습니다.

```text
stdout
    정상적인 출력

stderr
    오류와 진단 출력

exit status
    성공과 실패 상태

filesystem
    생성·삭제·수정된 파일

process
    프로세스 종료 여부와 남아 있는 자식 프로세스
```

CLI 계약에 어떤 항목이 포함되는지에 따라 테스트 범위를 정합니다.

텍스트 출력은 `diff`로 비교할 수 있습니다.

임의의 바이트 데이터는 문자열 함수로 검사하지 않고 길이와 `cmp`, `memcmp` 같은 바이트 단위 도구를 사용합니다.

테스트하기 어려운 코드는 경계를 조금 바꾸는 것만으로도 검증하기 쉬워질 수 있습니다.

예를 들어 항상 stdout에 직접 출력하는 함수보다 파일 디스크립터나 출력 버퍼를 인자로 받는 내부 함수를 두면 단위 테스트가 쉬워질 수 있습니다.

stdout을 `pipe`와 `dup2`로 캡처하는 방식도 가능하지만 주의가 필요합니다.

프로그램이 pipe의 버퍼 용량보다 많은 데이터를 쓰는데 테스트 코드가 프로그램 종료 후에야 읽으려고 하면 writer가 가득 찬 pipe에서 대기하면서 교착될 수 있습니다.

출력량이 커질 수 있다면 읽기와 쓰기가 동시에 진행되도록 설계해야 합니다.

## 테스트의 층

테스트는 서로 다른 범위와 실패를 관찰합니다.

```text
unit
    작은 함수와 자료구조의 불변식

integration
    여러 모듈·파일·라이브러리 사이의 경계

system
    실제 사용자 관점의 실행 파일과 CLI 계약

failure
    할당 실패·시스템 호출 실패·부분 초기화 경로

sanitizer
    실제 실행된 경로의 메모리 오류와 일부 UB 탐지
```

한 종류의 테스트가 다른 종류를 대신하지는 않습니다.

단위 테스트가 모두 통과해도 최종 링크 구성이 잘못될 수 있고, 시스템 테스트가 성공해도 특정 할당 실패 경로는 한 번도 실행되지 않았을 수 있습니다.

어떤 테스트가 어떤 종류의 문제를 발견하도록 설계되었는지 구분합니다.

## shell 테스트의 기본 패턴

간단한 CLI 테스트는 POSIX shell만으로도 작성할 수 있습니다.

```sh
#!/bin/sh
set -eu

actual=$(mktemp)

trap 'rm -f "$actual"' EXIT HUP INT TERM

./program input >"$actual"

printf '%s\n' 'expected' | diff -u - "$actual"
```

기본적으로 다음을 지킵니다.

* 임시 파일을 사용했다면 종료 경로에서 정리
* 변수 확장은 특별한 이유가 없으면 인용
* stdout과 stderr를 필요에 따라 별도로 검사
* 프로그램의 종료 상태도 계약에 포함해 검사
* 테스트 명령 자체의 실패를 숨기지 않음

복잡한 임시 디렉터리나 여러 자원을 다룬다면 정리 함수와 `trap`을 더 명시적으로 구성합니다.

Unix 환경의 텍스트 검사 패턴은 [부록](../90-appendix/03-unix-text-testing.md)에서 별도로 다룹니다.

## sanitizer 빌드

AddressSanitizer와 UndefinedBehaviorSanitizer를 사용하는 별도 검증 target을 둘 수 있습니다.

```make
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer

sanitize: clean
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANFLAGS) \
	    tests/test_textkit.c src/textkit.c \
	    $(LDFLAGS) $(SANFLAGS) $(LDLIBS) \
	    -o build/test_textkit_sanitize
	./build/test_textkit_sanitize
```

sanitizer 옵션은 코드 생성과 최종 링크 양쪽에 영향을 줄 수 있으므로 sanitizer로 컴파일한 코드와 일반 빌드 산출물을 무분별하게 섞지 않는 편이 안전합니다.

작은 프로젝트에서는 `clean` 뒤 sanitizer 전용 빌드를 만드는 것으로 충분할 수 있습니다.

더 큰 프로젝트에서는 다음처럼 빌드 디렉터리를 분리할 수도 있습니다.

```text
build/debug/
build/release/
build/sanitize/
```

LeakSanitizer 지원 여부와 사용 방법은 플랫폼과 컴파일러에 따라 달라질 수 있습니다. 특정 환경에서 지원되지 않는 검사를 억지로 성공으로 처리하기보다 지원 조건을 명시합니다.

sanitizer가 테스트를 통과했다는 사실 역시 실행하지 않은 경로의 안전성을 증명하지는 않습니다.

## 반복 가능한 완료 조건

프로젝트의 빌드와 검증 절차는 최소한 다음 질문에 답할 수 있어야 합니다.

* 깨끗한 checkout에서 어떤 도구가 필요한가?
* 처음부터 빌드하는 명령은 무엇인가?
* 한 명령으로 기준 테스트를 실행할 수 있는가?
* 실패한 단계와 진단 출력을 확인할 수 있는가?
* 소스 하나를 바꾸면 필요한 대상만 다시 만들어지는가?
* 헤더 변경이 실제 의존 번역 단위를 다시 컴파일하는가?
* 제거된 소스의 오래된 산출물이 결과에 남지 않는가?
* 실패한 recipe의 불완전한 결과를 다음 빌드가 정상 결과로 오인하지 않는가?
* 병렬 빌드에서도 동일한 의존 관계가 성립하는가?
* `clean` 뒤 프로젝트가 관리하는 생성물이 남지 않는가?
* 일반 빌드와 sanitizer 빌드의 산출물을 구분할 수 있는가?
* 사용한 빌드 시스템이 추적하지 못하는 변경 조건은 무엇인가?

완료 조건의 핵심은 특정 Makefile 형태를 만드는 것이 아닙니다.

```text
입력과 의존 관계를 설명할 수 있고
→ 필요한 산출물을 반복해서 만들 수 있으며
→ 변경 뒤 필요한 범위만 다시 만들고
→ 같은 검증 절차를 다시 실행해
→ 실패 지점을 확인할 수 있는 상태
```

이 상태를 만드는 것이 빌드 자동화와 테스트 환경을 갖추는 목적입니다.

## 실습

[textkit](../../exercises/02-c-language/01-textkit/README.md)의 제공된 Makefile과 학습자 workspace 산출물을 관찰해 다음을 확인합니다. 이 단계에서 직접 구현하는 파일은 여전히 `workspace/src/textkit.c`이며, build graph 자체를 수정하는 별도 실습은 아닙니다.

1. 소스 하나를 정적 라이브러리로 만듭니다.
2. CLI와 테스트가 같은 라이브러리를 링크합니다.
3. `make` 두 번째 실행은 불필요하게 컴파일하지 않습니다.
4. 헤더를 수정하면 필요한 오브젝트를 다시 만듭니다.
5. `make clean`, `make exercise-test`, `make sanitize`가 독립적으로 동작합니다.

저장소 루트에서 아직 workspace를 만들지 않았다면 먼저 생성합니다.

```sh
scripts/new-workspace.sh exercises/02-c-language/01-textkit
make -C exercises/02-c-language/01-textkit exercise-build
make -C exercises/02-c-language/01-textkit -n exercise-build
ar t exercises/02-c-language/01-textkit/build/exercise/libtextkit.a
```

`make -n` 출력에서 compile, archive, link의 입력 관계를 읽고, `ar t`에서는 자신이 구현한 workspace로 만든 archive member를 확인합니다. 기준 구현은 학습자 구현과 검증을 마친 뒤에만 비교합니다.
