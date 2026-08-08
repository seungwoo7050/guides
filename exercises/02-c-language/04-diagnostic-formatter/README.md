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

## 완료 기준

- `make exercise-test`와 `make sanitize`가 통과하며 `%s`, `%d`, `%%`의 혼합 결과와 NUL을 제외한 전체 필요 길이가 정확합니다.
- capacity 0, 1과 필요한 길이보다 작은 버퍼를 시험해 가능한 접두사와 NUL 종료가 지켜지고 `INT_MIN`도 overflow 없이 출력됩니다.
- null 인자·미지원 지정자·길이 overflow가 -1을 반환하며, 원본 `va_list`를 복사해 두 번 사용해도 같은 인자를 읽을 수 있음을 확인합니다.

## 자기 설명

- 잘린 출력에서도 전체 필요 길이를 계산하려면 쓰기 위치와 논리적 출력 길이를 어떻게 분리해야 하나요?
- `INT_MIN`의 절댓값을 같은 signed 타입에서 바로 계산하면 왜 위험하며 `va_copy` 없이 원본 `va_list`를 순회하면 어떤 계약을 깨나요?

## 검증

```sh
make exercise-test
make sanitize
```
