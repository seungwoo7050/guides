# Infrastructure as Code와 state

## 1. 선언 파일만으로 infrastructure를 소유할 수 없습니다

Infrastructure as Code(IaC)는 cloud resource를 text file로 적는 것보다 넓은 계약입니다.

```text
configuration
+ state
+ provider가 관찰한 원격 자원
+ plan과 승인
+ apply 실행 기록
+ 권한·locking·복구 절차
```

configuration은 원하는 구조를 표현합니다. state는 configuration의 resource instance와 실제 원격 object identity를 연결합니다. 원격 자원은 provider API가 가진 실제 상태입니다. 셋이 다르면 어떤 변경이 일어날지 다시 계산해야 합니다.

Terraform과 OpenTofu의 state 목적과 locking 자료는 [source index의 IaC state](../reference/source-index.md#iac-state)를 확인하세요.

## 2. Resource identity를 안정적으로 관리합니다

IaC tool은 일반적으로 다음 관계를 기대합니다.

```text
configuration의 한 resource instance
↔ state의 한 binding
↔ 원격 시스템의 한 object
```

이 관계가 깨지는 대표 사례:

- 같은 원격 자원을 두 state에서 관리합니다.
- resource address를 바꾸고 move 선언 없이 apply합니다.
- console에서 자원을 교체했지만 state를 갱신하지 않습니다.
- import를 여러 번 수행해 identity가 중복됩니다.
- provider가 보고한 ID와 실제 object의 수명이 달라집니다.

platform team은 module 사용법보다 먼저 **누가 어떤 state unit에서 어떤 resource identity를 소유하는지** 정해야 합니다.

## 3. State unit을 blast radius로 나눕니다

하나의 거대한 state는 모든 dependency를 한 번에 볼 수 있지만 다음 위험이 있습니다.

- plan과 lock 범위가 커집니다.
- 작은 변경도 넓은 권한을 요구합니다.
- state 손상과 잘못된 apply의 blast radius가 커집니다.
- 팀별 변경 속도와 ownership이 결합됩니다.

너무 잘게 나누면 output 전달과 dependency가 복잡해집니다.

분리 기준:

- 생명주기가 함께 움직이는가?
- 같은 팀과 권한 경계가 소유하는가?
- 같은 failure·rollback 단위인가?
- 자주 함께 plan해야 하는가?
- 한 unit의 삭제가 다른 unit을 암묵적으로 파괴하는가?

예:

```text
organization foundation state
account/project state
regional network state
cluster state
shared platform service state
team environment state
```

환경 이름만으로 state를 나누지 않고 ownership과 blast radius를 함께 봅니다.

## 4. State는 민감한 운영 데이터입니다

state에는 resource ID, endpoint와 provider에 따라 secret 값이 포함될 수 있습니다.

필수 통제:

- remote backend와 access control
- encryption at rest와 transport protection
- locking 또는 동등한 동시 변경 방지
- version history와 복구 절차
- read와 write 권한 분리
- audit log
- local copy와 CI artifact의 수명 제한
- state를 Git에 commit하지 않는 검사

`sensitive` 표시는 화면 출력을 가릴 수 있지만 state에서 값을 제거한다는 뜻은 아닙니다. state 자체를 secret처럼 다룹니다.

## 5. Plan은 변경 제안이지 미래의 보장이 아닙니다

plan은 다음 시점의 입력으로 계산됩니다.

```text
configuration revision
+ provider version과 schema
+ state snapshot
+ refresh에서 관찰한 remote state
+ variable와 credentials
```

plan과 apply 사이에 remote state나 configuration이 바뀌면 이전 plan의 판단이 유효하지 않을 수 있습니다.

자동화 계약:

- saved plan에 source revision과 state serial을 연결합니다.
- 승인 뒤 다른 revision을 apply하지 않습니다.
- apply 주체는 plan 생성 주체와 동일하거나 검증 가능한 handoff를 사용합니다.
- destructive action은 별도 분류와 승인 정책을 둡니다.
- plan artifact의 보존 기간과 민감도를 정합니다.
- apply 뒤 새 state와 outputs를 실행 기록에 연결합니다.

## 6. Drift를 세 종류로 나눕니다

### 허가되지 않은 변경

console, CLI 또는 다른 automation이 IaC 정본을 우회했습니다. 원인을 조사하고 configuration으로 되돌리거나 정식 import합니다.

### 외부 시스템의 정상 변화

provider가 자동으로 바꾸는 field, autoscaling과 server-generated metadata처럼 configuration이 완전히 고정하지 않는 상태입니다. 어떤 field를 소유하는지 명시합니다.

### 의도된 긴급 변경

사고 완화를 위해 live state를 먼저 바꿨습니다. 변경 ticket, owner, 만료 시간과 정본 반영 절차를 남깁니다.

“drift가 있다”만으로 자동 원복하지 않습니다. 원복이 장애를 다시 만들거나 data loss를 유발할 수 있습니다.

## 7. Module은 재사용 단위이자 변경 계약입니다

좋은 module은 resource 수를 숨기는 wrapper가 아닙니다.

- 사용자가 선택해야 하는 최소 입력을 노출합니다.
- 안전한 default와 금지 조합을 검증합니다.
- output을 downstream contract로 관리합니다.
- provider와 runtime assumption을 문서화합니다.
- upgrade와 state migration 경로를 제공합니다.
- 내부 resource address를 불필요하게 public contract로 만들지 않습니다.

module version을 올릴 때 API schema 변경과 state address 변경을 분리해 검토합니다.

## 8. Refactoring은 state migration을 포함합니다

파일 이동이나 module 분리만으로는 원격 자원의 identity가 자동 보존되지 않을 수 있습니다.

안전한 순서:

```text
현재 state와 원격 identity 확인
→ migration 전 backup과 lock
→ move/import/remove 계획
→ no-op 또는 의도한 plan 확인
→ 작은 범위 적용
→ remote object identity와 dependency 검증
→ 이전 경로 제거
→ audit와 rollback 근거 보존
```

직접 state JSON을 편집하지 않습니다. tool이 제공하는 move/import/state command와 versioned configuration을 사용합니다.

## 9. Destroy를 정상 기능으로 설계합니다

platform API가 environment 삭제를 제공한다면 IaC destroy도 제품 기능입니다.

확인 항목:

- data retention과 legal hold
- shared resource reference
- backup과 export
- DNS·certificate·identity revoke 순서
- final snapshot
- protection flag와 approval
- orphan detection
- 실패한 cleanup 재시도
- 비용이 계속 발생하는 잔여 자원 검사

“destroy가 성공했습니다”는 command exit code만으로 판정하지 않습니다. provider inventory와 비용·DNS·identity 상태를 다시 확인합니다.

## 10. IaC pipeline과 platform controller 경계

platform controller가 provider SDK를 직접 호출할 수도 있고 IaC run을 요청할 수도 있습니다. 두 방식 모두 state owner는 하나여야 합니다.

권장 상태 흐름:

```text
platform resource generation
→ IaC configuration revision 또는 run input
→ plan ID
→ policy·approval
→ apply operation ID
→ state version
→ outputs
→ platform condition 업데이트
```

controller restart 뒤에도 operation ID와 state version에서 진행 상태를 복구할 수 있어야 합니다.

## 11. Evidence

각 변경에 남길 최소 근거:

- source revision과 module/provider version
- state unit과 prior serial/version
- plan summary와 destructive action
- 승인자와 정책 결과
- apply operation ID와 종료 결과
- new state version과 output checksum
- drift 또는 manual intervention
- rollback 또는 후속 작업

## 12. 실습

[`04-iac-state`](../exercises/04-iac-state/)에서 state partition, backend 통제, plan/apply, drift, destructive change와 migration 절차를 설계합니다.

다음 반례를 반드시 검토합니다.

- 같은 network를 두 state가 import했습니다.
- 승인 뒤 configuration revision이 바뀌었습니다.
- 긴급 console 변경이 incident를 완화했습니다.
- module refactor가 resource recreate를 제안합니다.
- deletion이 shared database를 함께 제거하려 합니다.
