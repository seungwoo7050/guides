# 값·분기·반복: 여러 입력에서 결과 만들기

프로그램은 값을 저장하고, 조건에 따라 경로를 선택하고, 반복해서 상태를 갱신합니다. 문법을 따로 암기하기보다 “어떤 상태를 무엇으로 갱신하는가”를 먼저 적는 편이 안전합니다.

## 기본 값과 타입

```c
int count = 0;
long sum = 0;
double average = 0.0;
char grade = 'A';
```

타입은 값의 가능한 범위와 연산을 정합니다. C의 정수형 크기는 구현에 따라 다를 수 있으므로 범위를 가정하지 않습니다. `<limits.h>`의 `INT_MIN`, `INT_MAX`, `LONG_MIN`, `LONG_MAX`를 사용할 수 있습니다.

자동 저장 기간의 지역 변수는 자동으로 0이 되지 않습니다.

```c
int count;      /* 아직 값이 정해지지 않음 */
count += 1;     /* 잘못된 읽기 */
```

누적 상태는 선언과 함께 초기화합니다.

## 식과 비교

```c
int is_even = value % 2 == 0;
int inside = value >= minimum && value <= maximum;
```

C에서 0은 거짓, 0이 아닌 값은 참으로 해석됩니다. 비교 결과를 다시 `== 1`로 확인할 필요는 없습니다.

```c
if (is_even)
{
    even_count++;
}
```

`=`는 대입이고 `==`는 비교입니다. 경고를 켜 두면 조건식의 실수 일부를 찾을 수 있지만, 경고가 모든 논리 오류를 찾는 것은 아닙니다.

## 분기

```c
if (value < 0)
{
    negative_count++;
}
else if (value == 0)
{
    zero_count++;
}
else
{
    positive_count++;
}
```

분기는 가능한 상태를 나눕니다. 서로 겹치는 조건의 순서가 결과를 바꿀 수 있으므로, 각 입력이 어느 경로에 들어가는지 표로 확인합니다.

`switch`는 하나의 정수·열거 값에 따라 여러 명확한 경우를 나눌 때 유용합니다. `break`를 빠뜨리면 다음 case까지 실행되는 fallthrough가 발생합니다.

## 반복과 불변식

명령행 인자를 순회합니다.

```c
for (int index = 1; index < argc; index++)
{
    printf("%s\n", argv[index]);
}
```

반복을 이해하려면 각 반복 전후에 항상 참이어야 하는 문장을 적습니다.

```text
index는 아직 처리하지 않은 첫 인자를 가리킨다.
count는 지금까지 처리한 유효한 값의 개수다.
sum은 지금까지 처리한 값의 합이다.
minimum과 maximum은 처리한 값이 하나 이상일 때만 유효하다.
```

이 문장이 반복 불변식입니다. 초기 상태에서 참이고, 반복 한 번 뒤에도 유지되며, 반복 종료 때 원하는 결과를 설명해야 합니다.

## 최솟값과 최댓값의 초기화

임의의 큰 상수를 최솟값 초기값으로 두지 않습니다.

```c
long minimum = 999999; /* 입력 범위가 달라지면 깨짐 */
```

첫 유효 입력을 사용합니다.

```c
if (count == 0)
{
    minimum = value;
    maximum = value;
}
else
{
    if (value < minimum)
    {
        minimum = value;
    }
    if (value > maximum)
    {
        maximum = value;
    }
}
count++;
```

“값이 아직 없음”이라는 상태를 별도로 표현하는 것이 핵심입니다.

## 정수 나눗셈과 형 변환

```c
double wrong = sum / count;
double right = (double)sum / (double)count;
```

두 피연산자가 정수이면 나눗셈도 정수로 수행된 뒤 `double`로 바뀝니다. 평균을 구하기 전에 적어도 한쪽을 부동소수점으로 변환합니다. 또한 `count == 0`인지 먼저 확인해야 합니다.

## 오버플로를 계약에 포함하기

입력 값 각각이 `long` 범위에 들어와도 합은 넘칠 수 있습니다. 부호 있는 정수 오버플로는 정의되지 않은 동작입니다.

```c
if ((value > 0 && sum > LONG_MAX - value) ||
    (value < 0 && sum < LONG_MIN - value))
{
    /* 합을 계산하기 전에 실패 처리 */
}
else
{
    sum += value;
}
```

오버플로 검사는 연산 뒤가 아니라 연산 전에 해야 합니다.

## 경계값으로 검사하기

보통 값만 테스트하면 분기 경계가 빠집니다.

- 입력 한 개
- 같은 값 여러 개
- 음수와 0
- `LONG_MIN`, `LONG_MAX`
- 합이 정확히 한계에 도달하는 경우
- 합이 한계를 한 칸 넘는 경우

각 사례의 stdout, stderr와 종료 상태를 정합니다.

## 실습

`number-report`를 다음까지 확장합니다.

- 숫자 인자들을 반복합니다.
- count, min, max와 sum을 갱신합니다.
- 짝수와 홀수 개수를 셉니다.
- 평균을 소수점 두 자리로 출력합니다.
- 합 오버플로 가능성을 연산 전에 거부합니다.

문자열을 숫자로 안전하게 바꾸는 방법은 다음 문서와 [입력 오류 문서](04-input-errors-debugging.md)에서 완성합니다.
