# 플랫폼 소유권 매트릭스

아래 표는 시작 template입니다. 실제 조직에서는 capability별로 한 명 또는 한 팀의 단일 책임자를 지정하고, 공동 책임이라는 표현으로 실패 owner를 감추지 않습니다.

| 경계 | Application team | Platform team | Security/Policy | Runtime operator | External provider |
|---|---|---|---|---|---|
| 서비스 업무 코드 | A/R | C | C | I | - |
| Repository·owner metadata | A/R | C | I | I | - |
| Platform API schema | C | A/R | C | C | - |
| Runtime profile | C | A/R | C | C | - |
| Build workflow | C | A/R | C | I | C |
| Artifact 내용 | A/R | C | C | I | - |
| Registry/platform availability | I | A/R | C | C | C |
| Deployment request | A/R | C | I | I | - |
| Promotion policy | C | R | A | C | - |
| Workload readiness | A/R | C | I | C | - |
| Cluster scheduling/capacity | I | C | I | A/R | C |
| Identity issuer | I | R | A | C | C |
| Secret 원본 | A 또는 전문 owner | C | A/C | I | C |
| Network policy default | C | R | A | C | - |
| Tenant quota | C | A/R | C | C | C |
| Platform SLO | C | A/R | C | C | C |
| Application SLO | A/R | C | I | I | C |
| Incident command | 영향에 따라 명시 | 영향에 따라 명시 | 영향에 따라 명시 | 영향에 따라 명시 | C |
| Service retirement | A/R | C | C | C | C |

표기:

- `A`: 최종 책임(Accountable)
- `R`: 실행 책임(Responsible)
- `C`: 협의(Consulted)
- `I`: 통지(Informed)

## 작성 규칙

- 한 행의 `A`는 가능하면 하나로 둡니다.
- `R`이 여러 팀이면 handoff와 완료 condition을 적습니다.
- 정상 운영과 사고 대응의 owner가 다르면 별도 행으로 나눕니다.
- 실제 정본과 변경 권한을 owner 표와 일치시킵니다.
- 외부 provider가 책임져도 사용자 communication과 fallback owner는 내부에 둡니다.
