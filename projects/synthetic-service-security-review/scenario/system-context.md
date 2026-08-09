# LedgerLab 시스템 Context

## 사용자 기능

인증된 사용자는 자신의 transaction을 조회하고 특정 기간의 report 생성을 요청할 수 있습니다. report 생성이 끝나면 짧은 수명의 download URL을 받습니다.

보호할 핵심 상태의 초안은 다음과 같습니다.

- 사용자는 자신에게 허가된 account와 report만 읽습니다.
- report worker는 현재 job에 필요한 transaction과 object만 읽고 씁니다.
- release는 검증된 source·dependency·artifact에서 재현 가능한 identity로 배포됩니다.
- 민감한 read·write·policy decision은 actor와 resource까지 재구성할 수 있습니다.
- incident 뒤 trusted source에서 identity·artifact·data 상태를 복구할 수 있습니다.

이 문장은 학습자의 최종 보안 requirement가 아닙니다. 제공 자료를 검토해 보완해야 합니다.

## 구성요소와 흐름

```text
browser
  │ user session
  ▼
public gateway
  │ internal request identity + delegated user
  ▼
account API ───────→ account database
  │                      transaction data
  ├─ report job ───→ report queue
  └─ download ─────→ object signer

report queue
  │ job id
  ▼
report worker
  ├─ transaction read ─→ account API
  └─ object read/write ─→ object proxy ─→ object storage provider

source repository
  → CI runner ─→ internal package proxy (build-time dependency resolution)
  → artifact registry
  → deployer
  → runtime

component event
  → audit collector
  → event store
```

## Environment

- 이름: `staging-synthetic`
- 사용자·transaction·object: 모두 `synthetic/*` prefix
- production과 별도 database·bucket을 사용한다고 설계 문서에 적혀 있음
- registry organization과 package proxy control plane은 production과 공유
- runtime subnet은 private로 표시됨
- 실제 egress rule export는 제공되지 않음
- 배포 manifest는 기준 시각보다 약 13시간 41분 전(`2026-08-08T10:18:55Z`)에 생성됨
- identity policy는 2일 전 snapshot
- event fixture는 2026-08-08 incident window에서 추출한 합성 자료

## 팀과 소유권

| 영역 | Owner | 변경 경로 |
|---|---|---|
| gateway·account API | application team | repository + CI |
| report worker | reporting team | repository + CI |
| workload identity | platform identity team | policy repository |
| package proxy | developer platform team | admin API + policy repository |
| artifact registry·deployer | release engineering | CI + deploy approval |
| object proxy·storage | data platform team | service config + provider policy |
| audit collector·event store | security operations | event schema repository |

## 현재 주장

1. download route는 report owner를 항상 확인합니다.
2. worker credential은 한 job의 tenant prefix에만 제한됩니다.
3. package proxy는 동일한 package version이 다른 content를 반환하지 않습니다.
4. runtime은 release manifest의 immutable digest를 실행합니다.
5. 모든 sensitive object access는 user와 service identity를 함께 기록합니다.
6. supply-chain incident에서도 trusted artifact로 복구할 수 있습니다.

각 주장은 제공 evidence로 별도 판정해야 합니다.
