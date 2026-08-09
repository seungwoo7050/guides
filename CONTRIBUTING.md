# 기여 안내

문서, 상태 모델과 검증은 같은 계약을 가리켜야 합니다. 특정 보드에서 한 번 동작했다는 사실을 전체 MCU·RTOS의 보장으로 확대하지 않습니다.

## 문서를 고칠 때

- 자연스러운 한국어 경어체를 사용합니다.
- register, ISR, DMA, deadline 같은 원어가 검색과 명세 확인에 필요하면 첫 등장에 함께 적습니다.
- `c`, `computer-architecture`, `operating-systems`가 이미 소유하는 원리는 짧게 연결하고 반복하지 않습니다.
- hardware 보장, RTOS API 보장, application 정책과 관찰 결과를 구분합니다.
- register bit, interrupt number, flash address와 timing 수치는 사용하는 SoC·board·문서 판본을 함께 적습니다.
- 한 vendor의 구현을 일반 규칙처럼 설명하지 않습니다.
- 측정하지 않은 worst-case latency, power, endurance와 안정성을 단정하지 않습니다.

## 실습을 고칠 때

- 문제의 초기 상태, 입력 사건, 상태 소유자와 완료 조건을 먼저 작성합니다.
- hardware가 없어도 검증 가능한 계약과 실제 board에서만 확인 가능한 계약을 구분합니다.
- timeout, queue overflow, bus error, reset, power loss와 image revert를 정상적인 시험 입력으로 포함합니다.
- reference 구현이 없다면 필요한 artifact와 acceptance criteria를 충분히 구체적으로 적습니다.
- simulator 통과를 실제 timing·electrical·power 보장으로 표현하지 않습니다.

## 코드를 고칠 때

- 작은 결정론적 상태 모델만 `examples/`에 둡니다.
- target-specific code를 추가하면 board, toolchain과 version을 명시합니다.
- build artifact와 generated file은 추적하지 않습니다.
- interrupt context에서 blocking, allocation 또는 긴 formatting을 추가하지 않습니다.
- DMA buffer, persistent record와 update slot의 소유권 전이를 테스트로 드러냅니다.

## 변경 확인

```sh
./prepare.sh
./verify.sh
```

커밋 전에는 다음도 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

문서와 해당 상태 모델·검증 변경은 같은 커밋에 둘 수 있습니다. 서로 독립적인 분야 변경은 나누어 기록합니다.
