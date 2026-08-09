# 평가 범위, 허가와 Rules of Engagement

보안 테스트의 첫 산출물은 scan 결과가 아니라 **누가 무엇을 어떤 방식으로 어디까지 검증하도록 허가했는지**를 나타내는 계약입니다. 범위와 중단 조건이 없으면 기술적으로 흥미로운 행동도 안전한 평가가 아닙니다.

## 1. 허가가 먼저입니다

다음 중 하나가 명확해야 합니다.

- 자신이 소유하고 통제하는 로컬 환경
- 교육 목적의 명시적 lab·CTF
- 조직이 문서로 승인한 test environment
- 공개 vulnerability disclosure program이 허용한 자산과 행동

공개 인터넷에 보인다는 사실은 테스트 허가가 아닙니다. 계정이 있다는 사실도 다른 사용자·tenant·provider의 자산을 검증할 권한을 주지 않습니다.

### 허가는 version이 있는 상태입니다

허가 문서는 한 번 받은 서명이 아니라 수명이 있는 security state입니다.

```text
draft → approved → active → paused/revised → expired/revoked
```

- `draft`: 평가자가 제안했지만 어떤 test action도 허가하지 않습니다.
- `approved`: 권한자가 특정 version의 scope·identity·시간·행동·budget을 승인했지만 시작 시각 전일 수 있습니다.
- `active`: 현재 시각과 환경이 승인 조건에 맞아 enforcement가 허용할 수 있습니다.
- `paused`: stop condition, topology 불일치 또는 incident 때문에 새 행동을 중단합니다. 변경 없는 재개도 승인된 연락 경로의 결정을 기록합니다.
- `revised`: scope·identity·시간·허용 행동·budget·evidence handling 중 하나가 바뀐 새 draft입니다. 이전 승인을 상속하지 않고 다시 승인받습니다.
- `expired`: 승인 종료 시각을 지났습니다.
- `revoked`: 권한자가 종료 시각 전이라도 허가를 철회했습니다.

`expired`와 `revoked` version은 다시 `active`로 돌리지 않습니다. 필요한 경우 새 version을 `draft`에서 시작합니다. evaluator는 자신의 허가를 승인·연장·재개할 수 없습니다.

각 version에는 최소한 다음을 고정합니다.

```text
authorization_id와 version
supersedes
approved_by·approved_at
valid_from·valid_until
exact asset identifiers와 environment
evaluator identity·role
allowed·forbidden actions
request·resource budget
stop condition·escalation
evidence·cleanup policy
```

authorization state는 승인 권한자가 바꾸고, enforcement owner는 실제 proxy·sandbox·account·resource limit에 현재 active version을 적용하며, evidence custodian은 승인본과 상태 변경 기록을 보존합니다. 업무·위험 소유자와 risk acceptance authority가 같은 사람인지도 추측하지 않고 명시합니다.

| 사례 | 판단 | 기대 결과 |
|---|---|---|
| 정상 | active version의 test identity가 지정한 staging asset에서 허용 행동 수행 | budget 안에서 실행되고 authorization version이 evidence에 기록됨 |
| 경계 | 정확한 시작·종료 시각, asset alias 변경, redirect, retry, evaluator 교대 | current version으로 단일하게 판정하며 모호하거나 범위 밖이면 실행 전에 중단 |
| 대표 실패 | expired·revoked version, 승인되지 않은 새 action·identity, topology 불일치 | 기본 거절하고 보호 상태를 바꾸지 않으며 pause·escalation 근거를 남김 |

## 2. 평가 charter

최소한 다음을 적습니다.

```text
목적
authorization ID·version·상태
승인자와 연락처
평가자
시작·종료 시간
in-scope 자산과 version
out-of-scope 자산
허용 행동
금지 행동
요청·동시성·데이터 제한
중단 조건
evidence 저장·전달·폐기
incident escalation
cleanup과 복구 확인
```

## 3. 자산 식별

도메인 하나만 적으면 부족합니다.

- 정확한 hostname·IP·repository·application ID
- production·staging·local 구분
- public endpoint와 admin endpoint
- test account와 role
- mobile·API·worker·queue·storage 등 포함 component
- third-party provider와 shared infrastructure
- 현재 release·commit·image digest

동적으로 변하는 cloud 자산이라면 tag·account·project·namespace 같은 식별 기준을 추가합니다.

## 4. 허용 행동과 금지 행동

### 허용 행동 예

- 제공된 test account로 정상 request와 권한 거절 확인
- 합성 object를 생성·조회·삭제
- rate limit 안에서 자동화된 회귀 요청
- 로컬 container에서 crash와 memory error 재현
- 승인된 source와 binary의 정적 분석
- 지정된 log와 event export 읽기

### 금지 행동 예

- 실제 사용자 계정 추측·탈취
- 대량 password guessing과 credential stuffing
- phishing, social engineering과 physical access 시도
- 서비스 중단을 유발할 수 있는 resource exhaustion
- persistence 설치, 방어 기능 비활성화, 로그 삭제
- 범위 밖 host·tenant·bucket·repository 접근
- 실제 개인정보·secret 다운로드
- 제3자 service에 공격 traffic 전달

허용되지 않은 행동을 “영향 확인을 위해 필요했다”고 사후 정당화하지 않습니다.

## 5. 최소 영향 원칙

취약점 검증은 다음 순서로 진행합니다.

```text
정적 근거
→ non-mutating request
→ 합성 resource에 제한된 상태 변경
→ 필요한 최소 영향 증명
→ 즉시 중단과 cleanup
```

예를 들어 다른 사용자의 데이터 접근 가능성을 검증할 때 실제 내용을 대량 수집하지 않습니다. 합성 account 두 개와 synthetic marker를 사용해 cross-owner read 여부만 확인합니다.

## 6. 중단 조건

다음 상황에서는 즉시 중단하고 승인자에게 알립니다.

- 범위 밖 자산으로 request가 전달됩니다.
- 실제 개인정보·secret·production key가 노출됩니다.
- 예상하지 못한 data mutation 또는 service degradation이 발생합니다.
- logging·monitoring·backup 같은 보호 기능이 손상됩니다.
- 다른 사용자의 작업이나 shared environment에 영향이 보입니다.
- test account가 아닌 identity가 사용됐습니다.
- 허가 문서와 실제 topology가 다릅니다.

중단 뒤 무엇을 보존하고 무엇을 되돌릴지도 미리 정합니다.

## 7. 요청과 자원 budget

자동화된 도구와 agent는 사람이 예상한 것보다 많은 행동을 수행할 수 있습니다.

- 최대 request 수와 초당 request
- 동시 connection·process·job 수
- 생성 가능한 data 양
- CPU·memory·disk·network 한계
- 실행 시간과 비용 한계
- retry 횟수
- 특정 오류나 alert 발생 시 kill condition

budget은 prompt나 문서만으로 강제하지 않고 실제 proxy·sandbox·resource limit에서 적용합니다.

enforcement에는 authorization version도 전달합니다. 문서는 `active`인데 test account role, proxy allowlist 또는 rate limit이 이전 version이면 허가와 실행 범위가 달라집니다. 시작 전 작은 정상·경계·거절 probe로 현재 적용 상태를 확인하고, 결과에 version과 timestamp를 남깁니다.

## 8. 계정과 데이터

- 각 evaluator에게 별도 test identity를 발급합니다.
- role과 scope를 명시합니다.
- 실제 사용자 data를 복제하지 않습니다.
- synthetic marker로 소유권과 변조를 확인합니다.
- test secret은 짧은 수명과 제한 scope를 사용합니다.
- 종료 뒤 account·token·object를 폐기합니다.

## 9. 증거 handling

보안 증거는 그 자체로 민감할 수 있습니다.

```text
무엇을 수집하는가
왜 필요한가
누가 접근하는가
어디에 암호화해 저장하는가
어떤 식별자를 redaction하는가
언제 폐기하는가
hash·timestamp·source를 어떻게 남기는가
```

원본과 분석 copy를 구분합니다. 원본을 직접 편집하지 않습니다.

## 10. 제3자와 shared responsibility

평가 대상이 SaaS, CDN, cloud, identity provider 또는 package registry를 사용하면 다음을 구분합니다.

- 자신의 configuration과 application behavior
- provider가 허용한 test 범위
- provider 내부 구현
- 다른 tenant와 shared control plane

자신의 애플리케이션을 평가한다는 이유로 provider 자체를 scan하거나 우회하지 않습니다.

이 장은 안전한 기술 평가 계약의 구조를 다룹니다. 계약의 법적 효력, 관할권, 개인정보 처리, 규제·감사 요건과 공식 조직 권한은 법무·privacy·compliance와 해당 조직의 승인 절차가 소유합니다. template를 채웠다는 사실만으로 그 승인을 대신하지 않습니다.

## 11. 발견 즉시 escalation할 항목

모든 finding을 보고서 완료까지 기다리지 않습니다.

- active exploitation 징후
- 실제 credential·signing key·backup key 노출
- 범위 밖 데이터 접근
- production integrity 손상
- 즉시 악용 가능한 public remote execution 가능성
- 조사 중인 보호 통제의 비활성화

연락 경로, 확인 응답 시간과 평가 일시 중지 여부를 정합니다.

## 12. disclosure와 보고

자신이 소유하지 않은 프로젝트에서 취약점을 발견했다면 공개 issue에 먼저 쓰지 않습니다.

- `SECURITY.md`와 vulnerability disclosure policy 확인
- 지정된 private channel 사용
- 재현에 필요한 최소 정보 제공
- 실제 secret·사용자 data 첨부 금지
- maintainer와 공개 시점 조정
- patch가 배포되기 전 불필요한 공격 세부 공개 금지

## 13. 이 장의 산출물

[안전한 실습 정책](../reference/safe-lab-policy.md)과 [평가 계약 template](../reference/assessment-charter-template.md)을 사용해 다음을 작성합니다.

1. 목적과 승인자
2. exact in-scope asset 목록
3. out-of-scope와 third-party 경계
4. 허용·금지 행동
5. request·resource budget
6. test identity·synthetic data 계획
7. stop condition과 escalation
8. evidence handling과 retention
9. cleanup·recovery 확인
10. authorization version, 상태 이력과 superseded version
11. 정상·경계·대표 실패 probe와 실제 enforcement evidence
12. 자동 확인이 판단하지 못하는 법적·조직적 권한과 사람 검토 질문

작성된 charter의 존재는 enforcement를 증명하지 않습니다. reviewer는 승인자의 실제 권한, current version과 실행 환경의 일치, stop·revoke 전파, 범위 밖 redirect의 거절, evidence 보존과 cleanup 결과를 별도 근거로 확인합니다. 자동 검사는 필드와 형식 또는 합성 행동을 확인할 수 있지만 승인 의사의 진정성이나 production의 모든 경계를 보장하지 않습니다.

## 14. 완료 질문

- 공개 endpoint가 테스트 허가를 의미하지 않는 이유는 무엇입니까?
- 취약점 영향과 최소 영향 원칙을 어떻게 함께 만족합니까?
- 자동화된 evaluator에 필요한 budget은 어디에서 강제해야 합니까?
- 범위 밖 component가 attack path에 포함되면 어떻게 처리합니까?
- 평가 중 실제 incident를 발견하면 어떤 계약이 먼저 작동합니까?
- scope·identity·시간·허용 행동이 바뀌면 기존 승인에 메모만 추가하지 않고 새 version을 승인해야 하는 이유는 무엇입니까?
- 승인 문서가 `active`여도 실제 평가를 시작하기 전에 enforcement 상태를 확인해야 하는 이유는 무엇입니까?
