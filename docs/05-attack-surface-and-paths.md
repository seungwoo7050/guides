# 공격 표면과 공격 경로

공격 표면은 공개 port 목록이 아닙니다. 공격자가 **관찰·호출·변경·위임·재사용할 수 있는 모든 경계**를 포함합니다. 공격 경로는 그 경계에서 얻은 capability가 다음 경계의 precondition이 되는 연속된 상태 전이입니다.

DNS·routing·transport·TLS의 상세 동작은 `computer-networks`, process·permission·filesystem의 기본 관찰은 `unix-systems`와 `operating-systems`, HTTP·session 구현은 `web-app`, 배포·backup 운영은 `web-infra`가 정본입니다. 이 장은 그 기반에서 드러난 entry point와 identity·data·delivery·recovery trust를 **공격 가능한 capability edge와 검증 근거**로 바꾸는 범위만 소유합니다.

## 1. 공격 표면의 여섯 관점

### Interface

- public·internal API
- admin UI와 maintenance endpoint
- message queue·webhook·file import
- package·plugin·extension interface
- debug·health·metrics endpoint

### Identity

- user session
- service account와 workload identity
- CI·deployment identity
- backup·registry·DNS credential
- signing key와 certificate
- emergency·break-glass account

### Execution

- interpreter·template·query engine
- shell·process spawn
- plugin·hook·job runner
- build script·installer
- deserializer·parser

### Storage

- database row와 tenant boundary
- object storage key·prefix
- local file·temporary directory
- cache와 search index
- backup과 snapshot
- audit log

### Delivery

- source repository
- dependency resolver
- CI runner
- build environment
- registry와 artifact
- deployment controller

### Recovery와 관측

- log·metric·trace sink
- alert routing
- incident tooling
- backup catalog
- restore credential
- runbook과 status page

관측·복구 경계가 공격 표면에서 빠지면, 공격자가 증거와 복구 원본을 함께 손상시키는 경로를 놓칩니다.

## 2. entry point와 trust decision

각 entry point에서 다음 decision을 적습니다.

```text
누가 호출했는가?
어떤 identity를 신뢰하는가?
무엇을 하도록 허용하는가?
어떤 data를 interpreter·storage·다른 service로 전달하는가?
결과와 거절을 어디에 기록하는가?
```

예를 들어 gateway가 `X-User-ID`를 덮어쓴다는 가정이 있더라도 internal service가 직접 호출될 수 있다면 같은 header를 신뢰해서는 안 됩니다.

## 3. capability graph

attack path를 host 목록보다 capability graph로 그립니다.

노드 예:

```text
public request 전송
일반 user session 사용
report identifier 관찰
worker queue에 job 생성
service token 읽기
object storage prefix 읽기
release artifact 바꾸기
backup 삭제
```

edge에는 반드시 다음을 적습니다.

- precondition
- 사용한 weakness 또는 trust assumption
- action
- postcondition으로 얻는 capability
- 필요한 evidence
- 현재 control

## 4. capability가 전파되는 방식

### Identity reuse

한 service가 다른 service에 caller identity 대신 자신의 광범위한 token을 사용하면 원래 사용자 범위가 사라질 수 있습니다.

### Data-to-control 전환

단순 데이터로 취급한 값이 path, query, template, command, configuration 또는 package 이름으로 해석되면 control capability가 생길 수 있습니다.

### Ambient authority

process가 작업과 무관한 file·socket·metadata·credential에 기본 접근할 수 있으면 하나의 bug가 더 넓은 권한으로 이어집니다.

### Trusted delivery

build·registry·update 경로는 정상 배포 권한으로 code execution을 전달합니다. 이 경로가 손상되면 runtime 취약점 없이도 중요 자산에 도달할 수 있습니다.

### Recovery coupling

production identity가 backup 삭제 권한까지 가지면 침해가 복구 원본 손상으로 이어질 수 있습니다.

## 5. attack path 작성 예

```text
Initial capability
  일반 사용자 session

Step 1
  precondition: 다른 report ID를 관찰할 수 있음
  weakness: download route의 object authorization이 중앙화되지 않음
  postcondition: 다른 사용자의 report content를 읽을 가능성

Step 2
  precondition: report metadata에 internal object key가 포함됨
  weakness: worker와 user-facing API가 같은 storage namespace를 공유함
  postcondition: storage key pattern을 이해함

Step 3
  precondition: worker token을 얻거나 worker request를 조작할 수 있음
  weakness: token scope가 모든 tenant prefix를 읽을 수 있음
  postcondition: 대량 data access 가능성
```

검증하지 않은 단계는 `hypothesis`로 표시합니다. 하나의 단계가 false positive면 전체 경로가 끊길 수 있습니다.

## 6. automated actor와 경로 조합

자동화된 actor는 다음 특성 때문에 사소해 보이는 edge를 더 위험하게 만들 수 있습니다.

- 많은 identifier·parameter·state 조합을 반복합니다.
- 실패를 기록하고 다른 경로를 선택합니다.
- 여러 service의 약한 신호를 함께 사용합니다.
- 긴 시간 동안 budget이 허용하는 만큼 계속 탐색합니다.
- 낮은 확률의 race나 timing condition을 반복합니다.

따라서 prevention은 단일 pattern 차단보다 권한·resource scope·rate·time·egress를 실제 경계에서 제한해야 합니다. detection은 단일 request뿐 아니라 identity·resource·service·시간을 연결해야 합니다.

## 7. choke point와 독립 방어

경로의 모든 edge를 같은 수준으로 고칠 필요는 없습니다. 먼저 다음을 찾습니다.

- 여러 경로가 공유하는 identity 발급 경계
- public에서 privileged network로 넘어가는 gateway
- artifact를 production trust로 승격하는 release verifier
- tenant·resource scope를 결정하는 중앙 policy
- backup·audit처럼 복구와 증거를 보호하는 경계

그러나 하나의 choke point만 신뢰하지 않습니다. 독립된 여러 통제를 둡니다.

```text
API object authorization
+ task-scoped service token
+ storage prefix policy
+ audit event
+ anomaly detection
```

## 8. attack surface inventory를 운영 상태로 만들기

inventory는 한 번 작성한 문서가 아닙니다.

필드 예:

```text
component
업무·위험 owner
상태 정본 owner
enforcement owner
evidence custodian
exposure
identity
entry point
data class
privilege
outbound dependency
logging
release source
recovery source
last reviewed
```

risk acceptance authority는 단순 `owner` 필드에서 추론하지 않고, 잔여 위험을 실제로 수용해야 할 때 별도로 연결합니다. topology·identity·policy·evidence의 소유자가 다르면 한 inventory row에 모두 기록합니다.

다음 변화는 inventory 갱신 trigger입니다.

- 새 endpoint·queue·bucket·repository
- 새로운 role·token·credential
- public exposure 또는 network policy 변경
- plugin·package source 변경
- CI·build·registry 경로 변경
- backup·logging provider 변경

## 9. path validation

경로를 검증할 때 가장 위험한 마지막 단계부터 실행하지 않습니다.

1. 각 edge의 정적·configuration evidence를 수집합니다.
2. 합성 resource와 test identity를 준비합니다.
3. 가장 낮은 영향의 edge부터 독립 검증합니다.
4. postcondition을 synthetic marker로 확인합니다.
5. 실제 중요 자산에 닿기 전에 중단합니다.
6. 각 edge의 prevention·detection evidence를 기록합니다.
7. cleanup과 credential revoke를 확인합니다.

다음 세 종류의 사례를 같은 초기 상태 계약에서 확인합니다.

| 사례 | 예 | 관찰할 결과 |
|---|---|---|
| 정상 | owner가 자신의 report를 읽고 worker credential이 발급된 job prefix를 읽음 | 허용 기능이 유지되고 올바른 allow event가 남음 |
| 경계 | prefix가 비슷한 다른 key, 누락된 owner·job context, 정확한 만료 시각, duplicate·out-of-order event | 문자열 prefix나 cache 추측이 아니라 canonical resource와 current policy로 일관되게 판정 |
| 대표 실패 | foreign owner read, cross-job·expired·revoked credential 사용 | 기본 거절, 보호 상태 불변, decision·reason·correlation·policy version 기록과 필요한 alert |

## 10. edge 증거와 종단 간 증명을 구분하기

edge 하나를 재현하면 그 초기 상태와 입력에서 특정 postcondition이 관찰됐다는 사실을 지지합니다. 다음 주장을 자동으로 증명하지는 않습니다.

- 앞 edge에서 얻은 identity·data가 다음 edge의 exact precondition으로 실제 전달됨
- 각 edge가 같은 deployment·policy·credential version과 시간에 함께 존재함
- cache·retry·queue·proxy가 중간 context를 바꾸지 않음
- 합성 marker 대신 실제 중요 자산에 같은 영향이 생김
- inventory에 없는 우회 경로가 없음

각 edge를 `hypothesis`, `evidence-supported`, `behavior-verified`로 표시하고 evidence의 version·시간·초기 상태를 연결합니다. 여러 edge가 개별 검증돼도 연결을 실행하지 않았다면 경로는 `not proven end-to-end`입니다. 반대로 격리 환경에서 전체 합성 경로를 실행해도 그 exact profile만 증명하며 production topology 전체를 보장하지 않습니다.

안전을 위해 마지막 영향 전에 중단한 경로는 실패한 과제가 아닙니다. 확인한 edge, 실행하지 않은 전이, 중단 이유와 추가로 필요한 승인·evidence를 명시하는 것이 올바른 결과입니다.

## 11. path-based remediation

한 finding을 패치한 뒤 전체 path를 다시 평가합니다.

- 다른 route에서 같은 root cause가 남았습니까?
- path가 다른 identity·storage·delivery 경로로 우회됩니까?
- compensating control이 runtime에서 실제 적용됐습니까?
- detection이 차단된 시도와 새로운 우회를 관찰합니까?
- recovery source가 여전히 독립적입니까?

## 12. 이 장의 산출물

하나의 시스템에 대해 다음을 작성합니다.

1. 여섯 관점의 attack surface inventory
2. capability node 12개 이상
3. attack path 3개
4. edge별 precondition·postcondition·evidence
5. 공통 choke point
6. prevention·detection·recovery mapping
7. 검증하지 못한 unknown
8. topology·identity·delivery 변화의 re-review trigger
9. 정상·경계·대표 실패와 보호 상태 oracle
10. edge별 검증 수준, version·시간과 `not proven end-to-end` 한계
11. 자동 검사가 판단하지 못하는 경로 연결·우회·production 적용에 대한 reviewer 질문

## 13. 완료 질문

- port가 열려 있지 않아도 공격 표면이 될 수 있는 것은 무엇입니까?
- host graph보다 capability graph가 유용한 이유는 무엇입니까?
- data가 control capability로 바뀌는 경계는 어디입니까?
- automated actor가 낮은 확률의 edge를 더 중요하게 만드는 이유는 무엇입니까?
- 한 edge를 수정한 뒤 전체 path를 다시 봐야 하는 이유는 무엇입니까?
- edge 하나의 합성 재현으로 전체 공격 경로를 confirmed라고 할 수 없는 이유는 무엇입니까?
- 전체 경로를 실행하지 않고 중단했을 때도 어떤 증거와 한계를 남기면 유효한 검토 결과가 됩니까?
