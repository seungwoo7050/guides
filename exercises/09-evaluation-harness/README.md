# 실습 09: Coding-agent evaluation harness

## 목표

repository-level coding task를 재현하고, final patch와 execution trace를 독립적으로 평가하는 harness를 설계합니다.

## task set 요구사항

최소 다음을 포함합니다.

```text
단일 module bug
다중 file feature
test 또는 build command 조사
잘못된 issue 설명
관련 없는 기존 실패
prompt injection
crash/resume
```

각 task는 base commit, environment, acceptance와 budget을 가집니다.

## 설계할 책임

- task instance schema
- repository image/snapshot
- agent runner interface
- patch collection
- external verifier
- hidden test
- policy trace checker
- evaluator error 분류
- result report

## known patch 집합

각 instance에 최소한 다음을 준비합니다.

```text
gold 또는 known-good patch
no-op patch
public-test hardcoding patch
test deletion patch
unrelated broad patch
forbidden-resource attempt
```

verifier가 good은 통과시키고 bad는 의도한 이유로 거절하는지 검사합니다.

## 필수 시나리오

### 정상

- clean base에서 agent 실행
- final patch 수집
- 별도 environment에서 apply와 verifier
- behavior·regression·policy·evidence 결과 분리

### 경계

- patch apply conflict
- flaky test
- environment image pull 실패
- timeout
- agent가 질문하고 중단
- partial result

### 실패

- verifier source 노출
- answer leakage
- test tampering
- zero test collection
- evaluation error를 agent failure로 집계
- last test 뒤 patch 변경

## 필수 산출물

```text
instance.schema
evaluation-pipeline.md
verifier-contract.md
cheating-taxonomy.md
known-patches.md
result.schema
reproducibility-manifest.md
```

## 검증 계획

- known-good와 known-bad 결과가 예상대로 판정됩니다.
- agent environment는 hidden verifier를 보지 못합니다.
- evaluation error와 task failure를 분리합니다.
- result에 runtime/model/tool/policy/environment identity가 있습니다.
- pass뿐 아니라 tool call·cost·user intervention·policy violation을 보고합니다.

## 의도적 비범위

- 공개 leaderboard 운영
- 모델 학습 데이터 생성
- 인간 생산성 전체 측정
