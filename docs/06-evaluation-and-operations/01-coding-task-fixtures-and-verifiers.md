# 코딩 과제 fixture와 verifier

## 목표

코딩 에이전트가 실제로 문제를 해결했는지 재현 가능한 저장소 환경과 독립 verifier로 판정합니다. 모델의 설명, diff 크기나 public test 한 번 통과만으로 성공을 정하지 않습니다.

## 평가 instance

하나의 instance는 다음을 포함합니다.

```text
instance_id
repository source와 base commit
task description
initial environment
public evidence
allowed resources
acceptance conditions
hidden verifier
forbidden resources
time·cost·tool budget
expected failure classes
```

base commit과 dependency image를 고정해 동일한 초기 상태를 재현합니다.

## fixture repository

좋은 fixture는 단순한 한 줄 치환보다 실제 개발 행동을 요구합니다.

- 관련 file을 사전에 알려 주지 않습니다.
- production code와 test가 여러 directory에 있습니다.
- build·test 명령을 repository에서 발견해야 합니다.
- issue 설명이 구현 방법을 직접 말하지 않습니다.
- 최소 두 파일 이상의 연관 변경 가능성이 있습니다.
- 관련 없는 기존 실패 또는 noise를 선택적으로 포함합니다.
- 금지 path와 prompt injection fixture를 둘 수 있습니다.

하지만 문제 자체는 사람이 해결 가능하고 acceptance가 명확해야 합니다.

## verifier 분리

```text
Agent environment
- task와 public repository
- public test
- 허용 tool

Evaluation environment
- final patch 또는 workspace snapshot
- hidden test
- policy/audit log
- answer metadata
```

agent가 verifier source와 expected patch를 읽거나 수정할 수 없어야 합니다.

## 결과 verifier

다음 레벨을 조합합니다.

### Patch application

- base commit에 clean apply
- forbidden file 변경 없음
- binary·mode·generated change 정책 준수

### Behavior

- task acceptance test
- 기존 regression test
- error·permission·concurrency invariant

### Build quality

- compile·type·lint·format
- test collection과 실행 수
- dependency·lockfile 정책

### Process and policy

- network·secret·permission 위반 없음
- approval 없는 effect 없음
- budget·timeout 준수
- verifier/answer 접근 없음

### Evidence

- final diff와 test receipt 일치
- 마지막 검사 이후 workspace 변경 없음
- 미실행 gate와 잔여 위험 보고

## oracle의 종류

- deterministic test
- state invariant checker
- output snapshot
- property test
- static analysis
- performance threshold
- policy trace checker
- human review rubric

모델 judge만으로 코드 정답을 판정하지 않습니다. 자연어 품질과 유지보수성의 보조 평가에는 사용할 수 있지만 executable behavior를 대신하지 않습니다.

## instance 난이도 축

```text
저장소 크기
언어·build 복잡도
관련 file 발견 난이도
필요 iteration 수
여러 file 변경
환경·service 요구
모호성·사용자 질문
안전 공격 입력
장기 실행·resume
```

단일 점수만 보지 않고 어떤 능력에서 실패하는지 분해합니다.

## evaluator 오류

verifier도 잘못될 수 있습니다.

- gold patch도 실패
- task description과 hidden test 불일치
- flaky test
- environment image 손상
- architecture/platform 문제
- timeout이 너무 짧음
- hidden dependency unavailable

`AGENT_FAILED`와 `EVALUATION_ERROR`를 분리합니다. 가능하면 known-good patch와 known-bad patch로 harness를 자체 검증합니다.

## 실패 조건

- expected patch text와 정확히 같아야 통과합니다.
- public test만 실행하고 hidden test가 없습니다.
- agent가 verifier와 answer file을 읽을 수 있습니다.
- test가 하나도 실행되지 않았는데 exit code 0만 봅니다.
- gold patch가 현재 image에서 통과하는지 확인하지 않습니다.
- 환경 오류를 agent 품질 저하로 집계합니다.

## 완료 조건

- 한 instance가 base·task·environment·verifier·budget을 고정합니다.
- known-good와 여러 known-bad patch로 verifier를 검사합니다.
- behavior, regression, policy와 evidence를 별도 결과로 냅니다.
- evaluation error가 agent failure와 분리됩니다.
