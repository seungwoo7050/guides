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

## 실행 파일과 판정

- 구현 경계: [starter `evaluation.py`](../10-capstone-local-coding-agent/starter/coding_agent/evaluation.py)
- 비교 구현: [reference `evaluation.py`](../10-capstone-local-coding-agent/reference/coding_agent/evaluation.py), [독립 evaluator harness](../10-capstone-local-coding-agent/evaluator/harness.py)
- 공개 판정: [`test_stage_09_evaluation.py`](../10-capstone-local-coding-agent/tests/test_stage_09_evaluation.py)

```sh
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation reference --stage 09
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation starter --stage 09 --expect-incomplete
python3 exercises/10-capstone-local-coding-agent/tests/run.py --implementation .workspace/local-coding-agent --stage 09
```

starter의 `NotImplementedError` 메시지에 있는 `stage-09`는 agent 밖의 materialization·verification과 task/policy/evaluation 오류 분리의 의도한 미완성 표식입니다. 대표 실패는 zero-test, hidden verifier/secret 노출, out-of-scope change 또는 evaluation 환경 오류를 task 성공·실패로 잘못 집계하는 경우입니다. 단계 검사는 01부터 누적됩니다. 위 설계 산출물만으로는 완료가 아니며, 구현·canonical test 결과와 known-good/known-bad별 독립 evaluator report를 함께 제출합니다.

사람 검토 질문:

- agent 완료 선언과 무관한 clean environment가 같은 final revision을 판정합니까?
- behavior·regression·policy·evidence와 evaluator 자체 오류를 분리해 재현할 identity가 report에 충분합니까?

## 의도적 비범위

- 공개 leaderboard 운영
- 모델 학습 데이터 생성
- 인간 생산성 전체 측정
