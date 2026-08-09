# 04. FaaS event lifecycle

## 목적

upload event를 처리하는 function의 중복, timeout, batch failure, concurrency, dead-letter와 replay 상태를 설계합니다.

## 입력

[`inputs/event-scenarios.md`](inputs/event-scenarios.md)를 사용합니다.

## 결과물

`event-processing-plan.md`에 event identity, state, retry classification, idempotency, output, quota, observability와 cost를 작성합니다.

## 사람 검토 질문

1. handler success와 business effect commit을 구분했습니까?
2. 같은 event가 다시 와도 output과 usage가 하나입니까?
3. timeout 뒤 external effect가 unknown일 때 판정 경로가 있습니까?
4. poison event가 무한 retry와 비용 폭주를 만들지 않습니까?
5. replay가 현재 tenant·schema·function version을 확인합니까?
