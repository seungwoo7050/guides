# IaaS Architecture Review

## Resource inventory와 owner

| Resource | 상태 | 위치 | runtime owner | data/cost owner | 재생성 |
|---|---|---|---|---|---|
| load balancer | routing config | regional 가정 | operations | product | config에서 가능 |
| app VM 2개 | ephemeral runtime | zone A | application | product | image+bootstrap 필요 |
| boot/local disk | cache·scratch | zone A | application | product | 손실 허용, 정본 금지 |
| database primary | authoritative | private, 단일 failure domain | data team | product | backup에서 restore |
| object storage | authoritative upload | regional contract 확인 | application | data owner | export·version 필요 |
| snapshot | recovery artifact | provider scope 확인 | operations | data owner | restore 검증 필요 |
| log | evidence | workload와 분리 필요 | operations/security | compliance | retention 필요 |

모든 resource에 owner, service, environment, data class, created_by, expires_at 또는 lifecycle과 cost center를 추가한다. 이름이 아니라 provider resource ID를 inventory 정본으로 사용한다.

## State classification

VM image와 declarative configuration은 reproducible state다. application process·local cache·temporary file은 ephemeral이다. database row와 upload object는 durable authoritative state다. thumbnail은 upload에서 다시 만들 수 있는 derived state다. audit·deployment·restore report는 evidence state이며 workload가 삭제할 수 없는 저장소로 보낸다.

현재 image가 한 달 전 수동 생성됐고 startup이 외부 package repository에 의존하므로 동일한 replacement를 보장하지 못한다. dependency를 build 시점에 고정하고 image ID·source·digest·readiness를 release manifest에 기록한다.

## Network와 identity boundary

public ingress는 load balancer의 HTTPS endpoint 하나로 제한한다. VM과 database는 public address를 갖지 않는다. load balancer→VM, VM workload identity→database/object/log의 목적별 access만 허용한다. 운영자 human identity와 VM workload identity를 분리한다. database admin credential을 VM image나 startup log에 넣지 않는다.

private라는 이름만 믿지 않고 route, firewall, public address, private endpoint와 DNS를 함께 검사한다. negative test로 외부 runner에서 database port와 object private prefix 접근이 거부되는지 확인한다.

## Failure domain과 capacity

현재 두 VM이 모두 zone A에 있으므로 zone failure에 독립적이지 않다. 평상시 120 request/s에서 VM 하나만 남으면 capacity 100 request/s로 즉시 overload가 된다. 두 zone에 2개씩 배치하거나, zone 하나가 사라졌을 때 최소 180 request/s peak를 감당할 reserved capacity와 빠른 scale-out을 증명해야 한다.

database가 단일 primary이면 application VM만 multi-zone으로 옮겨도 전체 availability는 database failure에 묶인다. managed multi-zone 또는 verified replica/failover를 선택하고 client reconnect와 transaction outcome을 실험한다.

## Backup, restore와 rebuild

snapshot enable은 restore evidence가 아니다. monthly restore drill이 아니라 초기에는 매 release 또는 주 1회 isolated environment restore를 수행한다. checksum, schema version, representative document count와 business invariants를 검사하고 RTO·RPO를 기록한다. object storage version/lifecycle와 encryption key dependency를 포함한다.

clean environment rebuild에는 network, identity, image, database restore, object access, secret version, DNS와 monitoring이 필요하다. 수동 console state를 제거하거나 inventory에 기록한다.

## Scaling, quota와 overload

request rate와 tail latency를 scale signal로 사용하되 maximum capacity와 startup latency를 기록한다. database connection과 package repository가 downstream bottleneck이므로 VM만 무한 확장하지 않는다. admission limit, bounded queue와 overload response를 둔다. quota increase lead time과 region capacity risk를 기록한다.

## Failure injection과 evidence

1. VM 하나 terminate: load balancer removal, replacement operation ID, image ID, readiness와 error rate를 기록한다.
2. zone A target 전체 제거: 남은 capacity, error/latency, alarm과 recovery time을 기록한다.
3. package repository deny: replacement가 외부 install 없이 시작되는지 확인한다.
4. database connection deny: fail-fast/degraded behavior와 retry storm 부재를 확인한다.
5. latest snapshot restore: restore duration과 business invariant를 기록한다.
6. public database rule 주입: policy 검사와 audit alert가 거부 또는 탐지하는지 확인한다.

## Cleanup 순서와 잔여 비용

traffic drain과 DNS 확인 뒤 final export/backup을 만들고 compute, load balancer, public address, unattached volume, snapshot policy, log sink와 identity attachment를 dependency에 맞게 정리한다. retention 대상 log와 backup은 비용 owner와 expiry를 남긴다. destroy command 성공 뒤 final inventory와 billing export 지연을 확인한다.

## Release decision

현재 상태는 `DEFER`다. 동일 zone 배치, 단일 database, 수동 image, restore evidence 부재와 owner 없는 resource가 핵심 공백이다. multi-zone capacity, data failover, immutable image, restore drill, network negative test와 cleanup evidence가 확보된 뒤 제한된 traffic으로 승인한다.
