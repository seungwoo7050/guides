# FaaS Event Processing Plan

## Event identity와 schema

TODO

## 상태 기계와 완료 지점

`SOURCE_AVAILABLE → INVOCATION_RUNNING → EFFECT_COMMITTED → ACK_COMMITTED`에서 source ack/checkpoint와 timeout 분기를 작성합니다.

TODO

## Idempotency와 external effect

TODO

## Retry classification과 deadline

TODO

## Batch failure와 ordering

TODO

## Concurrency, tenant fairness와 quota

TODO

## Dead-letter와 replay

TODO

## Observability와 evidence

TODO

## Cost guard

TODO

## Failure scenario 판정

`F04-01`부터 `F04-08`까지 같은 ID를 유지해 source position, attempt, function version, external effect, ack/checkpoint, retry·replay, 비용과 evidence를 판정합니다.

TODO
