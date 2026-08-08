# 동기·비동기 요청 판정

## 목표

즉시 판정이 필요한 요청과 나중에 처리할 수 있는 요청의 계약을 구분하고, 정책 판정이 실패한 경로에서 상태가 바뀌지 않는지 확인합니다.

## 구현할 계약

- 동기 요청은 정책 결과를 받은 뒤에만 수량을 변경합니다.
- 정책이 거절되거나 응답하지 않으면 `REJECTED`이며 수량 변화는 0입니다.
- 비동기 수락은 `PENDING`과 작업 소유권만 약속합니다.
- 비동기 요청은 실제 처리 단계에서 정책을 확인한 뒤 결과를 확정합니다.
- 같은 operation ID는 이전 결과를 반환합니다.

## 실패 조건

`skeleton`은 정책 서비스를 호출하기 전에 수량을 먼저 예약합니다. 응답이 거절 또는 장애여도 부정 불변 조건이 깨집니다.

## 작업

`Coordinator.decideNow`에서 상태 변경의 순서를 고칩니다. 원격 정책 결과가 `ALLOW`일 때만 `CapacityLedger.reserve`를 호출합니다.

## 검증

```sh
./scripts/verify-java.sh \
  exercises/01-boundaries-and-failure/03-request-decision/reference
```

정상 응답만 보지 말고 `REJECTED`와 `UNAVAILABLE`에서 `reserved == 0`인지 확인합니다.
