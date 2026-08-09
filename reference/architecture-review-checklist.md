# Cloud architecture review 점검표

## Scope

- [ ] workload, 사용자와 tenant가 정의돼 있습니다.
- [ ] production·region·data classification이 명시돼 있습니다.
- [ ] external dependency와 provider service가 목록화돼 있습니다.

## State

- [ ] durable authoritative state가 있습니다.
- [ ] derived·ephemeral·evidence state를 구분합니다.
- [ ] commercial state(plan·quota·usage)가 분리됩니다.
- [ ] create·update·delete의 중간 상태가 있습니다.

## Responsibility

- [ ] provider·consumer 작업이 task 단위로 기록됩니다.
- [ ] business·runtime·data·cost owner가 있습니다.
- [ ] managed service가 숨기는 상태와 limit를 기록합니다.

## Identity와 network

- [ ] human·workload·automation identity가 분리됩니다.
- [ ] control plane과 data plane permission을 구분합니다.
- [ ] public/private/egress path가 evidence로 확인됩니다.
- [ ] tenant context가 모든 application path에 전달됩니다.

## Failure와 recovery

- [ ] instance·zone·region·control plane failure를 구분합니다.
- [ ] duplicate·timeout·partial success를 다룹니다.
- [ ] quota와 cost anomaly가 있습니다.
- [ ] backup과 restore evidence가 있습니다.
- [ ] RTO·RPO와 capacity headroom을 측정합니다.

## SaaS

- [ ] membership, role, entitlement와 quota가 분리됩니다.
- [ ] cache·queue·analytics·support·export를 격리합니다.
- [ ] metering event가 idempotent합니다.
- [ ] tenant deletion이 subsystem 전체에 전파됩니다.

## Cost

- [ ] idle·variable·step cost가 있습니다.
- [ ] unit economics가 정의돼 있습니다.
- [ ] owner·tag·expiry와 cleanup이 있습니다.
- [ ] budget alert와 hard control을 구분합니다.

## Exit

- [ ] data·schema·identity·configuration·key를 회수합니다.
- [ ] migration throughput·duration·egress를 rehearsal합니다.
- [ ] source retention·deletion과 final inventory가 있습니다.

## Decision

- [ ] evidence의 한계를 기록합니다.
- [ ] residual risk와 owner가 있습니다.
- [ ] review trigger와 reversal plan이 있습니다.
