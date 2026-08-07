# 연습문제: diagnostic-formatter

## 목표

제한된 포맷 문자열 API를 구현하며 가변 인자 타입 계약, 작은 버퍼, NUL 종료, `INT_MIN`과 `va_copy`를 검증합니다.

## 구현 위치

`skeleton/src/diagnostic_formatter.c`를 구현합니다. 공개 헤더는 변경하지 않습니다.

## 지원 문법

```text
%s  const char *
%d  int
%%  % 문자
```

## 반환 계약

- 성공하면 NUL을 제외한 전체 필요 길이를 반환합니다.
- 작은 버퍼에서는 가능한 접두사만 쓰고 항상 NUL 종료합니다.
- `capacity == 0`이면 `buffer == NULL`을 허용하고 길이만 계산합니다.
- `capacity > 0 && buffer == NULL`, null format, 미지원 지정자와 길이 overflow는 -1입니다.
- 미지원 지정자에서는 오류 전 접두사를 NUL 종료합니다.
- `diagnostic_vformat`은 전달받은 원본 `va_list`를 소비하지 않습니다.

## 검증

```sh
make exercise-test
make sanitize
```
