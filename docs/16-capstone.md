# 공격·수정·탐지 Capstone

Capstone은 개별 장의 산출물을 하나의 가상 시스템에 연결합니다. 완성 exploit이나 security appliance를 만드는 것이 아니라, 실제 프로젝트에서 보안 검토가 어떤 근거와 결정으로 이어지는지 경험합니다. 문서 분석만으로 끝내지 않고, 작은 격리 행동 profile에서 공격 전 상태, 패치, 같은 공격의 차단과 탐지까지 실행 근거로 연결합니다.

실제 파일은 [`projects/synthetic-service-security-review`](../projects/synthetic-service-security-review/README.md)에 있습니다.

## 1. 시나리오

`LedgerLab`은 사용자가 account report를 생성하고 내려받는 가상 서비스입니다.

```text
browser
  → public gateway
  → account API
  → database
        │
        └→ report queue
             → report worker
             → object storage

source repository
  → CI
  → internal package proxy
  → artifact registry
  → runtime

모든 component
  → audit sink
```

제공 자료에는 다음 약한 경계의 후보가 있습니다.

- report object authorization의 일관성
- worker identity의 resource scope
- mutable package·artifact trust
- audit event의 actor·resource field
- incident runbook의 공급망 시나리오 coverage

후보가 모두 confirmed finding이라는 뜻은 아닙니다. evidence를 사용해 판정합니다.

## 2. 필수 profile과 선택 확장

### Analysis + isolated behavior profile — 필수

제공된 문서·JSON·JSONL을 분석해 보안 산출물을 작성하고, [격리된 공격 경로 실습](../exercises/07-isolated-attack-path/README.md)의 작은 Python model을 수정합니다. 외부 network, container, 실제 credential과 관리자 권한은 필요하지 않습니다.

필수 실행 근거는 다음 하나의 trace를 증명해야 합니다.

```text
FND → THR → REQ → TEST → PATCH → DET → incident/recovery → release decision
```

- canonical skeleton에서 cross-owner·cross-job 접근이 허용되는 취약 상태 proof
- 수정 구현의 SHA-256과 skeleton 대비 patch diff
- 정상 owner/job 기능, 경계와 deny-all·scope bypass·탐지 누락 known-bad 회귀 결과
- 같은 cross-owner·cross-job 요청의 corrected deny event
- detector positive·benign negative 결과
- 실행 뒤 cleanup, 관찰 blind spot과 production에 일반화할 수 없는 범위

### Full service implementation profile — 선택 확장

동일한 contract를 로컬 service·container로 넓혀 직접 구현할 수 있습니다. 이 확장은 필수 isolated behavior profile을 대체하지 않으며, 의도한 취약점과 수정 상태를 synthetic state oracle과 외부 verifier로 확인합니다.

구현 profile도 다음을 금지합니다.

- 외부 egress
- 실제 credential·user data
- host mount·privileged container
- 제3자 service 호출
- persistence·evasion
- service resource exhaustion

## 3. 단계별 산출물

### Stage 1. 평가 계약

`scope.md`

- authorization
- in·out of scope
- allowed·prohibited action
- request·resource budget
- stop condition
- evidence handling
- cleanup

### Stage 2. system context와 threat model

`threat-model.md`

- asset·actor·capability
- trust boundary·data flow
- threat statement
- attack path
- assumption·unknown

### Stage 3. finding 검증

`findings.json`

candidate 판정, 처리와 수명 주기를 서로 다른 축에 기록합니다.

```text
validation_status: confirmed | false-positive | not-reproducible | unknown
treatment: remediate | mitigate | accept | defer | not-applicable | null
lifecycle_status: open | assigned | in-progress | ready-for-retest | closed | reopened
duplicate_of: FND-* | null
```

`confirmed`에는 causal mechanism과 proof oracle을, `false-positive`에는 반증한 가정과 counterevidence를, `not-reproducible`·`unknown`에는 미확인 범위·다음 안전한 evidence·reopen trigger를 기록합니다. evidence가 부족한 `unknown`·`not-reproducible`은 treatment를 `null`로 둘 수 있고, 명시적 `defer`에는 owner와 review date·trigger를 남깁니다. `not-applicable`은 false positive에 사용합니다. `accept`는 confirmed finding에만 사용할 수 있으며 authority, owner, expiry, compensating control, monitoring과 재검토 trigger가 필요합니다.

아직 없는 `REQ`·`TEST`·`PATCH`·`DET`를 채우기 위해 ID를 만들지 않습니다. non-confirmed finding의 trace 배열은 evidence가 실제로 연결된 곳까지만 기록하고 나머지는 비워 둘 수 있습니다.

### Stage 4. 보안 requirement와 test

`security-requirements.md`
`test-plan.md`

- threat-to-requirement trace
- normal·boundary·failure matrix
- test oracle
- known-bad mutation
- isolated behavior profile의 runtime evidence

### Stage 5. remediation과 hardening

`remediation-plan.md`

- containment
- causal root fix와 정상 기능을 보존하는 최소 change set
- similar path
- credential·data cleanup
- regression
- deployment·rollback
- retest·close condition

### Stage 6. telemetry와 detection

`detection-plan.md`

- event schema
- identity chain
- detection hypothesis
- analytic
- known positive·negative
- triage
- pipeline health

`DET-*`는 isolated behavior profile에서 같은 공격의 corrected deny event를 positive로, 정상·중복·순서가 바뀐 event를 negative로 확인합니다.

### Stage 7. incident timeline와 recovery

`incident-timeline.md`

- FACT·HYPOTHESIS·DECISION·ACTION·RESULT·UNKNOWN
- incident scope
- containment trade-off
- evidence preservation
- trusted recovery
- communication

timeline은 같은 `FND-*`, `PATCH-*`, `DET-*`를 참조하고, 복구의 trust anchor와 아직 재수립하지 못한 신뢰를 구분합니다.

### Stage 8. release decision

`final-report.md`

- confirmed state
- open risk
- evidence limitation
- go·conditional go·no-go
- risk owner·expiry
- production validation
- next project step

합성 실행 결과를 production 검증이라고 부르지 않습니다. 승인된 합성 post-release 검사 결과와 별도의 production validation 계획, 실행 권한 owner를 구분합니다.

## 4. 평가 기준

### 불합격 사례

- tool·attack 이름만 나열함
- finding status에 evidence가 없음
- 실제 중요 data를 얻어야만 impact를 증명한다고 가정함
- patch만 있고 regression·detection·cleanup이 없음
- 모든 log를 저장하자는 결론만 있음
- risk score만으로 priority를 정함
- 범위 밖 provider를 직접 test하도록 제안함
- unknown을 숨기고 안전하다고 선언함

### 합격 기준

- 모든 주장에 evidence 또는 unknown 표시가 있음
- attack path의 precondition·postcondition이 연결됨
- 같은 finding에서 requirement·test·patch·event·runbook·release trace가 있음
- root cause와 similar-path review가 있음
- prevention·detection·recovery가 모두 있음
- residual risk·owner·expiry가 있음
- 안전 범위와 cleanup이 명확함

## 5. 자동 검사

tracked template를 덮어쓰지 않는 도구로 작업 directory를 만듭니다.

```sh
python3 scripts/new_workspace.py capstone
```

취약 proof를 보존한 뒤 `work/behavior-lab/ledgerlab_policy.py`를 수정합니다. 문서와 구현을 완성한 뒤 행동 evidence와 patch를 생성하고 전체 검사를 실행합니다.

```sh
python3 scripts/capture_capstone_behavior.py \
  projects/synthetic-service-security-review/work

python3 scripts/verify_capstone.py \
  projects/synthetic-service-security-review/work
```

이 명령은 learner Python을 현재 process 권한으로 불러와 실행하며 OS sandbox가 아닙니다. 자신이 검토한 코드만 실행하고, 구현에서 network·subprocess·저장소 밖 파일 접근을 사용하지 않습니다.

검사기는 파일 구조, 상태별 JSON 계약, canonical ID trace를 확인하고 learner implementation을 다시 실행해 제출된 behavior evidence·fingerprint·patch와 비교합니다. root cause의 인과성, patch의 최소성, 우회 경로, detector의 실제 오탐·미탐과 release/risk 판단의 기술적 타당성은 대신 판정하지 않습니다.

## 6. 선택 full service profile의 권장 구조

```text
local gateway
+ API
+ worker
+ package proxy stub
+ object storage stub
+ audit sink
+ external verifier
```

중요한 점:

- intentional weakness는 목록과 code owner가 명확합니다.
- unintended vulnerability가 없는지 별도 review합니다.
- synthetic flag 외 data는 없습니다.
- attacker와 verifier는 production credential을 가지지 않습니다.
- corrected profile은 동일한 regression에서 차단됩니다.
- detection fixture와 incident timeline이 실제 event에서 생성됩니다.

필수 isolated behavior profile이 보장하는 범위는 합성 in-memory authorization·audit·detection contract뿐입니다. full service 확장은 network·process·container 경계를 더 관찰할 수 있지만 production IAM, provider audit completeness와 실제 운영 복구를 자동으로 보장하지 않습니다.

## 7. guide 이후

Capstone을 완료한 뒤 다음 중 하나로 이동합니다.

- 오픈소스의 security test·regression 추가
- dependency·artifact provenance 도구 기여
- parser·protocol·file format의 fuzz target 추가
- authorization·identity library의 bug 재현·패치
- detection rule과 fixture 기여
- incident·hardening·release 문서 개선

단계는 [프로젝트 진입 지도](../reference/project-entry-map.md)에 있습니다.
