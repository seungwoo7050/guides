# Capstone 4: 실시간 협업 보드

최종 프로젝트는 앞선 화면·API·DB·인증 위에 WebSocket, presence, Canvas와 충돌 복구를 추가합니다. 목표는 기능 수가 많은 제품이 아니라 **여러 경계가 동시에 실패해도 정본·소유권·종료 계약을 추적할 수 있는 시스템**입니다.

기본 작업 공간과 단계별 계약은 [`실시간 협업 보드 실습`](../../exercises/collaboration-board/README.md)에 있습니다. 기본 학습 경로는 patch 적용이 아니라 skeleton에서 직접 구현하고 각 stage 요구사항을 통과하는 것입니다.

## 종료 능력

완료한 독자는 다음을 설명하고 증명할 수 있어야 합니다.

- browser·Node.js·PostgreSQL·WebSocket의 실행 위치와 수명
- server·URL·component·실시간 임시 상태의 정본
- route·service·repository·contract package의 책임
- session·role·ownership·Origin의 권한 경계
- snapshot·patch·sequence·version의 복구 계약
- migration·transaction·shutdown과 실패 후 상태
- typecheck·unit·API·DB·WS·build·browser 검사의 증거 범위

## 시스템 구조

```text
Browser / Next.js
  ├─ HTTP JSON ─────────────┐
  └─ WebSocket ─────────────┤
                            ↓
Fastify API + WebSocket Hub
  ├─ application services
  ├─ policy
  ├─ repositories
  └─ PostgreSQL
```

공유 package는 transport schema와 안정된 DTO만 제공합니다. DB adapter, server secret과 React component state를 공유 package에 넣지 않습니다.

## 단계

### 1. Runtime과 workspace

```text
apps/web
apps/api
packages/contracts
packages/db
```

완료 계약:

- package 공개 진입점
- typecheck·test·build script
- 환경 변수 검증
- server·timer·pool 종료
- browser와 Node.js 전용 module 분리

상세 요구사항: [`01-runtime-workspace.md`](../../exercises/collaboration-board/specs/01-runtime-workspace.md)

### 2. Browser foundation

- semantic page와 form
- URL에 선택·검색 상태
- keyboard·focus
- 320px layout
- loading·empty·error 상태 text

상세 요구사항: [`02-browser-foundation.md`](../../exercises/collaboration-board/specs/02-browser-foundation.md)

### 3. Contract와 frontend

- HTTP·WebSocket Zod schema
- React 목록·동적 상세 route
- server/client component 경계
- API adapter
- 요청 취소와 오래된 응답 방지

상세 요구사항: [`03-contracts-frontend.md`](../../exercises/collaboration-board/specs/03-contracts-frontend.md)

### 4. HTTP API

- Fastify app factory
- route·service·repository
- 안정된 400·401·403·404·409·500 계약
- request ID와 비밀값 redaction
- `app.inject` 검사

상세 요구사항: [`04-http-api.md`](../../exercises/collaboration-board/specs/04-http-api.md)

### 5. PostgreSQL

- users·sessions·boards·members·items·events·admin actions
- migration과 Kysely type
- 조건부 item update
- item·board version과 event sequence
- 실제 DB rollback·경쟁 검사

상세 요구사항: [`05-postgresql.md`](../../exercises/collaboration-board/specs/05-postgresql.md)

### 6. Security

- password hash와 cookie session
- owner·editor·viewer
- ownership·계정 상태
- CSRF·CORS·WebSocket Origin
- 관리자 조치·session 폐기·audit transaction

상세 요구사항: [`06-security.md`](../../exercises/collaboration-board/specs/06-security.md)

이 단계까지가 이전 capstone인 공유 메모의 종료점입니다.

### 7. Realtime

- `board.join`
- snapshot·patch·presence
- drag 중 임시 좌표와 final transaction
- sequence gap·version conflict
- heartbeat·backpressure·reconnect
- Canvas 좌표 변환과 접근 가능한 DOM 보조 UI

상세 요구사항: [`07-realtime.md`](../../exercises/collaboration-board/specs/07-realtime.md)

### 8. Quality

- 단위·계약·컴포넌트
- 인증·권한 API
- 실제 PostgreSQL
- 실제 두 WebSocket client
- Next.js build
- browser E2E
- resource cleanup와 잘못된 구현 검출

상세 요구사항: [`08-quality.md`](../../exercises/collaboration-board/specs/08-quality.md)

## 핵심 데이터 계약

### 항목 이동

client 입력:

```json
{
  "type": "item.move",
  "boardId": "...",
  "itemId": "...",
  "operationId": "...",
  "baseVersion": 4,
  "x": 320,
  "y": 180,
  "final": true
}
```

server 확정 patch:

```json
{
  "type": "board.patch",
  "boardId": "...",
  "sequence": 18,
  "operationId": "...",
  "actorId": "...",
  "operation": {
    "kind": "item.moved",
    "itemId": "...",
    "x": 320,
    "y": 180,
    "version": 5
  }
}
```

server는 좌표를 clamp하고 현재 membership·version을 검사합니다. final move는 item 갱신, board version 증가와 event 추가가 한 transaction입니다.

## 복구 계약

### Patch gap

```text
client lastSequence=17
새 patch sequence=19
→ 19를 적용하지 않음
→ snapshot.request
→ sequence>=19의 snapshot 적용
→ 임시 preview 정리
```

### Version conflict

```text
baseVersion=4, DB version=5
→ 409 또는 operation.rejected(stale_item)
→ 최신 item·snapshot 제공
→ client draft·pending operation 유지 또는 명시적 되돌림
```

### Reconnect

```text
socket close
→ 제한된 exponential backoff + jitter
→ 새 session 확인
→ board.join
→ 최신 snapshot
→ 이전 연결 listener·timer 제거
```

## 운영 가능한 종료 수명

개발 서버도 종료 계약을 가집니다.

1. readiness를 false로 전환합니다.
2. 새 HTTP·upgrade 수락을 멈춥니다.
3. 진행 중 request를 제한된 시간 기다립니다.
4. WebSocket에 close를 보내고 heartbeat를 중단합니다.
5. scheduler·timer를 정리합니다.
6. DB pool과 HTTP server를 닫습니다.
7. deadline 뒤 남은 작업을 강제 종료하고 원인을 기록합니다.

검사가 끝나지 않는다면 누수된 handle을 성공으로 숨기지 않습니다.

## 검증 명령의 분리

최종 프로젝트는 최소한 다음 명령을 독립적으로 가집니다.

```text
typecheck
unit·contract test
API integration test
DB integration test
WebSocket integration test
production build
browser E2E
full verify
```

하나의 `verify`는 이들을 순서대로 조립하되 각 명령을 따로 실행해 실패 경계를 좁힐 수 있어야 합니다.

## Patch 자료의 역할

기존 단계별 patch는 삭제하지 않고 선택적 walkthrough로 보존합니다. patch 전용 `walkthrough-base/`와 학습자용 `skeleton/`은 서로 다른 계약입니다.

```sh
pnpm check:walkthrough
```

사용 순서:

```text
직접 구현
→ stage 검사 통과
→ 자신의 commit
→ 필요한 경우 reference final·patch와 설계 비교
```

patch를 모두 적용해 완성하는 방식은 기본 학습 경로가 아닙니다.

## 최종 검증 시나리오

1. owner 로그인과 보드 생성
2. editor·viewer 초대
3. 두 browser 또는 두 WebSocket client 참가
4. cursor·drag preview 전달
5. final move와 activity 저장
6. viewer 쓰기 거부
7. 같은 version의 두 변경 충돌
8. patch gap에서 snapshot 복구
9. editor role을 viewer로 변경한 뒤 기존 연결 쓰기 거부
10. reconnect와 최신 snapshot
11. logout·계정 정지 뒤 기존 session·socket 거부
12. server 종료 후 process·timer·pool이 남지 않음

각 시나리오는 화면, API 응답, DB 상태와 socket message 중 필요한 증거를 함께 확인합니다.

## 실패 조건

- client 좌표와 role을 신뢰합니다.
- HTTP와 WebSocket이 다른 권한 정책을 사용합니다.
- drag 중 모든 좌표를 DB에 씁니다.
- item update와 event insert가 서로 다른 transaction입니다.
- patch gap을 무시하고 계속 적용합니다.
- reconnect 뒤 옛 listener와 pending state를 그대로 둡니다.
- reference patch 적용을 학습 완료로 간주합니다.
- typecheck 또는 E2E 하나로 전체 품질을 대신합니다.

## 완료 기준

- 여덟 단계의 계약을 skeleton에서 직접 구현합니다.
- HTTP·DB·WebSocket이 같은 사용자·권한·version 규칙을 사용합니다.
- 임시 상태와 확정 상태를 분리하고 gap·conflict·reconnect에서 수렴합니다.
- 실제 PostgreSQL·두 socket·browser·production build를 검증합니다.
- 종료 뒤 process·timer·socket·pool 누수가 없습니다.

## 다음 단계

이 가이드의 종료점입니다. 이후에는 목적에 따라 React·Next.js 전문 과정, 데이터베이스 시스템, 웹 인프라 또는 분산 서비스 가이드로 이동합니다.
