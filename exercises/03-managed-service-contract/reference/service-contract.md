# Managed Service Contract

## Capability와 선택 이유

표준 web workload의 authoritative metadata는 managed relational database에 두고, async processing command는 queue, upload와 result는 object service에 둔다. 선택 이유는 host·engine 운영을 줄이면서 transaction, durable event buffer와 large object lifecycle 기능을 사용하기 위해서다. 관리형이라는 이유만으로 application correctness와 data lifecycle 책임이 사라지지는 않는다.

## 공급자 책임

공급자는 database host와 engine patch 실행, 선택한 multi-zone replica orchestration, backup artifact 생성 기능, queue storage와 delivery infrastructure, object durability와 service control plane을 관리한다. physical infrastructure와 내부 replacement는 공급자 영역이다. 세부 SLA·maintenance·deletion은 현재 공식 contract를 확인한다.

## 소비자 책임

소비자는 schema·query·transaction, connection pool, client timeout·retry, queue event identity와 idempotency, object key·tenant scope, backup retention 선택, restore drill, access policy, key, cost limit, version compatibility, monitoring, data export와 deletion evidence를 소유한다.

## Identity와 network

application runtime은 database connect, 지정 queue consume/publish, tenant-scoped object prefix read/write만 허용하는 workload identity를 사용한다. human admin과 deployment automation을 분리한다. database와 object management action은 runtime role에 주지 않는다. private endpoint를 선택할 때 DNS·route·egress dependency와 support access를 기록한다.

## Availability, consistency와 delivery

multi-zone database는 zone failure에 대한 외부 계약과 client reconnect를 확인한다. application transaction의 commit outcome과 replica read consistency는 별도 검증한다. queue는 at-least-once 가능성을 전제로 duplicate를 허용하고 partition key 내부 ordering만 요구한다. object overwrite·version·delete semantics는 공식 문서와 실험으로 확인한다.

## Limits, quota와 maintenance

connection 500은 service 전체인지 instance인지 확인하고 pool과 autoscaling maximum을 그보다 낮게 제한한다. storage 2 TB 도달 전에 growth alert와 migration trigger를 둔다. queue payload가 1 MB를 넘는 content는 object에 두고 reference만 전달한다. throughput quota와 increase lead time을 기록한다. major version 종료 12개월 전 driver·extension·query compatibility rehearsal을 시작한다.

## Backup, restore와 observability

14일 point-in-time 기능이 있어도 월 1회 isolated restore를 수행하고 schema, row count, sample checksum와 business invariant를 검사한다. object version과 queue in-flight state는 database backup에 포함되지 않으므로 별도 복구 계약을 둔다. provider health, resource metric, client error, business outcome, usage와 cost를 연결한다.

## Cost model

minimum database capacity, replica, backup storage, queue request, object byte-month·request·retrieval·egress, private network gateway와 log ingestion을 estimate에 포함한다. `cost per 1000 processed documents`를 unit으로 두고 retry·dead-letter·restore test 비용을 별도 기록한다.

## Portability, export와 deletion

관계 schema·data full export, object inventory와 bulk copy, queue freeze 또는 drain, identity·configuration·key mapping을 exit plan에 포함한다. database 2 TB와 object volume에서 실제 export throughput·egress cost를 작은 rehearsal로 측정한다. source deletion 뒤 provider backup retention과 key lifecycle을 확인한다.

## Unknown과 확인 계획

- database failover RTO와 in-flight transaction 결과
- queue duplicate ID와 redelivery delay
- object deletion completion와 inventory freshness
- support operator access
- cross-region backup copy와 key requirement
- quota increase lead time

각 항목은 공식 문서 URL, 확인 날짜, region, 실험 결과 또는 provider support response로 닫는다.

## Decision

`APPROVE_WITH_CONDITIONS`다. private access, workload identity, duplicate-safe consumer, restore drill, version lifecycle owner, cost budget와 exit rehearsal이 먼저 필요하다. unknown이 닫히지 않으면 production data를 넣지 않는다.
