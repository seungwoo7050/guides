# textkit

## 개요

`textkit`은 NUL 종료 byte string을 대상으로 길이, 특정 byte의 출현 횟수, 공백 기준 단어 수를 계산하는 소형 C library입니다. 함께 제공되는 `textstat` CLI는 library의 길이와 단어 수 기능을 명령행에서 사용할 수 있게 합니다.

## 주요 기능

- `NULL` 입력을 빈 입력으로 취급하는 일관된 API
- locale의 `isspace` 규칙을 사용하는 단어 경계 계산
- `char`를 `unsigned char`로 변환한 뒤 ctype API에 전달
- static library와 독립 실행 CLI 동시 제공

## 빌드

```sh
make
```

생성물:

```text
build/libtextkit.a
build/textstat
```

## 사용법

```sh
./build/textstat 'one two'
```

```text
length=7
words=2
```

Library API는 `include/textkit.h`에 선언되어 있습니다.

```c
size_t textkit_length(const char *text);
size_t textkit_count_char(const char *text, char needle);
size_t textkit_word_count(const char *text);
```

## 검증

```sh
make test
make sanitize
```

Library 테스트는 `NULL`, 빈 문자열, 모든 공백 문자, high-bit byte와 일반 단어 경계를 검사합니다. CLI 테스트는 정상 출력, 빈 문자열과 usage 오류 계약을 확인합니다.

## 설계 결정

이 project는 Unicode grapheme이나 locale-aware text segmentation이 아니라 byte string 분석을 제공합니다. 단어는 `isspace`가 참인 byte 사이의 연속 구간으로 정의합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Public text-analysis contract | `include/textkit.h` |
| 2 | Byte-length traversal | `src/textkit.c` |
| 3 | Byte-frequency traversal | `src/textkit.c` |
| 4 | Whitespace-delimited word state | `src/textkit.c` |
| 5 | CLI composition | `app/main.c` |

## 범위와 제한

API는 NUL 종료 문자열만 처리합니다. 포함된 NUL 뒤의 byte는 분석하지 않으며, multi-byte encoding의 문자 수를 계산하지 않습니다.
