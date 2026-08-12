# 중복 전달과 단일 효과

## 목표

업무 상태를 변경한 뒤 ACK 전에 처리기가 중단되어 같은 이벤트가 다시 전달되는 상황을 재현합니다.

## 구현할 계약

- 같은 `event_id`는 여러 번 전달되어도 업무 효과가 한 번만 적용됩니다.
- 중복 기록과 상태 변경은 하나의 원자적 경계에 있습니다.
- 재전달은 이전 결과를 반환합니다.
- 서로 다른 event ID는 독립적으로 적용됩니다.

## 실패 조건

`skeleton`은 잔액을 먼저 변경하고 나중에 `event_id` 중복을 확인합니다. 첫 전달이 commit 뒤 중단되면 재전달에서 잔액이 다시 증가합니다.

## 작업

`EffectStore.applyOnce`의 순서를 고칩니다. 중복이면 상태를 바꾸지 않고 이전 결과를 반환하고, 새 이벤트일 때만 상태 변경과 처리 기록을 함께 남깁니다.

## 권장 구현 순서

범위는 이 실습의 `reference` 프로젝트 전체이며 아래 번호를 모든 구현 파일에서
공유합니다. 이 번호는 학습을 위한 권장 구성 순서이고 실제 Git 이력이나 과거 작성
순서를 뜻하지 않습니다.

| 순서 | 구현 위치 | 책임과 연결 |
| --- | --- | --- |
| Implementation 1 | `Event` | 이벤트 식별자와 payload를 함께 묶어 충돌 판정 근거를 만듭니다. |
| Implementation 2 | `EffectStore` | 잔액, 처리 결과, 입력 지문을 하나의 상태 소유 경계에 둡니다. |
| Implementation 2-1 | `EffectStore.applyOnce` | 중복은 이전 결과로 수렴시키고 신규 이벤트만 한 번 적용합니다. |
| Implementation 3 | `Handler` | 저장 commit과 ACK 사이의 전달 lifecycle을 연결합니다. |
| Implementation 3-1 | `Handler.handle` | commit 뒤 중단을 재현해 재전달에서도 단일 효과가 유지되게 합니다. |

## 완료 기준

- 같은 event ID를 반복 전달해도 잔액과 처리 기록은 한 번만 증가합니다.
- 첫 commit 뒤 ACK가 사라진 경로도 이전 결과로 수렴합니다.
- 서로 다른 이벤트는 독립 적용되고 같은 ID의 다른 payload는 충돌로 거절됩니다.

## 자기 설명

- 중복 기록과 업무 상태 변경이 같은 원자적 경계에 있어야 하는 이유는 무엇입니까?
- event ID만 같고 payload가 다를 때 조용히 중복 처리하면 왜 위험합니까?

## 검증

처음 한 번 저장소 루트에서 추적된 skeleton을 안전한 workspace로 복사합니다. 기존
destination은 덮어쓰지 않습니다.

```sh
./scripts/new-workspace.sh duplicate-delivery
```

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/duplicate-delivery
```

학습자 workspace 검증을 통과하고 위 자기 설명에 답한 뒤에만 reference와 비교합니다.

```sh
./scripts/verify-java.sh \
  exercises/02-delivery-and-consistency/01-duplicate-delivery/reference
```

검사는 첫 호출의 성공 응답이 아니라 재전달 뒤 잔액과 처리 이벤트 수를 확인합니다.
