# 분산 시스템 설계 검토표

## 1. System model

- [ ] participant와 client를 나열했습니다.
- [ ] network delay·loss·duplicate·reorder·partition 범위를 정했습니다.
- [ ] crash-stop과 crash-recovery를 구분했습니다.
- [ ] volatile·durable state를 나열했습니다.
- [ ] storage atomicity와 corruption 범위를 정했습니다.
- [ ] safety와 liveness의 시간 가정을 분리했습니다.

## 2. State와 ownership

- [ ] authoritative state와 replica·derived state를 구분했습니다.
- [ ] leader·owner·configuration에 epoch가 있습니다.
- [ ] stale actor를 storage·routing 경계에서 fencing합니다.
- [ ] state transition이 retry와 crash 뒤 재개 가능합니다.
- [ ] client request와 session identity가 있습니다.

## 3. Replication과 consistency

- [ ] commit rule과 acknowledgment 의미가 명확합니다.
- [ ] read consistency를 write protocol과 별도로 정했습니다.
- [ ] version의 순서·concurrency 의미가 명확합니다.
- [ ] quorum 교차의 membership 전제를 확인했습니다.
- [ ] timeout 뒤 partial replica state의 repair owner가 있습니다.
- [ ] tombstone과 GC evidence가 있습니다.

## 4. Consensus

- [ ] term·vote·log durable ordering이 명확합니다.
- [ ] candidate log freshness를 검사합니다.
- [ ] current-term commit rule을 적용합니다.
- [ ] commit·apply·response를 분리합니다.
- [ ] restart는 안전한 role과 state에서 시작합니다.
- [ ] client retry가 effect를 중복 생성하지 않습니다.

## 5. Snapshot과 membership

- [ ] snapshot state와 log boundary가 동등합니다.
- [ ] session·configuration metadata를 포함합니다.
- [ ] incomplete generation이 active가 되지 않습니다.
- [ ] old/new configuration quorum이 교차합니다.
- [ ] learner catch-up 뒤 voter 승격이 일어납니다.
- [ ] removed node의 write를 fencing합니다.

## 6. Sharding과 transaction

- [ ] key당 write authority가 한 epoch에 하나입니다.
- [ ] routing cache가 stale해도 owner가 epoch를 검사합니다.
- [ ] migration의 snapshot·delta·fence·cutover·cleanup 순서가 있습니다.
- [ ] prepared transaction과 coordinator decision이 durable합니다.
- [ ] atomicity와 isolation을 별도 검증합니다.
- [ ] cross-shard query의 partial result와 snapshot semantics가 있습니다.

## 7. 검증

- [ ] sequential specification이 있습니다.
- [ ] internal invariant와 client history property가 있습니다.
- [ ] every-step deterministic invariant check가 있습니다.
- [ ] explicit failure schedule과 seed를 저장합니다.
- [ ] history checker가 timeout·pending을 올바르게 다룹니다.
- [ ] model counterexample을 code regression으로 옮깁니다.
- [ ] actual fault 적용 evidence가 있습니다.
- [ ] 정상·장애·복구 성능을 분리해 측정합니다.

## 8. 운영·호환

- [ ] wire·log·snapshot format version이 있습니다.
- [ ] rolling upgrade와 feature activation 순서가 있습니다.
- [ ] rollback 가능 지점과 불가능 지점을 기록했습니다.
- [ ] corruption을 stale state와 구분합니다.
- [ ] source·config·topology identity가 artifact에 남습니다.
- [ ] 지원하지 않는 failure와 잔여 위험을 명시했습니다.
