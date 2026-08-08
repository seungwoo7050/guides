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

## 완료 기준

- `make exercise-test`와 `make sanitize`가 통과하며 세 함수가 `NULL`, 빈 문자열, 연속 ASCII 공백을 계약대로 처리합니다.
- 고비트가 설정된 바이트를 포함한 입력에서도 `ctype.h` 호출이 정의된 범위 안에서 이루어지고 sanitizer 오류가 없습니다.
- `ar t build/reference/libtextkit.a`로 구현 object가 archive에 들어 있음을 확인하고, CLI와 테스트가 같은 정적 라이브러리를 링크함을 빌드 명령에서 확인합니다.

## 자기 설명

- plain `char`를 그대로 `isspace`에 전달하면 어떤 입력에서 정의되지 않은 동작이 될 수 있으며 `unsigned char` 변환이 왜 필요한가요?
- 정적 라이브러리를 사용하는 링크 명령에서 archive의 위치가 중요한 이유와 라이브러리를 뺐을 때 undefined symbol이 생기는 과정을 설명할 수 있나요?

## 검증

```sh
make exercise-test
make sanitize
```
