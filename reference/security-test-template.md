# 보안 테스트 계획 Template

## 1. 검증할 주장

- Requirement ID:
- Threat ID:
- 보안 상태:
- 확인하지 않는 주장:

## 2. 테스트 계층

| 계층 | 확인할 경계 | 장점 | 보장하지 못하는 것 |
|---|---|---|---|
| Unit | | | |
| Integration | | | |
| System | | | |
| Static | | | |
| Dynamic | | | |
| Fuzzing | | | |
| Configuration | | | |
| Manual review | | | |

## 3. Fixture

- 합성 identity:
- 합성 resource:
- 시작 policy·build:
- time·randomness 제어:
- cleanup:

## 4. Oracle

성공·실패 판정에 사용하는 독립 상태를 작성합니다. status code·error text 하나만 사용하지 않습니다.

## 5. Case matrix

| ID | 정상·경계·실패 | Preconditions | Input·event | Expected state | Negative assertion |
|---|---|---|---|---|---|

## 6. Known-bad mutation

검사기가 실제 결함을 거부하는지 확인할 의도적 오답 또는 policy mutation을 작성합니다.

## 7. Evidence

- test result:
- build·policy identity:
- runtime event:
- evidence retention:
- evidence age:

## 8. 한계

- 환경 차이:
- race·load 조건:
- third-party 상태:
- manual follow-up:
