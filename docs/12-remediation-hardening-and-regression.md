# 수정, hardening과 회귀

취약점 수정은 한 request를 막는 patch에서 끝나지 않습니다. 공격자가 얻은 capability, 노출된 credential·data, 같은 root cause의 다른 path, 배포와 rollback까지 다뤄야 합니다.

## 1. 수정 범위를 네 층으로 나누기

### Immediate containment

현재 악용·확산을 줄이는 가역적 조치입니다.

- 위험 endpoint 일시 제한
- token revoke
- network·resource scope 축소
- feature flag 또는 traffic block

monitoring 강화는 containment의 효과와 새로운 시도를 관찰하지만 공격자의 capability나
attack-path edge를 제거하지 않습니다. 따라서 containment action과 detection·monitoring
action을 같은 완료 항목으로 세지 않고 각각 owner·evidence를 둡니다.

### Root-cause remediation

약점을 만든 설계·구현·운영 계약을 수정합니다.

- 중앙 authorization policy
- parameterized API
- task-scoped identity
- immutable artifact verification
- atomic state transition

### Hardening

같은 bug가 남아도 blast radius를 줄입니다.

- least privilege
- egress restriction
- read-only filesystem
- rate·resource limit
- independent audit·backup

### Recurrence prevention

개발 과정에서 같은 class를 줄입니다.

- secure abstraction
- linter·static rule
- test template
- review checklist
- coding standard
- default configuration

## 2. symptom patch와 root cause

예:

```text
Symptom patch
/download route에 owner check 한 줄 추가

Root-cause fix
모든 report read가 중앙 policy API를 통과하도록 repository·worker·export path를 통합하고,
subject·resource·action·tenant를 policy input으로 고정
```

root cause를 고치더라도 migration과 compatibility 위험을 평가합니다.

## 3. 최소 패치의 의미

최소 패치는 단순히 diff가 가장 작은 변경이 아닙니다. **정상 기능을 보존하면서 깨진
불변식을 모든 적용 가능한 path에서 복원하는 최소 change set**입니다. 한 route에 조건문을
추가했지만 export·worker·cache path가 같은 정책을 우회하면 작은 diff여도 최소 패치가
아닙니다. 반대로 중앙 policy 호출로 여러 파일이 바뀌더라도 그 변경이 불변식을 일관되게
복원하는 데 필요하다면 최소 범위일 수 있습니다.

patch scope를 다음처럼 기록합니다.

| Path | 적용 상태 | patch 전 oracle | 필요한 변경 | patch 후 oracle·evidence |
|---|---|---|---|---|
| owner API read | applicable | owner allow | policy context 고정 | allow + policy event |
| foreign API read | applicable | foreign data 노출 | 중앙 deny | no state change + deny event |
| export worker | applicable | cross-owner 가능 | job·tenant scope | intended export만 생성 |
| legacy cache | unknown | 조사 미완료 | owner·기한 지정 | 확인 전 close 금지 |

`N/A`는 해당 source→sink 또는 state transition이 구조적으로 존재하지 않음을 근거로 보일
때만 사용합니다. 구현하지 않았거나 test가 없다는 뜻으로 쓰지 않으며, architecture 변경 시
다시 검토할 trigger를 둡니다.

## 4. 유사 path 조사

finding의 source·sink·policy·identity pattern으로 search합니다.

- 같은 helper를 사용하지 않는 route
- batch·admin·export·mobile·legacy API
- background job과 retry path
- cache·search index·report generator
- 동일 dependency·base image를 사용하는 artifact
- 같은 secret·service account를 공유하는 workload

duplicate finding으로 묶을지 별도 owner와 deadline이 필요한지 결정합니다.

## 5. credential과 session cleanup

credential 노출 가능성이 있으면 patch만으로 충분하지 않습니다.

- 유효 credential·session 목록
- 발급·사용 log
- revoke·rotate 순서
- dependent service 전환
- cache·agent·client에 남은 copy
- old credential 사용 탐지
- signing key라면 artifact·release 신뢰 영향

과거 유효 credential이 현재 invalid하더라도 노출 기간 동안의 사용을 조사합니다.

## 6. data integrity와 derived state

잘못된 write가 가능했다면 영향을 받은 정본과 파생 상태를 찾습니다.

```text
primary record
→ cache
→ search index
→ report
→ event stream
→ analytics
→ backup
```

정본만 고쳐도 파생 상태가 오염된 채 남을 수 있습니다. rebuild·replay·invalidate 범위를 정합니다.

## 7. 배포와 rollback

보안 patch도 일반 변경과 같은 운영 계약이 필요합니다.

- exact artifact와 source revision
- migration·configuration change
- preflight
- staged rollout
- security test와 readiness
- runtime evidence
- rollback 조건
- rollback이 취약 version을 다시 활성화하는 위험

긴급 patch라도 검증·기록·review를 완전히 생략하지 않습니다. 시간을 줄일 수는 있지만 어떤 근거를 나중에 보완할지 적습니다.

서명과 provenance가 유효해도 compromised source·builder가 만든 취약 artifact일 수 있습니다.
검증 결과는 exact digest와 주장된 build 관계를 확인하는 evidence이며 patch의 안전성이나
builder의 신뢰를 대신하지 않습니다. rollback candidate도 동일한 source·builder·dependency·
configuration trust를 다시 평가합니다.

## 8. regression suite

최소 matrix:

- 원래 reproduction이 실패함
- 정상 사용은 성공함
- 다른 role·tenant·resource는 거절됨
- race·retry·parallel path에서 유지됨
- background·export·cache path도 동일함
- audit·detection event가 생성됨
- unavailable policy·dependency에서 정의한 fallback
- old credential·artifact가 거절됨

각 path를 `applicable-pass`, `applicable-fail`, `not-run`, `unknown`, 근거가 있는 `N/A`로
표시합니다. 원래 reproduction 하나가 실패한다는 사실만으로 다른 적용 path나 recovery
requirement까지 통과했다고 간주하지 않습니다.

## 9. retest independence

가능하면 원래 구현자와 다른 사람이 finding과 requirement를 기준으로 retest합니다. 같은 사람이 수행하면 원래 assumption을 반복할 수 있습니다.

retest packet:

```text
original finding
fix summary
changed files·configuration
new requirement·test
deployed version·digest
credential·data cleanup
remaining exception
```

## 10. compensating control

근본 수정이 지연될 때 임시 통제를 사용할 수 있습니다.

좋은 compensating control:

- 실제 attack-path edge를 끊습니다.
- 적용 범위와 bypass 조건이 명확합니다.
- runtime evidence가 있습니다.
- owner와 expiry가 있습니다.
- root fix를 대체하지 않는다는 사실을 기록합니다.

예: public reachability를 제한하는 것은 external path를 줄이지만 internal actor와 stolen service identity에는 효과가 없을 수 있습니다.

탐지 rule이나 강화된 monitoring만으로는 첫 impact를 막지 못합니다. 빠른 대응으로 exposure를
줄이는 보조 조건이 될 수는 있지만, 어떤 event가 관찰되지 않는지와 alert 뒤 실제로 누가
얼마 안에 조치하는지를 함께 기록해야 합니다.

## 11. patch confidence

다음 질문으로 confidence를 평가합니다.

- root cause를 설명할 수 있는가?
- 같은 class의 path를 조사했는가?
- known-bad mutation을 test가 거부하는가?
- deployed runtime에서 확인했는가?
- credential·data·artifact cleanup을 완료했는가?
- detection과 incident review가 필요한가?
- rollback이 취약 상태를 복원하지 않는가?
- residual risk owner가 있는가?

## 12. vulnerability management 연결

finding lifecycle을 변경 관리에 연결합니다.

```text
owner assigned
→ target date
→ fix branch·review
→ security regression
→ release artifact
→ production validation
→ cleanup
→ retest
→ close
```

SLA 숫자만으로 품질을 판단하지 않습니다. 중요한 것은 exposure·impact·attack path와 수정 confidence입니다.

## 13. 이 장의 산출물

confirmed finding 하나에 대해 다음을 작성합니다.

1. containment
2. root-cause fix
3. similar-path search
4. hardening
5. credential·session cleanup
6. data·derived state cleanup
7. regression matrix
8. deployment·rollback
9. retest packet
10. residual risk와 close condition
11. path별 patch applicability·N/A·unknown 근거

## 14. 완료 질문

- original request를 막는 것과 root cause를 수정하는 것은 어떻게 다릅니까?
- credential 노출 가능성이 있으면 patch 외에 무엇이 필요합니까?
- derived state가 남아 있는지 왜 조사해야 합니까?
- rollback이 보안 위험을 다시 활성화할 수 있는 경우는 언제입니까?
- compensating control이 유효함을 어떻게 증명합니까?
- 가장 작은 diff와 불변식을 복원하는 최소 패치는 어떻게 다릅니까?
- monitoring을 containment 완료로 세면 어떤 위험이 남습니까?
