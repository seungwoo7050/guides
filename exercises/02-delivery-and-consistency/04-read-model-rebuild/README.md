# 읽기 모델 checkpoint와 재구축

## 목표

projection 적용과 checkpoint 전진의 순서를 바꾸어 이벤트가 유실되는 실패를 확인하고, 재전달과 전체 재생에 안전한 읽기 모델을 만듭니다.

## 구현할 계약

- 이벤트 적용 전에 checkpoint를 전진하지 않습니다.
- 적용 뒤 checkpoint 전에 중단되면 같은 이벤트를 다시 읽습니다.
- 같은 event ID의 재전달은 집계를 두 번 바꾸지 않습니다.
- 빈 projection에 전체 로그를 재생하면 같은 최종 상태가 만들어집니다.

## 실패 조건

`skeleton`은 이벤트를 적용하기 전에 checkpoint를 증가시킵니다. 그 사이 중단되면 재시작한 소비자는 적용되지 않은 이벤트를 건너뜁니다.

## 작업

`Runner.processNext`의 checkpoint 갱신을 projection 적용 뒤로 옮깁니다. 적용 뒤 중단에 따른 재전달은 `Projection`의 event ID 중복 제거로 처리합니다.

## 권장 구현 순서

아래 번호는 실제 과거 작성 순서가 아니라, 이 reference 전체를 이해하기 위한 권장 학습용 구성 순서입니다.

| 번호 | 구현 대상 | 책임과 연결 |
|---|---|---|
| Implementation 1 | `Event` | 재전달 identity와 aggregate 변화량을 함께 정의합니다. |
| Implementation 2 | `EventLog` | 재생 가능한 입력 순서와 position 조회를 소유합니다. |
| Implementation 3 | `Projection` | 집계와 이미 적용한 event 근거를 함께 소유합니다. |
| Implementation 3-1 | `Projection.apply` | 재전달은 멱등 처리하고 ID 재사용 충돌은 거절합니다. |
| Implementation 4 | `Runner` | 로그 위치와 projection 적용 lifecycle을 조정합니다. |
| Implementation 4-1 | `Runner.processNext` | 적용 뒤에만 checkpoint를 전진합니다. |
| Implementation 4-2 | `Runner.replayAll` | 같은 처리 경로로 전체 로그를 재생해 상태를 수렴시킵니다. |

## 완료 기준

- 이벤트 적용 전에 중단되면 checkpoint가 전진하지 않습니다.
- 적용 뒤 checkpoint 전 중단은 재전달되어도 집계를 두 번 바꾸지 않습니다.
- 빈 projection의 전체 replay가 온라인 처리와 같은 상태·checkpoint로 수렴합니다.

## 자기 설명

- apply와 checkpoint 사이의 순서가 at-least-once 처리에 어떤 영향을 줍니까?
- 같은 event ID의 다른 payload를 단순 중복으로 무시하면 어떤 결함이 숨습니까?

## 검증

처음 한 번 안전한 학습자 workspace를 만듭니다. 이미 같은 경로가 있으면 덮어쓰지 않고 실패합니다.

```sh
./scripts/new-workspace.sh read-model-rebuild
```

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/read-model-rebuild
```

workspace 검증을 통과하고 위 자기 설명에 답한 뒤에만 reference와 비교합니다.

```sh
./scripts/verify-java.sh \
  exercises/02-delivery-and-consistency/04-read-model-rebuild/reference
```
