# Responsibility matrix 빠른 참조

아래 표는 출발점일 뿐입니다. 실제 service contract를 작업별로 확인합니다.

| 작업 | IaaS 소비자 | PaaS 소비자 | FaaS 소비자 | SaaS 고객 | 공급자 측 주요 역할 |
|---|---|---|---|---|---|
| physical facility | 없음 | 없음 | 없음 | 없음 | 공급자 |
| host/hypervisor | 제한적 관찰 | 없음 | 없음 | 없음 | 공급자 |
| OS patch | 주 책임 | 대부분 공급자 | 공급자 runtime | SaaS 공급자 | 모델에 따라 |
| runtime version | 소비자 | 공동 | 지원 runtime 선택 | 없음 | 공동/공급자 |
| application code | 소비자 | 소비자 | 소비자 | SaaS 공급자 | 모델에 따라 |
| application authorization | 소비자 | 소비자 | 소비자 | 고객 설정+SaaS 공급자 | 공동 |
| data meaning·retention | 소비자 | 소비자 | 소비자 | 고객+SaaS 계약 | 소비자 중심 |
| network exposure | 소비자 | 공동 | 공동 | 고객 설정 일부 | 공동 |
| workload identity | 소비자 | 소비자 | 소비자 | 해당 없음 | 기능 제공 |
| scaling policy | 소비자 | 공동 | limit·event 설계 | SaaS 공급자 | 기능 제공 |
| backup 생성 | 소비자/기능 | 기능 제공 가능 | 외부 state별 | SaaS 공급자 | 모델에 따라 |
| restore 검증 | 소비자 | 소비자 | 소비자 | SaaS 계약 확인 | 공동 |
| observability | 소비자 | provider metric+소비자 | invocation+소비자 | SaaS 기능 | 공동 |
| cost·budget | 소비자 | 소비자 | 소비자 | subscription owner | 사용량 제공 |
| export·exit | 소비자 | 소비자 | 소비자 | 고객+SaaS 공급자 | 기능/계약 제공 |

## 작성 규칙

- component가 아니라 task를 적습니다.
- `공동`이면 누가 실행하고 누가 검증하는지 분리합니다.
- `managed`를 책임 없음으로 바꾸지 않습니다.
- evidence와 escalation path를 함께 적습니다.
