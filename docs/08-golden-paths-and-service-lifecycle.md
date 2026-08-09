# Golden path와 service lifecycle

Golden path는 모든 팀을 하나의 framework와 repository 구조에 가두는 표준이 아닙니다. 반복되는 안전·운영 요구를 미리 해결해, 일반적인 서비스가 적은 결정으로도 조직의 지원 기준을 만족하게 만드는 **지원되는 경로**입니다.

좋은 golden path는 시작 template만 제공하지 않습니다. 생성, build, 배포, 운영, upgrade와 폐기까지 service lifecycle 전체를 책임집니다.

## 1. Paved road와 강제 표준

지원되는 경로는 다음 가치를 제공해야 합니다.

- 빠른 첫 성공
- 검증된 default
- 보안·관측·복구 기능의 기본 포함
- 반복 가능한 upgrade
- 문제 발생 시 명확한 지원 책임
- 필요할 때 벗어날 수 있는 경계

강제 표준은 사용자가 얻는 가치보다 플랫폼 팀의 편의를 우선할 때 생깁니다.

```text
모든 서비스가 같은 template을 써야 한다
하지만 변경된 template을 기존 서비스에 적용할 방법은 없다

모든 팀이 같은 CI workflow를 복사한다
하지만 수정이 필요하면 수백 저장소를 직접 고친다

예외를 금지한다
하지만 지원되지 않는 요구를 해결할 공식 절차가 없다
```

Golden path는 “기본적으로 선택할 이유”를 제공해야 하며, 단지 다른 선택을 금지해서 채택률을 높이면 안 됩니다.

## 2. Service lifecycle

서비스의 수명을 단계로 봅니다.

```text
Discover
→ Request
→ Create
→ Develop
→ Verify
→ Release
→ Operate
→ Change
→ Migrate
→ Deprecate
→ Retire
```

각 단계에는 다음이 필요합니다.

- 입력과 사전 조건
- 생성·변경되는 정본
- 성공 condition
- 실패와 재시도
- 소유자와 지원 경로
- 다음 단계로 넘어가는 evidence
- 취소와 rollback

### 예: Create

```text
입력
service ID, owner, runtime profile, data classification

생성
repository, catalog entity, build pipeline, environment request

완료
repository 보호 규칙 적용
catalog owner 확인
첫 artifact build 성공
preview 환경 smoke 성공

실패
이름 충돌, owner 없음, policy 거부, downstream timeout

복구
중복 생성 방지, 부분 생성 목록, retry 또는 cleanup
```

Template 파일이 생성됐다는 사실만으로 완료하지 않습니다.

## 3. Golden path의 계층

하나의 거대한 template보다 안정적인 계층으로 나눕니다.

### 조직 공통 계약

- identity와 owner
- source control과 review
- artifact identity와 provenance
- 기본 telemetry
- secret과 policy
- support와 lifecycle metadata

### Runtime profile

- stateless HTTP service
- background worker
- scheduled job
- event consumer
- static frontend
- data pipeline

### Language profile

- Java, TypeScript, Python, Go 등
- build·test·dependency scanning
- runtime base image와 종료 신호

### Capability add-on

- database
- cache
- message subscription
- public endpoint
- object storage
- scheduled task

공통 계약과 profile을 분리하면 새 언어를 추가할 때 platform API 전체를 복사하지 않아도 됩니다.

## 4. Template은 시작점일 뿐입니다

Repository template은 첫 commit을 만들 수 있지만 이후 변경을 자동으로 전달하지 못합니다.

Template가 만든 파일을 세 종류로 나눕니다.

| 종류 | 예 | 이후 소유자 |
|---|---|---|
| 중앙 참조 | reusable CI workflow, base image | platform team |
| 생성 후 서비스 소유 | domain code, README | application team |
| 관리되는 configuration | policy metadata, dependency bot config | 명시된 controller 또는 공동 소유 |

Platform team이 나중에 모든 파일을 일괄 덮어쓰면 서비스 팀의 변경과 충돌합니다. 반대로 모든 파일을 복사 후 방치하면 보안·upgrade가 파편화됩니다.

가능한 전달 방식:

- 중앙 reusable workflow와 version pin
- dependency update automation
- code modification campaign과 PR
- platform API conversion
- policy gate와 remediation guide
- profile version migration tool

## 5. Profile version

서비스는 어떤 platform profile로 생성됐는지 알아야 합니다.

```yaml
platform:
  profile: stateless-http
  version: 3.2.0
  createdFrom: service-template/1.8.1
  exceptions:
    - id: public-egress-legacy
      expiresAt: 2026-12-31
```

Version은 단순 template tag가 아닙니다. 다음 계약 묶음을 뜻합니다.

- build and release workflow
- runtime base
- resource default
- identity and secret delivery
- telemetry schema
- policy set
- support level
- upgrade path

Profile version별 차이를 machine-readable하게 제공하면 catalog에서 오래된 경로를 찾고 migration wave를 계획할 수 있습니다.

## 6. Default와 선택권

좋은 default는 많은 사용 사례에 안전하고 비용이 합리적이며, 왜 선택됐는지 설명할 수 있어야 합니다.

예:

```text
resource request를 비워 두지 않음
기본 network egress를 제한
short-lived identity 사용
외부 endpoint는 명시적 capability
structured log와 request correlation 기본 제공
production에는 최소 replica와 disruption budget 요구
```

Default를 바꿀 때는 기존 resource에 자동 적용되는지, 새 생성에만 적용되는지 분리합니다. “기본값 변경”이 기존 서비스의 runtime state를 바꾸면 migration입니다.

## 7. Escape hatch

지원 범위 밖 요구는 존재합니다. Escape hatch를 금지하면 사용자는 숨겨진 우회로를 만듭니다.

예외 계약:

- 왜 기본 경로로 해결할 수 없는가?
- 어떤 risk와 운영 책임을 application team이 인수하는가?
- platform team은 어디까지 지원하는가?
- policy exception이 필요한가?
- 종료 또는 재검토 날짜는 언제인가?
- standard path로 복귀하는 조건은 무엇인가?

예외 수준 예:

| 수준 | 의미 |
|---|---|
| supported extension | 문서화된 plugin 또는 custom option, 정상 지원 |
| reviewed exception | 제한된 기간·범위, 공동 지원 |
| bring your own | platform은 identity·network 같은 최소 경계만 제공 |
| unsupported | 플랫폼 SLO와 지원 범위 밖, 별도 승인 필요 |

Escape hatch는 catalog에 보이게 하고 소유자·만료·risk를 기록합니다.

## 8. 서비스 생성만큼 폐기가 중요합니다

Self-service 플랫폼은 생성 속도만 높이면 orphan resource도 빠르게 늘립니다.

Retire 단계:

```text
traffic과 consumer 확인
→ 새 변경 차단
→ data retention·export 결정
→ credential·DNS·route 폐기
→ workload·infrastructure 제거
→ backup·audit 보존
→ catalog lifecycle 갱신
→ 비용과 orphan 검사
```

삭제 전에 dependency를 자동으로 찾더라도 모든 의미 관계를 증명할 수는 없습니다. Production 서비스, 공유 data와 외부 consumer는 사람 확인이 필요할 수 있습니다.

## 9. 문서와 발견 가능성

Golden path는 사용자가 찾을 수 있어야 합니다.

필요한 자료:

- 어떤 문제에 어떤 profile을 선택하는가
- 첫 성공까지의 최소 단계
- platform API schema와 예제
- 실패 code와 복구 행동
- support hours와 escalation
- known limitation
- profile version과 upgrade guide
- escape hatch 절차
- retire 절차

문서는 portal에만 두지 않고 repository와 versioned source로 관리합니다. Portal은 검색과 context를 개선하는 소비자입니다.

## 10. Adoption과 성공 측정

채택률만 보면 강제를 성공으로 오해할 수 있습니다.

함께 볼 지표:

- first successful deployment까지 걸린 시간
- manual handoff와 ticket 수
- standard path의 배포 성공률
- platform-related incident와 복구 시간
- profile upgrade 완료율과 오래된 version 수
- escape hatch 수·사유·만료 초과
- 개발자가 해결 가능한 오류 비율
- platform team의 반복 support load
- 팀이 실제로 얻은 lead time 또는 안정성 개선

숫자는 profile, team maturity와 workload risk를 구분해 해석합니다.

## 11. Anti-pattern

### Golden path가 거대한 repository template입니다

생성 후 drift와 upgrade를 관리할 수 없습니다.

### 모든 기술 선택을 platform team이 결정합니다

업무 요구보다 중앙 편의가 우선되고, 지원되지 않는 요구가 숨겨집니다.

### 예외는 영구적입니다

Owner와 만료가 없어서 표준과 예외의 경계가 사라집니다.

### Platform team이 application code를 소유합니다

경계가 흐려져 서비스 팀의 자율성과 장애 책임이 약해집니다.

### 생성은 자동이지만 폐기는 수동입니다

Orphan, credential와 비용이 누적됩니다.

## 12. 실습

[`06-self-service`](../exercises/06-self-service/)에서 다음을 service lifecycle로 연결합니다.

- 서비스 request와 profile 선택
- 생성 condition
- build·deploy·operate 단계
- profile version과 update 경로
- escape hatch와 support level
- retire와 data retention
- catalog에 기록할 evidence

## 13. 검토 질문

- Golden path가 사용자의 반복 문제를 실제로 줄입니까?
- Template 이후 upgrade를 어떻게 전달합니까?
- Profile과 add-on의 책임이 분리돼 있습니까?
- Default 변경이 기존 workload에 미치는 영향을 구분합니까?
- 예외의 owner·risk·expiry·지원 수준이 보입니까?
- 서비스 폐기 뒤 credential·data·DNS·비용을 확인합니까?
- 채택률 외에 사용자 결과와 support load를 측정합니까?

다음 장에서는 golden path의 build와 배포를 **변경 불가능한 artifact와 환경 승격 계약**으로 만듭니다.
