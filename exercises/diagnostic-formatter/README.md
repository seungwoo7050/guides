# diagnostic-formatter

## 개요

`diagnostic-formatter`는 진단 메시지에 필요한 제한된 format 문법을 bounded buffer에 기록하는 C library입니다. `%s`, `%d`, `%%`를 지원하고, buffer가 작아도 전체 필요 길이를 계산하며 가능한 접두사를 NUL 종료합니다.

## 지원 문법

```text
%s  const char *
%d  int
%%  literal percent sign
```

## 반환 계약

- 성공 시 NUL을 제외한 전체 필요 길이를 반환합니다.
- `capacity == 0`이면 `buffer == NULL`을 허용하고 길이만 계산합니다.
- 작은 buffer에서는 `capacity - 1` byte까지만 기록하고 NUL 종료합니다.
- `capacity > 0 && buffer == NULL`, `format == NULL`, 미지원 지정자, 길이 overflow는 `-1`입니다.
- 미지원 지정자 앞에서 이미 기록한 접두사는 NUL 종료됩니다.
- `diagnostic_vformat`은 전달받은 원본 `va_list`를 소비하지 않습니다.

## 빌드와 사용

```sh
make
```

static library는 `build/libdiagnostic_formatter.a`에 생성됩니다.

```c
char message[64];
int required = diagnostic_format(
    message,
    sizeof message,
    "file=%s line=%d",
    "main.c",
    42
);
```

## 검증

```sh
make test
make sanitize
```

테스트는 혼합 지정자, `INT_MIN`·`INT_MAX`, null string, exact fit, truncation, capacity 0·1, 잘못된 format과 동일 `va_list`의 반복 사용을 확인합니다.

## 설계 결정

실제 쓰기 위치와 논리적 출력 길이를 `struct output`에서 분리합니다. 모든 token은 단일 `output_char` 경계를 통과하므로 truncation과 길이 계산 규칙이 일관됩니다. 음수 정수의 magnitude는 unsigned arithmetic으로 계산해 `INT_MIN` negation overflow를 피합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Logical output state | `src/diagnostic_formatter.c` |
| 2 | Unified token emitters | `src/diagnostic_formatter.c` |
| 3 | Truncation and NUL termination | `src/diagnostic_formatter.c` |
| 4 | Format interpretation with copied va_list | `src/diagnostic_formatter.c` |
| 5 | Variadic API wrapper | `src/diagnostic_formatter.c` |

## 범위와 제한

field width, precision, length modifier, floating-point, hexadecimal 등 일반 `printf` 문법은 지원하지 않습니다. 지원하지 않는 지정자는 명시적인 오류입니다.
