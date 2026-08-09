# event and idempotency contract

## Scope

upload event에서 result object, document status와 usage까지 하나의 logical operation으로 추적한다.

## Stage 1 — IaaS

worker service가 queue message를 lease하고 event ID별 processing record를 저장한다. crash 뒤 message가 재전달돼도 effect를 재사용한다.

## Stage 2 — Managed platform

queue delivery, visibility/acknowledgment, retention과 DLQ를 공식 contract로 확인한다. client timeout·retry를 별도 설정한다.

## Stage 3 — FaaS

deterministic output key, event ID deduplication, maximum attempt·age, partial batch와 tenant concurrency를 정의한다. function return과 business completion을 구분한다.

## Stage 4 — SaaS

usage event와 quota reservation도 같은 operation ID에 연결한다. deleted tenant와 unsupported plan/schema는 terminal로 분류한다.

## Evidence와 한계

unique event, attempts, duplicate suppressed, output, usage, DLQ와 replay audit를 trace한다. provider delivery ID의 안정성은 공식 문서에서 확인한다.

## Open risks와 owner

외부 converter가 idempotency key를 지원하지 않을 때 reconciliation strategy를 application owner가 설계한다.
