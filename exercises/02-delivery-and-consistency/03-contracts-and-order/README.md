# 이벤트 계약과 aggregate 순서

## 목표

채널 이름, schema version과 aggregate별 sequence를 하나의 소비 계약으로 다룹니다.

## 구현할 계약

- 예상하지 않은 channel은 명시적인 계약 위반입니다.
- 지원하지 않는 schema version은 적용하지 않고 격리합니다.
- 같은 event ID는 중복으로 무시합니다.
- 다음 sequence보다 큰 이벤트는 buffer에 보관합니다.
- gap이 채워지면 보류 이벤트를 연속으로 적용합니다.
- 서로 다른 aggregate는 독립적인 순서를 가집니다.

## 실패 조건

`skeleton`은 도착 순서대로 상태를 덮어쓰며 channel과 version을 검사하지 않습니다. 상태 변경 이벤트가 생성보다 먼저 오면 존재하지 않던 aggregate의 최종 상태가 먼저 만들어집니다.

## 작업

`Projection.onEvent`에 계약·중복·sequence 검사를 추가하고, aggregate별 buffer를 사용해 gap을 처리합니다.

## 검증

```sh
./scripts/verify-java.sh \
  exercises/02-delivery-and-consistency/03-contracts-and-order/reference
```

전역 순서를 만들지 말고 같은 aggregate 안의 sequence만 직렬화합니다.
