# 연습문제: number-report

## 목표

명령행 숫자 목록을 검증하고 통계를 출력하는 프로그램을 직접 구현합니다. 값·분기·반복·함수 분해, stdout·stderr와 종료 상태를 하나의 작은 CLI 계약으로 연결합니다.

## 구현 위치

`skeleton/number_report.c`를 수정합니다. 기준 구현은 자신의 구현과 테스트가 통과한 뒤에만 비교합니다.

## 외부 계약

```sh
./number-report 10 -3 8 8 42
```

stdout:

```text
count=5
minimum=-3
maximum=42
sum=65
average=13.00
even=4
odd=1
```

- 인자가 없으면 사용법을 stderr에 출력하고 2로 종료합니다.
- 빈 문자열, 앞뒤 공백, 일부만 숫자인 문자열과 `long` 범위 밖 입력은 stderr 진단과 상태 2로 거부합니다.
- 합이 `long` 범위를 넘으려 하면 상태 3으로 종료합니다.
- 오류 시 stdout은 비어 있어야 합니다.
- 평균은 소수점 둘째 자리까지 출력합니다.

## 내부 완료 조건

- `parse_long`은 성공 뒤에만 출력 매개변수를 변경합니다.
- 합 overflow를 덧셈 전에 검사합니다.
- 첫 입력으로 minimum과 maximum을 초기화합니다.
- 반복 불변식을 설명할 수 있을 정도로 상태를 작게 유지합니다.

## 검증

```sh
make exercise-test
make sanitize
```

초기 skeleton은 의도적으로 테스트에 실패합니다.
