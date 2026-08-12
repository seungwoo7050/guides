# 첫 명령행 프로그램 실습

문자열 인자를 정수로 변환하고, 계산 결과와 오류 진단을 서로 다른 출력 경계에 두는 작은 Java 프로그램을 완성합니다. 이 실습은 Java 문법 전체보다 다음 개발 루프를 직접 돌리는 데 목적이 있습니다.

```text
소스 작성 → 컴파일 → 실행 → 실패 관찰 → 수정 → 자동 검증
```

## 목표

명령행 문자열을 안전하게 `long`으로 변환하고, 계산 성공과 입력 실패의 출력·종료 상태 경계를 하나의 실행 가능한 계약으로 만듭니다.

## 권장 구현 순서

`reference/` 전체가 하나의 numbering scope입니다. 번호는 실제 과거 작성 순서가 아니라 같은 프로그램을 다시 만들 때의 학습용 권장 구현 순서입니다. Maven project와 POM은 제공된 scaffold이므로 Implementation 0은 없습니다.

| 순서 | 구현 위치 | 책임 |
|---:|---|---|
| 1 | `NumberReportApplication.run` | 인자와 두 출력 stream을 받는 부작용 경계를 먼저 고정합니다. |
| 1-1 | `run`의 인자 순회 | 모든 입력을 변환하고 합계·최솟값·최댓값을 성공 출력 전에 계산합니다. |
| 1-2 | `run`의 평균·출력 블록 | 반올림과 locale을 고정하고 완성된 결과만 stdout에 commit합니다. |
| 2 | `NumberReportApplication.main` | 반환 상태를 실제 process exit로 번역합니다. |

## 프로그램 계약

다음처럼 하나 이상의 정수를 전달합니다.

```sh
java ... NumberReportApplication 10 -3 8 8 42
```

정상 입력은 표준 출력에 다음 값을 기록하고 종료 상태 `0`을 반환합니다.

```text
count=5
min=-3
max=42
sum=65
average=13.00
```

다음 경우에는 표준 출력에 아무것도 쓰지 않고, 표준 오류에 원인을 기록한 뒤 종료 상태 `2`를 반환합니다.

- 인자가 없습니다.
- 정수로 완전히 변환할 수 없는 값이 있습니다.
- 합계가 `long` 범위를 벗어납니다.

평균은 소수 둘째 자리까지 `HALF_UP`으로 반올림합니다.

## 구현 순서

1. 정본 생성 명령으로 `.workspace/first-program`을 만들고 검사해 지정 실패를 확인합니다.
2. 학습자 workspace의 `NumberReportApplication.run`을 구현합니다.
3. 입력 검증과 계산을 작은 메서드로 나눕니다.
4. 정상 결과는 `stdout`, 진단은 `stderr`에만 기록합니다.
5. 같은 입력으로 직접 실행한 결과와 자동 검사 결과를 비교합니다.

```sh
./scripts/new-workspace.sh exercises/01-language-and-domain/01-first-program
./scripts/check-workspace.sh exercises/01-language-and-domain/01-first-program
```

테스트를 약하게 바꾸어 skeleton을 통과시키지 않습니다. 구현을 마친 뒤에만 `reference`와 비교합니다.

## 완료 기준

- [ ] 공개 테스트를 바꾸지 않고 정상 입력의 count·min·max·sum·average를 모두 맞춥니다.
- [ ] 빈 입력, 잘못된 정수와 합계 오버플로가 stdout을 비우고 종료 상태 `2`를 반환합니다.
- [ ] 별도 JVM 프로세스 실행에서도 표준 출력·표준 오류·종료 상태가 같은 계약을 보입니다.

## 자기 설명

- 합계를 모두 계산하기 전에는 정상 출력의 일부도 기록하지 않아야 하는 이유는 무엇인가요?
- `double` 대신 `BigDecimal`과 `HALF_UP`을 명시하면 어떤 모호함이 사라지나요?

## 검증

```sh
./scripts/check-workspace.sh exercises/01-language-and-domain/01-first-program
```

workspace가 통과하고 자기 설명을 마친 뒤에만 비교용 구현을 검증하고 `reference/` 소스를 읽습니다.

```sh
./scripts/mvn-guide.sh -pl :first-program-reference -am test
```
