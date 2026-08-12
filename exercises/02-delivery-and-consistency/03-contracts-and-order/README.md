# 이벤트 계약과 aggregate 순서

## 목표

채널 이름, schema version과 aggregate별 sequence를 하나의 소비 계약으로 다룹니다.

## 구현할 계약

- 예상하지 않은 channel은 명시적인 계약 위반입니다.
- 설정한 지원 schema version과 들어온 event의 schema version은 모두 양수여야 합니다.
- 지원하지 않는 schema version은 적용하지 않고 격리합니다.
- 같은 event ID는 중복으로 무시합니다.
- 다음 sequence보다 큰 이벤트는 buffer에 보관합니다.
- gap이 채워지면 보류 이벤트를 연속으로 적용합니다.
- 서로 다른 aggregate는 독립적인 순서를 가집니다.

## 실패 조건

`skeleton`은 도착 순서대로 상태를 덮어쓰며 channel과 version을 검사하지 않습니다. 상태 변경 이벤트가 생성보다 먼저 오면 존재하지 않던 aggregate의 최종 상태가 먼저 만들어집니다.

## 작업

`Projection.onEvent`에 계약·중복·sequence 검사를 추가하고, aggregate별 buffer를 사용해 gap을 처리합니다.

## 권장 구현 순서

아래 번호는 실제 과거 작성 순서가 아니라, 이 reference 전체를 이해하기 위한 권장 학습용 구성 순서입니다.

| 번호 | 구현 대상 | 책임과 연결 |
|---|---|---|
| Implementation 1 | `Outcome`, `Event` | 소비 계약의 입력과 처리 결과 어휘를 먼저 고정합니다. |
| Implementation 2 | `Projection` | 적용 상태와 다음 sequence, 보류·격리 근거의 소유자를 정합니다. |
| Implementation 2-1 | `Projection.onEvent` 계약 gate | channel, identity, schema version을 상태 변경 전에 검사합니다. |
| Implementation 2-2 | sequence claim과 buffer | aggregate별 gap, stale, 충돌을 구분하고 근거를 보존합니다. |
| Implementation 2-3 | `Projection.apply` | 상태 적용과 다음 sequence 전진을 하나의 효과로 묶습니다. |
| Implementation 2-4 | `Projection.drain` | gap이 닫힌 aggregate의 보류 이벤트만 연속 적용합니다. |

## 완료 기준

- 예상 밖 channel과 지원하지 않는 schema version이 적용 전에 거절·격리됩니다.
- 설정 version과 event version이 0 이하라면 적용·격리 전에 계약 오류로 거절됩니다.
- aggregate별 gap은 buffer에 남고 앞 sequence 도착 뒤 연속 적용됩니다.
- 같은 sequence의 다른 event ID와 같은 ID의 다른 payload가 계약 충돌로 드러납니다.

## 자기 설명

- aggregate 순서와 시스템 전체 전역 순서를 구분해야 하는 이유는 무엇입니까?
- buffer가 sequence 하나당 이벤트 하나만 허용해야 하는 이유는 무엇입니까?

## 검증

처음 한 번 안전한 학습자 workspace를 만듭니다. 이미 같은 경로가 있으면 덮어쓰지 않고 실패합니다.

```sh
./scripts/new-workspace.sh contracts-and-order
```

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/contracts-and-order
```

workspace 검증을 통과하고 위 자기 설명에 답한 뒤에만 reference와 비교합니다.

```sh
./scripts/verify-java.sh \
  exercises/02-delivery-and-consistency/03-contracts-and-order/reference
```

전역 순서를 만들지 말고 같은 aggregate 안의 sequence만 직렬화합니다.
