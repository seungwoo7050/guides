# 멀티테넌트 문서 처리 SaaS Capstone

## 목적

하나의 문서 처리 workload를 IaaS, managed platform, FaaS와 SaaS로 단계적으로 확장하며 책임·실패·비용·tenant·exit 계약을 누적합니다.

완성 application code는 필수가 아닙니다. architecture dossier와 local model evidence를 통해 실제 프로젝트를 시작할 수 있는 설계 상태를 만드는 것이 목표입니다.

## 입력

- [`inputs/system-brief.md`](inputs/system-brief.md)
- 이전 단계 실습의 산출물
- [`rubric.md`](rubric.md)

## Workspace

```sh
scripts/new_workspace.sh projects/multitenant-document-processing-saas
scripts/check_workspace.sh projects/multitenant-document-processing-saas
```

## 결과물

```text
01-responsibility-matrix.md
02-resource-and-state-inventory.md
03-identity-network-and-tenant-boundaries.md
04-failure-and-recovery-plan.md
05-event-and-idempotency-contract.md
06-cost-quota-and-metering.md
07-portability-exit-and-deletion.md
08-release-review.md
```

## 작업 단계

1. IaaS 기준선을 작성합니다.
2. managed platform 전환으로 이동한 책임과 새 limit를 갱신합니다.
3. worker를 FaaS event model로 바꿉니다.
4. tenant·membership·plan·quota·usage·export·deletion을 추가합니다.
5. 각 stage의 cost·evidence·exit를 비교합니다.
6. `APPROVE`, `APPROVE_WITH_CONDITIONS`, `DEFER`, `REJECT` 중 하나를 결정합니다.

## 선택 확장

실제 provider 하나를 선택해 profile을 적용할 수 있습니다. 실제 resource를 만들기 전에 별도 계정, 예산, 최소 권한, prefix, TTL, inventory와 destroy plan을 준비합니다.
