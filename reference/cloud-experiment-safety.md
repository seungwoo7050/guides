# 실제 Cloud 실험 안전 계약

실제 계정 실험은 선택 사항입니다. 무료 등급을 신뢰하거나 개인 주 계정에서 즉흥적으로 실행하지 않습니다.

## 시작 전 필수

```text
실험 목적
성공·중단 조건
별도 account/subscription/project
허용 region
human/workload identity
maximum budget
budget alert
resource prefix와 owner tag
expires_at 또는 TTL
created resource inventory
destroy 순서
final inventory와 billing 확인
```

## 권한

- 개인 root/owner credential을 일상 CLI에 사용하지 않습니다.
- 학습 identity는 실험 resource scope만 허용합니다.
- production account와 연결하지 않습니다.
- access key를 repository·shell history·screenshot에 남기지 않습니다.
- function/VM role에 broad administrator 권한을 주지 않습니다.

## 비용

- provider calculator에서 estimate를 기록합니다.
- NAT, load balancer, public address, log, snapshot, egress처럼 idle/hidden cost를 확인합니다.
- maximum concurrency와 autoscaling limit를 설정합니다.
- experiment 종료 시각과 알람을 둡니다.
- bill data가 지연될 수 있음을 기록합니다.

## 데이터

- 실제 고객·개인·회사 secret을 사용하지 않습니다.
- 합성 data와 canary tenant를 사용합니다.
- public bucket/container와 database를 만들지 않습니다.
- export artifact에는 expiry와 access 제한을 둡니다.

## 정리

```text
traffic/trigger disable
→ final evidence export
→ data resource 확인
→ compute/function/runtime 삭제
→ load balancer·network·address 삭제
→ volume·snapshot·object lifecycle 확인
→ identity·key·secret 정리
→ log/backup retention 기록
→ final inventory
→ 다음 billing 확인
```

## 사고

credential 노출, 예상 밖 resource, 비용 급증 또는 public exposure가 발생하면 실험을 중단합니다. credential revoke, trigger disable, evidence 보존과 resource isolation을 먼저 수행하고 무작정 전체 삭제해 원인을 지우지 않습니다.
