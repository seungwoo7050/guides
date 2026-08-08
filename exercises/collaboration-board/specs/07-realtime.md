# 07. 실시간 동기화와 Canvas

## 목표

server-authoritative snapshot·patch protocol, ephemeral presence, 영속 변경, 충돌과 재연결 복구를 구현합니다.

## 구현할 변경

- upgrade에서 Origin과 session을 검사하고 join 뒤에만 room에 넣습니다.
- snapshot과 단조 증가 sequence가 있는 patch를 정의합니다.
- cursor와 drag 중간 좌표는 메모리에서만 broadcast합니다.
- drag 완료는 baseVersion을 검사하고 DB transaction으로 저장합니다.
- gap·conflict·reconnect에서는 snapshot을 다시 받아 복구합니다.
- heartbeat, backoff+jitter, connection·timer cleanup을 구현합니다.
- Canvas는 React/server state의 projection으로만 사용하고 DPR과 좌표 변환을 처리합니다.

## 실패 조건

- client 좌표·role·version을 그대로 신뢰합니다.
- 모든 drag move를 DB에 기록합니다.
- room을 구분하지 않고 전체 연결에 broadcast합니다.
- reconnect 뒤 오래된 local state를 정본으로 사용합니다.

## 검증

두 client의 동일 patch, viewer 쓰기 거부, stale baseVersion, sequence gap, reconnect snapshot, heartbeat cleanup과 좌표 범위를 확인합니다.

검증 진입점은 다음과 같습니다. `work/package.json`의 `verify:07`는 이 단계까지의 형 검사·테스트·build를 누적 실행해야 합니다.

```sh
node checks/verify-work.mjs work 7
```

## 완료 계약

일시적 상태와 영속 상태가 분리되고, 연결 실패 뒤에도 모든 client가 server 정본으로 수렴합니다.
