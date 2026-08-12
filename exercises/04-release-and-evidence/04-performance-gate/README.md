# 정확성을 포함한 성능 판정

## 목표

처리 시간이 짧다는 사실만으로 성공을 선언하지 않고, 반복 조건과 업무 결과가 모두 완전한 측정에만 `PASS` 또는 `FAIL`을 부여합니다.

## 문제 계약

`PerformanceGate`는 여러 실행의 다음 근거를 평가합니다.

- 같은 환경 지문
- 요구한 최소 반복 수
- 목표 작업 수와 완료한 업무 효과 수
- 오류, 누락과 중복 효과
- 실행별 지연 시간
- 허용할 최대 지연 시간

판정은 `PASS`, `FAIL`, `UNVERIFIED` 중 하나입니다.

- 근거가 빠졌거나 환경이 섞이면 `UNVERIFIED`
- 근거는 완전하지만 정확성 또는 시간 목표를 어기면 `FAIL`
- 모든 정확성·반복·시간 조건을 만족할 때만 `PASS`

## 실패 조건

skeleton은 가장 빠른 실행 하나만 보고 `PASS`를 반환합니다. 중복 효과나 오류가 있어도 빠르면 성공으로 오판합니다.

## 권장 구현 순서

`reference/` 전체가 하나의 numbering scope입니다. 아래 Implementation 번호는 권장
구현 순서이며 실제 과거 작성 순서를 뜻하지 않습니다.

| 구현 단계 | 파일·경계 | 책임 |
|---:|---|---|
| Implementation 1 | `Decision` | `PASS`, `FAIL`, `UNVERIFIED`의 증거 의미를 구분합니다. |
| Implementation 2 | `Run`, `Goal` | 측정 근거와 판정 정책의 소유자를 분리합니다. |
| Implementation 2-1 | `Goal` constructor | 잘못된 반복 수와 시간 정책을 먼저 거절합니다. |
| Implementation 3 | `evaluate` | 완전성, 환경, 정확성, 시간을 순서대로 gate합니다. |

먼저 `./scripts/new-workspace.sh performance-gate`로 안전한 복사본을 만들고
`.workspace/performance-gate`만 수정합니다. 정본 검사를 통과하고 `FAIL`과
`UNVERIFIED`의 차이를 설명한 뒤에만 `reference/`의 순서와 결과를 비교합니다.

## 완료 기준

- 빠르지만 오류·누락·중복 효과가 있는 결과는 `FAIL`입니다.
- 반복 수나 환경 지문 근거가 부족한 결과는 `UNVERIFIED`입니다.
- 같은 환경의 모든 반복이 정확성과 지연 목표를 만족할 때만 `PASS`입니다.

## 자기 설명

- 가장 빠른 실행 하나가 성능 주장을 뒷받침하지 못하는 이유는 무엇입니까?
- `UNVERIFIED`와 `FAIL`을 구분하면 의사 결정이 어떻게 달라집니까?

## 검증

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/performance-gate
```

workspace 검사가 통과하고 자기 설명을 마친 뒤에만 `reference/`의 판정 결과와
권장 구현 순서를 비교합니다.

- 빠르지만 중복 효과가 있는 결과는 `FAIL`입니다.
- 반복 수가 부족하거나 환경 지문이 섞이면 `UNVERIFIED`입니다.
- 모든 실행이 정확하고 시간 목표 안에 있을 때만 `PASS`입니다.
