# 보안 Finding Template

## 제목

confirmed finding은 `[전제]에서 [근거가 있는 원인]으로 [보안 영향]이 발생함`처럼 조건과 결과를 드러냅니다. false positive는 반증된 candidate 주장과 적용 version을, not-reproducible·unknown은 판정 범위와 미확인 상태를 제목에서도 원인처럼 단정하지 않습니다.

## 검증·처리·수명 주기

- Candidate ID:
- Validation status: `confirmed | false-positive | not-reproducible | unknown`
- Treatment: `remediate | mitigate | accept | defer | not-applicable | null(결정 전)`
- Lifecycle status: `open | assigned | in-progress | ready-for-retest | closed | reopened`
- Duplicate of: canonical finding ID 또는 `없음`
- Confidence:
- Severity와 근거:
- 발견·재검증 시각:

세 축은 서로 다른 질문에 답합니다. validation은 후보가 사실인지, treatment는 무엇을 할지, lifecycle은 업무가 어디까지 진행됐는지 나타냅니다. 중복은 status가 아니라 관계이며 canonical finding의 근거를 가리킵니다.

`unknown`·`not-reproducible`에서 처리 결정을 내릴 근거가 없으면 `treatment: null`을 사용합니다. `defer`는 owner·기한·재검토 trigger가 있는 결정이고, `not-applicable`은 반증된 후보처럼 처리 대상이 아님을 보였을 때만 사용합니다.

### Validation status별 필수 근거

| 상태 | 반드시 기록할 것 | 기록하지 말아야 할 추정 |
|---|---|---|
| `confirmed` | 전제, 재현 또는 독립 관찰, 깨진 불변식, 확인한 영향과 상한 | evidence 없이 확장한 영향·actor 의도 |
| `false-positive` | 평가 version·scope, candidate 전제나 영향에 대한 반증, 한계와 reopen trigger | 근거 없는 root cause·remediation |
| `not-reproducible` | 시도 조건, 실패 oracle, 환경 차이, 다음 안전한 evidence | “수정됨”, “영향 없음”이라는 결론 |
| `unknown` | 결정적 evidence gap, 확인 불가·안전하지 않은 이유, 다음 evidence와 후속 owner | 사실처럼 쓴 root cause·remediation |

`false-positive`와 `unknown`에서는 근거 없는 Root cause와 수정을 억지로 채우지 않고 `해당 없음` 또는 구조화 데이터의 `null`로 둡니다.

## 대상과 범위

- Asset·component:
- Version·build·environment:
- 평가 identity:
- In-scope evidence:
- 확인하지 않은 범위:

## 전제

- 필요한 초기 권한:
- 필요한 구성·데이터 상태:
- 경쟁 조건·시간 조건:
- 제3자 전제:

## 최소 재현

1. 합성 fixture를 준비합니다.
2. 보안 상태의 시작값을 기록합니다.
3. 최소 사건을 수행합니다.
4. 독립 oracle로 상태 변화를 확인합니다.
5. 충분한 증거가 생기면 중단하고 정리합니다.

## Evidence

| ID | Source | Observation | Supports | Limitation |
|---|---|---|---|---|

## 영향

- 확인한 영향:
- 가능한 영향이지만 확인하지 않은 것:
- 사용자·데이터·운영 결과:
- 공격 경로의 다음 capability:

## Root cause

어떤 책임 경계와 불변식이 어디서 강제되지 않았는지 **evidence가 뒷받침하는 범위에서만** 작성합니다. 영향이 확인됐지만 원인이 아직 확인되지 않았다면 그 차이를 명시합니다.

## 처리 결정과 수정

- Treatment 선택과 근거:
- Treatment owner:
- 처리 기한·defer 재검토 시각:

수정·완화가 적용될 때 다음을 작성합니다.

- 즉시 containment:
- root fix:
- similar-path review:
- credential·data·artifact cleanup:
- deployment·rollback:

`remediate`는 정상 기능을 보존하면서 모든 적용 경로의 불변식을 복원하는 최소 change set을 설명합니다. `mitigate`는 남는 원인과 경로를 기록합니다. 적용할 수정이 없는 판정에서는 빈 수정안을 발명하지 않습니다.

### 제한된 위험 수용

`treatment: accept`는 `validation_status: confirmed`에만 사용할 수 있습니다.

- Risk acceptance authority:
- 실행·monitoring owner:
- 근거와 수용 범위:
- Expiry:
- Compensating control:
- Monitoring과 threshold:
- Review trigger:

기술 finding 작성자나 verifier는 조직의 risk acceptance authority를 대신하지 않습니다. 만료나 trigger 발생 시 `reopened` 또는 새 결정을 요구합니다.

## 재검증과 종료

- 원래 재현:
- 정상 기능:
- 경계·실패·known-bad regression:
- runtime evidence:
- close condition:
- re-open trigger:

`closed`는 validation 결과가 아니라 workflow 상태입니다. 수정·완화의 close는 독립 retest와 정상·경계·known-bad 회귀 근거를 요구합니다. `not-reproducible`이나 `unknown`을 단지 시간이 지났다는 이유로 닫지 않습니다.

## 잔여 위험

- 남는 경로:
- compensating control:
- risk owner:
- expiry:
- monitoring:
- review trigger:

## 제출 evidence와 사람 검토

- candidate 원문과 직접 관찰 evidence를 구분한 기록
- 시작 상태, 최소 사건, 성공·실패 oracle과 정리 결과
- 확인한 영향, 미확인 범위, evidence limitation
- treatment와 lifecycle 전이의 owner·시각·근거
- 원래 경로, 정상 기능, 경계·known-bad의 retest 결과

Reviewer는 root cause의 인과 근거, evidence 독립성, severity와 영향 상한, 최소 수정의 우회 경로, acceptance authority를 확인합니다. 자동 검사는 enum·필수 필드·참조와 조건부 필드 존재를 검사할 수 있지만 이 판단들의 타당성을 인증하지 않습니다.
