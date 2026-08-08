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

## 완료 기준

- 이벤트 적용 전에 중단되면 checkpoint가 전진하지 않습니다.
- 적용 뒤 checkpoint 전 중단은 재전달되어도 집계를 두 번 바꾸지 않습니다.
- 빈 projection의 전체 replay가 온라인 처리와 같은 상태·checkpoint로 수렴합니다.

## 자기 설명

- apply와 checkpoint 사이의 순서가 at-least-once 처리에 어떤 영향을 줍니까?
- 같은 event ID의 다른 payload를 단순 중복으로 무시하면 어떤 결함이 숨습니까?

## 검증

```sh
./scripts/verify-java.sh \
  exercises/02-delivery-and-consistency/04-read-model-rebuild/reference
```
