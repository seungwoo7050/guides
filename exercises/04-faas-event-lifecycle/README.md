# 04. FaaS event lifecycle

## 목적

upload event를 처리하는 function의 source ack/checkpoint, invocation timeout, partial batch, concurrency·throttle, failure destination과 replay 상태를 설계합니다. 일반적인 retry·idempotency 구현은 [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)가 소유하며, 이 실습은 그 계약을 FaaS event source 제약에 적용합니다.

## 입력

[`inputs/event-scenarios.md`](inputs/event-scenarios.md)를 사용합니다.

## 결과물

`event-processing-plan.md`에 `SOURCE_AVAILABLE → INVOCATION_RUNNING → EFFECT_COMMITTED → ACK_COMMITTED` 상태, event identity, source별 retry owner, idempotency, partial batch, quota, observability와 retry cost를 작성합니다. 입력의 `F04-01`~`F04-08`을 같은 ID로 판정합니다.

## 사람 검토 질문

1. handler success와 business effect commit을 구분했습니까?
2. 같은 event가 다시 와도 output과 usage가 하나입니까?
3. timeout 뒤 external effect가 unknown일 때 판정 경로가 있습니까?
4. poison event가 무한 retry와 비용 폭주를 만들지 않습니까?
5. replay가 현재 tenant·schema·function version을 확인합니까?
6. source의 ack 또는 checkpoint가 언제 이동하고, partial batch의 성공 record는 무엇으로 증명합니까?
7. throttle과 retry가 한 tenant의 비용·공유 concurrency 독점으로 이어지지 않습니까?
