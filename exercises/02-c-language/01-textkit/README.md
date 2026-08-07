# 연습문제: textkit 정적 라이브러리

## 목표

공개 헤더와 구현 파일을 분리하고, 구현을 정적 라이브러리로 만든 뒤 CLI와 테스트가 같은 라이브러리를 링크하게 합니다.

## 구현 위치

`skeleton/src/textkit.c`의 세 함수를 구현합니다. `include/textkit.h`의 공개 계약은 변경하지 않습니다.

## 계약

- `textkit_length`: NUL 전 문자 수를 반환합니다. `NULL`이면 0입니다.
- `textkit_count_char`: 지정 문자의 개수를 반환합니다. `NULL`이면 0입니다.
- `textkit_word_count`: ASCII 공백(`isspace`)으로 구분한 단어 수를 반환합니다. 연속 공백은 하나의 경계입니다. `NULL`이면 0입니다.
- `ctype.h` 함수에는 `unsigned char`로 변환한 값을 전달합니다.

## 빌드 관찰

```sh
make reference-test
ar t build/reference/libtextkit.a
```

정적 라이브러리를 링크 명령에서 빼고 undefined symbol을 관찰해 봅니다.

## 검증

```sh
make exercise-test
make sanitize
```
