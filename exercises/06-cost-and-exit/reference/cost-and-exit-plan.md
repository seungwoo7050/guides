# Cost and Exit Plan

## Workload unit와 cost driver

핵심 unit은 `cost per 1000 successful documents`, `cost per active tenant`, `storage cost per retained GB`다. VM·database minimum은 baseline cost, function request/duration과 object operation은 variable cost, replica·capacity tier 추가는 step cost다. retry 8%는 useful outcome 없이 function·log·downstream cost를 증가시키므로 별도 추적한다.

## Fixed, variable와 step cost

VM 4개와 database minimum+standby, load balancer는 idle cost다. function invocation·duration, object request·storage·download, zone transfer와 log ingest는 variable cost다. database capacity tier, new replica와 archive retrieval은 step cost가 될 수 있다. price는 현재 provider calculator와 billing export에서 확인하고 checked_at을 기록한다.

## Allocation과 tenant attribution

resource에 owner, service, environment, tenant/dedicated 여부와 cost center tag를 강제한다. shared VM·database는 document processing time과 storage driver로 배분한다. object byte와 egress를 tenant별로 meter하고 raw usage event ID를 보존한다. support·security·shared network cost는 versioned allocation rule로 배분한다.

## Budget, quota와 anomaly response

budget 기준의 monthly forecast, 50/75/90/100% alert와 daily anomaly를 둔다. alert는 hard limit가 아니므로 test environment는 policy로 instance type·region·resource count를 제한하고 expires_at 없는 resource 생성을 거부한다. function에는 maximum concurrency·attempt·event age를 둔다. anomaly 발생 시 retry source disable, logging sample 조정, compromised credential revoke와 owner 호출 절차를 둔다.

## Rightsizing과 resilience trade-off

평균 CPU 15%만 보고 VM을 1개로 줄이지 않는다. zone failure 때 3개 필요하므로 두 zone에 최소 capacity를 배치하고 autoscaling latency를 측정한다. steady workload가 높으면 smaller always-on pool과 burst capacity를 비교한다. log 90일 hot은 incident·compliance 요구를 확인하고 older data를 lower-cost tier로 이동하되 retrieval test를 수행한다.

## Cleanup plan

unattached volume 12개, snapshot 80개, test load balancer 7개를 owner·last access·dependency로 분류한다. 삭제 전 backup·legal retention을 확인하고 승인 목록을 만든다. 모든 ephemeral resource에 prefix와 expires_at을 요구한다. cleanup command 뒤 final inventory와 다음 billing period의 잔여 line item을 확인한다. evidence log는 별도 retention으로 보존한다.

## Commitment decision

1년 commitment는 zone failure baseline과 확실한 steady capacity에만 적용한다. migration 가능성, growth·shrink range, instance family flexibility와 unused risk를 계산한다. function·storage처럼 variable workload를 commitment에 억지로 포함하지 않는다. exit trigger와 commitment 종료 날짜를 lock-in register에 남긴다.

## Data export와 migration

10 TB object는 inventory, version, checksum와 incremental copy가 필요하다. 월 5% 변경률을 반영해 initial bulk copy와 delta sync를 계획한다. database는 representative 100 GB export로 throughput을 측정해 전체 duration·downtime·egress를 estimate한다. identity, schema, metadata, retention, queue drain, function trigger와 DNS cutover를 포함한다.

## Source deletion과 evidence

cutover와 validation 뒤 source write를 차단하고 final delta를 적용한다. active resource, object version, snapshot, backup, log, key, token, DNS와 certificate를 inventory로 확인한다. provider backup retention과 physical deletion은 contract에 의존하는 범위를 기록한다. final invoice와 commitment를 확인한다.

## Decision과 review trigger

현재는 `APPROVE_WITH_CONDITIONS`다. orphan cleanup, tenant storage·egress metering, log retention 조정, export throughput 측정과 commitment scope 확정이 필요하다. monthly cost가 forecast의 120%를 넘거나 storage growth가 8%를 넘거나 migration trigger가 발생하면 재검토한다.
