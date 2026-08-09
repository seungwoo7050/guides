# Test·build·diagnostic 정규화

## 목표

언어와 도구마다 다른 build·test·lint 출력에서 에이전트가 다음 행동을 결정하는 데 필요한 구조를 추출합니다. 원문 artifact는 보존하되 모델에는 bounded evidence를 제공합니다.

## command 결과와 diagnostic은 다르다

```text
CommandResult
- process가 어떻게 종료됐는가

DiagnosticSet
- 어떤 문제를 어떤 source에서 보고했는가

TestRun
- 어떤 test가 실행·통과·실패·skip됐는가
```

exit code 1이 언제나 test assertion failure는 아닙니다. collection error, compile error, configuration error, timeout과 no-tests-collected가 섞일 수 있습니다.

## 공통 diagnostic model

```text
diagnostic_id
producer
severity
category
message
canonical_path
line·column
symbol
test_id
related_locations[]
causal_parent?
raw_artifact_ref
fingerprint
```

category 예시:

```text
COMPILE_ERROR
TYPE_ERROR
LINT_ERROR
TEST_ASSERTION
TEST_SETUP
IMPORT_OR_DEPENDENCY
RUNTIME_EXCEPTION
TIMEOUT
RESOURCE_EXHAUSTION
ENVIRONMENT
POLICY_BLOCK
UNKNOWN
```

## test result model

```text
suite_id
test_cases[]
passed·failed·skipped·error count
collection_status
duration
seed·shard·retry
coverage?
workspace_revision
command_run_id
```

동일 test 이름이 parameterization이나 shard마다 다를 수 있으므로 stable identity를 설계합니다.

## 원인과 noise

한 compile error가 수백 개 후속 error를 만들 수 있습니다. parser는 다음을 지원할 수 있습니다.

- first causal diagnostic 후보
- duplicate fingerprint 집계
- stack trace frame 제한
- generated/vendor frame 축약
- error summary와 full log reference

하지만 parser가 틀릴 수 있으므로 원문을 폐기하지 않습니다.

## 기존 실패 baseline

수정 전 가능한 범위에서 관련 test를 실행해 baseline을 만듭니다.

```text
before: test A failure, test B pass
change
after:  test A failure, test B failure
```

에이전트는 B를 새 회귀로 분류하고 A는 기존 실패인지 task와 관련된 실패인지 조사합니다.

전체 suite가 너무 비싸면:

- target test baseline
- package/module baseline
- 알려진 CI failure manifest

를 사용하고 한계를 보고합니다.

## flaky test

무조건 재실행해 green을 얻지 않습니다.

- 동일 seed·환경으로 재현
- 실패 fingerprint 비교
- retry 횟수와 결과 기록
- task change 없이도 변하는지 baseline 확인
- flaky로 분류했더라도 final risk에 포함

## 실행 단계

일반적인 순서:

```text
문제 재현
→ 수정에 가까운 단위 test
→ 관련 package test
→ lint·type check
→ 전체 또는 repository-required gate
```

초기부터 전체 suite만 반복하면 비용이 커지고 causal feedback이 느려집니다. 좁은 검사만 통과하고 완료해도 안 됩니다.

## model context용 요약

다음 정보를 우선합니다.

- command와 cwd
- exit kind
- failing test/target
- first causal diagnostic
- 관련 source excerpt
- 새 실패인지 기존 실패인지
- full artifact reference
- truncation 여부

모델이 생성한 요약과 parser가 추출한 사실을 구분합니다.

## 실패 조건

- exit code 0만 보고 실제 실행 test 수를 확인하지 않습니다.
- test가 하나도 수집되지 않았는데 성공으로 처리합니다.
- timeout을 assertion failure로 분류합니다.
- 수정 전 baseline 없이 모든 실패를 agent 탓 또는 기존 실패로 단정합니다.
- flaky test를 무제한 retry해 통과 결과만 남깁니다.
- log truncation이 숨겨집니다.

## 완료 조건

- 최소 두 종류의 test/build tool 출력을 공통 model로 변환하는 설계를 제시합니다.
- command failure, diagnostic parse failure와 task failure를 구분합니다.
- before/after 실패 fingerprint로 회귀를 판정합니다.
- 최종 보고서가 실행 test 수, skip, timeout, truncation과 미실행 gate를 보여 줍니다.
