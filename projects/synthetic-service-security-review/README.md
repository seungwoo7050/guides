# LedgerLab 합성 서비스 보안 검토

이 프로젝트는 문서·설정 snapshot·합성 검증 결과·audit event와 작은 격리 구현을 이용해 하나의 서비스에 대한 **공격 경로, 수정, 탐지, 사고 대응과 release 결정**을 완성하는 Capstone입니다.

완성 exploit과 정답 보고서는 제공하지 않습니다. 후보 finding에는 참·거짓·미확인이 섞여 있을 수 있습니다. 제공 자료가 부족하면 범위를 넘겨 확인하지 말고 `unknown`과 필요한 최소 evidence를 기록합니다.

## 1. 사용자 기능

LedgerLab 사용자는 자신의 account transaction을 바탕으로 report를 생성하고 내려받습니다.

```text
browser
  → public gateway
  → account API
       ├→ account database
       ├→ report queue
       └→ signed download response

report queue
  → report worker
       ├→ account API
       └→ object storage

source repository
  → CI
  → internal package proxy
  → artifact registry
  → runtime

모든 component
  → audit sink
```

## 2. 제공 자료

[`scenario/README.md`](scenario/README.md)의 순서대로 읽습니다.

- 시스템 context와 현재 보안 주장
- asset register
- workload·user identity policy snapshot
- route와 authorization query 설명
- package proxy policy
- release manifest와 artifact evidence
- 후보 finding
- 합성 verification observation
- audit event와 operator notes
- incident runbook excerpt

자료의 갱신 시각과 source가 다릅니다. 오래된 설계 문서와 runtime evidence를 같은 무게로 사용하지 않습니다.

## 3. 안전 범위

### In scope

- 저장소에 제공된 합성 자료
- `LedgerLab staging-synthetic` environment에 대한 문서 분석
- `ledgerlab-lab-*` identity와 `synthetic/*` resource를 가정한 테스트 설계
- Python 표준 라이브러리만 쓰는 필수 isolated behavior profile
- 로컬 service·container로 넓히는 선택 full implementation profile

### Out of scope

- 실제 cloud·registry·package provider
- 실제 사용자·계정·transaction·object
- production과 shared organization resource
- 외부 network scan, 계정 추측과 credential 획득
- service degradation·persistence·evasion

자세한 정책은 [`../../reference/safe-lab-policy.md`](../../reference/safe-lab-policy.md)를 따릅니다.

## 4. 시작

작업 directory를 비파괴적으로 만듭니다.

```sh
python3 scripts/new_workspace.py capstone
```

기존 `work/` 또는 symlink 경로는 덮어쓰지 않습니다. 모든 `TODO`를 실제 판단과 근거로 바꿉니다. templates와 의도적으로 취약한 `work/behavior-lab/ledgerlab_policy.py`는 시작 상태이며 그대로는 완료 검사에 통과하지 않습니다.

## 5. 단계

### Stage 1 — 평가 계약

`scope.md`

- 평가 목적과 authorization
- in·out of scope
- 허용·금지 행동
- request·resource·time budget
- stop condition
- evidence handling
- cleanup

### Stage 2 — 위협 모델

`threat-model.md`

- 시스템 보안 목표
- 자산·정본·owner
- actor·initial capability
- trust boundary·data flow
- threat statement
- attack path의 precondition·postcondition
- choke point·우회 경로
- assumption·unknown

### Stage 3 — Finding 검증

`findings.json`

각 candidate에 서로 독립인 세 상태 축과 duplicate 관계를 기록합니다.

```text
validation_status: confirmed | false-positive | not-reproducible | unknown
treatment: remediate | mitigate | accept | defer | not-applicable | null
lifecycle_status: open | assigned | in-progress | ready-for-retest | closed | reopened
duplicate_of: FND-* | null
```

`confirmed`에만 causal mechanism·proof oracle과 root fix를 요구합니다. `false-positive`는 반증한 가정과 counterevidence를 기록하고 보통 `not-applicable`로 처리합니다. evidence가 부족한 `not-reproducible`·`unknown`은 treatment를 `null`로 두며 미확인 범위·다음 안전한 evidence·reopen trigger를 기록합니다. 명시적으로 `defer`한다면 owner, ISO review date와 trigger가 필요합니다. `not-applicable`은 unknown을 닫는 수단이 아닙니다. `treatment: accept`는 confirmed finding에만 허용되며 별도 risk acceptance object에 authority, owner, ISO expiry, compensating controls, monitoring과 review trigger가 필요합니다.

non-confirmed finding은 존재하지 않는 downstream 산출물 ID를 만들지 않습니다. `trace`의 배열은 실제 근거가 연결된 범위까지만 채우고 아직 없는 `REQ`·`TEST`·`PATCH`·`DET`는 빈 배열로 둡니다.

### Stage 4 — 보안 요구사항과 검사

`security-requirements.md`, `test-plan.md`

- threat → requirement → enforcement owner
- 허용·거부 상태와 control failure behavior
- 정상·경계·실패·known-bad matrix
- 독립 test oracle
- runtime evidence와 evidence age

이 단계에서 최소 하나의 `FND-* → THR-* → REQ-* → TEST-*` 경로를 고정합니다.

### Stage 5 — 수정과 Hardening

`remediation-plan.md`

- 즉시 containment
- root cause 수정
- similar-path review
- credential·artifact·data cleanup
- regression
- deployment·rollback
- retest·close condition

`PATCH-*`는 위 경로의 `FND-*`를 참조하고 정상 기능을 보존하면서 해당 불변식을 모든 적용 경로에서 복원하는 최소 change set을 설명합니다.

### Stage 6 — Telemetry와 탐지

`detection-plan.md`

- canonical event schema
- actor·effective actor·delegated identity
- detection hypothesis
- analytic과 correlation
- known-positive·negative
- triage·containment
- pipeline health

`DET-*`는 isolated behavior profile의 corrected deny event를 positive로, 정상·중복·순서가 바뀐 event를 negative로 사용합니다.

### Stage 7 — 사고 대응과 복구

`incident-timeline.md`

- `FACT`, `HYPOTHESIS`, `DECISION`, `ACTION`, `RESULT`, `UNKNOWN`
- event·ingest·discovery·decision time
- evidence preservation
- scope와 containment trade-off
- eradication과 trusted recovery
- communication

### Stage 8 — 보안 검토 결정

`final-report.md`

- 검증된 상태와 evidence limitation
- attack path와 차단 지점
- open finding과 residual risk
- `go`, `conditional-go`, `no-go`
- risk owner·expiry
- production validation·rollback trigger
- 다음 프로젝트 단계

같은 `FND`, `THR`, `REQ`, `TEST`, `PATCH`, `DET` ID가 incident/recovery와 최종 결정까지 이어져야 합니다. 합성 post-release 결과와 승인권자가 있는 별도의 production validation 계획을 구분합니다.

## 6. 필수 격리 행동 Profile

문서 분석과 함께 [`../../exercises/07-isolated-attack-path`](../../exercises/07-isolated-attack-path/README.md)의 공개 행동 계약을 구현합니다. 이 profile은 합성 in-memory 상태에서 cross-owner report access와 cross-job credential access만 모델링하며 OS root exploit이나 실제 내부 이동은 다루지 않습니다.

작업 순서는 다음과 같습니다.

1. 생성된 취약 구현을 바꾸기 전에 canonical skeleton의 cross-owner·cross-job 허용을 재현합니다.
2. owner/job scope의 causal root cause와 최소 change set을 기록하고 `work/behavior-lab/ledgerlab_policy.py`를 수정합니다.
3. 정상 owner/job 기능, prefix·expiry·revocation·누락 context 경계, 같은 공격 deny와 detector positive·negative를 실행합니다.
4. 실행 근거와 exact patch를 생성합니다.

```sh
python3 scripts/capture_capstone_behavior.py \
  projects/synthetic-service-security-review/work
```

capture와 verifier는 learner Python을 현재 사용자 권한으로 불러와 실행하며 OS sandbox가 아닙니다. 자신이 검토한 구현만 실행하고 network·subprocess·저장소 밖 파일 접근을 넣지 않습니다.

생성되는 필수 근거는 다음과 같습니다.

- `vulnerable-evidence.json`: canonical 취약 상태와 pre/post state hash
- `behavior-evidence.json`: 수정 구현 fingerprint, 정상·경계·known-bad 결과, deny event와 detector 결과
- `known-bad-evidence.json`: deny-all, cross-owner, prefix bypass와 detection 누락 mutant 거부 결과
- `behavior-patch.diff`: canonical skeleton 대비 exact diff
- `behavior-review.md`: root cause, patch 최소성, trace ID, cleanup과 검증 한계에 대한 사람 판단

## 7. 구조·행동 검사

```sh
python3 scripts/verify_capstone.py \
  projects/synthetic-service-security-review/work
```

검사기는 다음을 확인합니다.

- 필수 파일과 section
- 남아 있는 `TODO`
- `findings.json`의 validation·treatment·lifecycle 상태와 상태별 evidence
- 대소문자를 정규화한 ID 중복·참조·candidate completeness
- confirmed finding의 causal mechanism·proof oracle
- accepted treatment의 authority·owner·expiry·control·monitoring·review trigger
- scenario에 없는 candidate 참조
- 하나의 coherent `FND → THR → REQ → TEST → PATCH → DET → incident/recovery → release` trace
- learner implementation 재실행과 제출 behavior evidence·fingerprint·patch의 일치

검사기가 통과해도 기술적 판단이 옳다는 뜻은 아닙니다. evidence source의 실질적 독립성, causal root cause, patch 최소성·우회 경로, detector 오탐·미탐, recovery trust anchor, risk acceptance와 release decision은 사람이 검토합니다.

### 검사기가 요구하는 최소 추적 구조

| 산출물 | 최소 구조 |
|---|---|
| `threat-model.md` | 서로 다른 `THR-*` 세 개 이상과 하나 이상의 다단계 공격 경로 |
| `findings.json` | 일곱 candidate를 각각 한 번 판정 |
| `security-requirements.md` | threat model에 존재하는 `THR-*`를 연결한 `REQ-*` 세 개 이상 |
| `test-plan.md` | 위 requirement 중 `REQ-*` 세 개 이상과 서로 다른 `TEST-*`를 정상·경계·실패·known-bad로 검사 |
| `remediation-plan.md` | `findings.json`의 `FND-*`와 서로 다른 `PATCH-*` 참조 |
| `detection-plan.md` | 서로 다른 `DET-*` 두 개 이상, positive·negative fixture |
| `incident-timeline.md` | 같은 `FND-*`, `PATCH-*`, `DET-*`와 `FACT`, `HYPOTHESIS`, `DECISION`, `ACTION`, `RESULT`, `UNKNOWN` 중 네 종류 이상 |
| `final-report.md` | end-to-end trace ID, `Release 결정: go|conditional-go|no-go`, 유효한 ISO 재검토 날짜 |
| 행동 근거 | 취약 proof, 수정 구현·diff, 정상·경계·failure·known-bad, corrected deny, detection positive·negative |

이는 문서 분량을 늘리기 위한 조건이 아닙니다. 위협, finding, control, 검사와 운영 결정을 서로 추적할 최소 구조입니다.

## 8. 제출 전 자기 검토

- [ ] 모든 중요한 주장에 evidence ID 또는 `unknown`이 있습니다.
- [ ] attack path 단계가 capability 변화로 연결됩니다.
- [ ] 실제 데이터·제3자 평가가 필요하다는 계획이 없습니다.
- [ ] root cause·similar path·cleanup·regression이 연결됩니다.
- [ ] prevention·detection·recovery를 모두 다룹니다.
- [ ] evidence source와 age를 기록했습니다.
- [ ] isolated behavior 실행의 state hash, implementation hash와 exact patch를 제출했습니다.
- [ ] 같은 공격의 deny event와 detector positive·benign negative를 `DET-*`에 연결했습니다.
- [ ] patch가 정상 owner/job 기능을 보존하며 prefix·expiry·revocation 우회를 막는지 사람이 검토했습니다.
- [ ] open risk에 owner·expiry·re-review trigger가 있습니다.
- [ ] release 결정이 severity 숫자 하나에 의존하지 않습니다.

## 9. 선택 Full Service 구현 Profile

문서 profile을 완료한 뒤 같은 상태를 로컬 process 또는 container로 구현할 수 있습니다.

권장 구성:

```text
local gateway
+ account API
+ report worker
+ package proxy stub
+ object store stub
+ audit sink
+ external verifier
```

구현은 다음 계약을 만족해야 합니다.

- 외부 egress 기본 거부
- 합성 identity·object만 사용
- privileged container·host mount 금지
- intentional weakness 목록과 owner 명시
- synthetic flag 또는 state oracle로만 성공 판정
- corrected profile에서 같은 regression 차단
- event fixture와 timeline을 실제 실행 결과에서 생성
- 실행 뒤 process·network·credential·workspace 정리

full service profile은 필수 완료 조건이 아닙니다. 다만 작은 isolated behavior profile과 그 실행 근거는 필수입니다. 문서로 상태·실패·검증을 먼저 고정하지 않았다면 확장을 시작하지 않습니다.
