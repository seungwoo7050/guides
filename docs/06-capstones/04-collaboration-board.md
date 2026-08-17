# 종합 프로젝트 4: 실시간 협업 보드

최종 프로젝트는 앞서 만든 화면, API, 데이터베이스, 인증 위에 WebSocket, 접속 상태, Canvas, 충돌 복구를 추가합니다. 기능 수가 많은 제품을 만드는 것이 목표가 아닙니다. **여러 경계에서 동시에 문제가 발생해도 상태의 기준, 자원 소유권, 종료 절차를 추적할 수 있는 시스템**을 만드는 것이 목표입니다.

기본 워크스페이스와 단계별 요구사항은 [`실시간 협업 보드 실습`](../../exercises/collaboration-board/README.md)에 있습니다. 기본 학습 경로에서는 패치를 적용하거나 표준 `skeleton/`을 직접 수정하지 않습니다. `pnpm workspace:create collaboration-board`로 생성한 `work/`에서 각 단계의 요구사항을 구현합니다.

## 완료 후 갖춰야 할 역량

프로젝트를 완료한 뒤에는 다음 내용을 설명하고 테스트로 증명할 수 있어야 합니다.

- 브라우저, Node.js, PostgreSQL, WebSocket의 실행 위치와 생명주기
- 서버, URL, 컴포넌트, 실시간 임시 상태의 기준 위치
- 라우트, 서비스, 리포지터리, 계약 패키지의 책임
- 세션, 역할, 소유권, `Origin`으로 구성된 권한 경계
- 스냅샷, 패치, 시퀀스, 버전을 사용하는 복구 절차
- 마이그레이션, 트랜잭션, 정상 종료와 실패 후 상태
- 타입 검사, 단위·API·DB·WebSocket·브라우저 테스트와 빌드가 증명하는 범위

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

공유 패키지에는 전송 스키마와 안정적인 DTO만 둡니다. 데이터베이스 어댑터, 서버 비밀값, React 컴포넌트 상태는 공유 패키지에 넣지 않습니다.

## 단계별 요구사항

### 1. 실행 환경과 워크스페이스

```text
apps/web
apps/api
packages/contracts
packages/db
```

완료 조건:

- 패키지의 공개 진입점
- 타입 검사·테스트·빌드 스크립트
- 환경 변수 검증
- 서버·타이머·연결 풀 종료
- 브라우저 전용 모듈과 Node.js 전용 모듈 분리

상세 요구사항: [`01-runtime-workspace.md`](../../exercises/collaboration-board/specs/01-runtime-workspace.md)

### 2. 브라우저 기반 화면

- 시맨틱 페이지와 폼
- 선택·검색 상태를 URL에 저장
- 키보드와 포커스 처리
- 320px 화면 레이아웃
- 로딩·빈 결과·오류 상태를 텍스트로 표시

상세 요구사항: [`02-browser-foundation.md`](../../exercises/collaboration-board/specs/02-browser-foundation.md)

### 3. 계약과 프런트엔드

- HTTP·WebSocket Zod 스키마
- React 목록과 동적 상세 경로
- Server Component와 Client Component 경계
- API 어댑터
- 요청 취소와 오래된 응답 차단

상세 요구사항: [`03-contracts-frontend.md`](../../exercises/collaboration-board/specs/03-contracts-frontend.md)

### 4. HTTP API

- Fastify 애플리케이션 팩터리
- 라우트·서비스·리포지터리
- 안정적인 400·401·403·404·409·500 응답
- 요청 ID와 비밀값 마스킹
- `app.inject` 테스트

상세 요구사항: [`04-http-api.md`](../../exercises/collaboration-board/specs/04-http-api.md)

### 5. PostgreSQL

- 사용자·세션·보드·구성원·항목·이벤트·관리자 작업 테이블
- 마이그레이션과 Kysely 타입
- 조건부 항목 갱신
- 항목·보드 버전과 이벤트 시퀀스
- 실제 데이터베이스의 롤백·경쟁 테스트

상세 요구사항: [`05-postgresql.md`](../../exercises/collaboration-board/specs/05-postgresql.md)

### 6. 보안

- 비밀번호 해시와 쿠키 세션
- `owner`·`editor`·`viewer` 역할
- 소유권과 계정 상태
- CSRF·CORS·WebSocket `Origin` 검증
- 관리자 작업·세션 폐기·감사 기록 트랜잭션

상세 요구사항: [`06-security.md`](../../exercises/collaboration-board/specs/06-security.md)

선택형 공유 메모 과제와 책임 범위가 일부 겹치지만 이 검증기는 보드 도메인만 검사합니다.

### 7. 실시간 기능

- `board.join`
- 스냅샷·패치·접속 상태
- 드래그 중 임시 좌표와 최종 트랜잭션
- 시퀀스 누락과 버전 충돌
- 하트비트·역압·재연결
- Canvas 좌표 변환과 접근 가능한 DOM 보조 UI

상세 요구사항: [`07-realtime.md`](../../exercises/collaboration-board/specs/07-realtime.md)

### 8. 품질 검증

- 단위·계약·컴포넌트 테스트
- 인증·권한 API 테스트
- 실제 PostgreSQL 테스트
- 실제 WebSocket 클라이언트 두 개를 사용하는 테스트
- Next.js 프로덕션 빌드
- 브라우저 E2E
- 자원 정리와 잘못된 구현 검출

상세 요구사항: [`08-quality.md`](../../exercises/collaboration-board/specs/08-quality.md)

## 핵심 데이터 계약

### 항목 이동 요청

클라이언트 입력:

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

서버가 확정한 패치:

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

서버는 좌표를 허용 범위로 제한하고 현재 멤버십과 버전을 검사합니다. 최종 이동은 항목 갱신, 보드 버전 증가, 이벤트 추가를 하나의 트랜잭션으로 처리합니다.

## 복구 절차

### 패치 누락

```text
클라이언트 lastSequence=17
새 패치 sequence=19
→ 19번 패치를 적용하지 않음
→ snapshot.request 전송
→ sequence>=19인 스냅샷 적용
→ 임시 미리보기 정리
```

### 버전 충돌

```text
baseVersion=4, DB version=5
→ 409 또는 operation.rejected(stale_item)
→ 최신 항목 또는 스냅샷 제공
→ 클라이언트 초안과 대기 작업 유지 또는 명시적으로 되돌림
```

### 재연결

```text
소켓 종료
→ 상한이 있는 지수 백오프 + 무작위 지연
→ 새 세션 확인
→ board.join
→ 최신 스냅샷
→ 이전 연결의 리스너와 타이머 제거
```

## 정상 종료

개발 서버도 명확한 종료 절차를 가져야 합니다.

1. 준비 상태를 `false`로 전환합니다.
2. 새 HTTP 요청과 WebSocket 업그레이드 수락을 중단합니다.
3. 진행 중인 요청이 끝나기를 제한된 시간 동안 기다립니다.
4. WebSocket 종료 프레임을 보내고 하트비트를 중단합니다.
5. 스케줄러와 타이머를 정리합니다.
6. 데이터베이스 연결 풀과 HTTP 서버를 닫습니다.
7. 전체 제한 시간이 지나도 남은 작업은 강제로 종료하고 원인을 기록합니다.

테스트가 끝나지 않는다면 누수된 핸들을 무시하고 성공 처리해서는 안 됩니다.

## 검증 명령 분리

최종 프로젝트에는 최소한 다음 명령이 독립적으로 있어야 합니다.

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

통합 `verify` 명령은 이들을 순서대로 실행할 수 있습니다. 그러나 각 명령도 따로 실행해 실패한 경계를 좁힐 수 있어야 합니다.

## 단계별 패치의 용도

정리된 단계별 패치는 권장 구현 순서를 비교하기 위한 선택형 자료입니다. 실제 Git 이력이 아니며 패치 전용 `walkthrough-base/`와 학습자용 `skeleton/`은 서로 다른 용도로 사용됩니다.

```sh
pnpm check:walkthrough
```

사용 순서:

```text
직접 구현
→ 단계 테스트 통과
→ 자신의 커밋 작성
→ 필요할 때만 최종 참조 구현과 패치를 보며 설계 비교
```

패치를 모두 적용해 완성하는 방식은 기본 학습 경로가 아닙니다.

## 최종 검증 시나리오

1. 소유자 로그인과 보드 생성
2. `editor`와 `viewer` 초대
3. 브라우저 두 개 또는 WebSocket 클라이언트 두 개 참가
4. 커서와 드래그 미리보기 전달
5. 최종 이동과 활동 기록 저장
6. `viewer`의 쓰기 거부
7. 같은 버전을 사용한 두 변경의 충돌
8. 패치 누락 후 스냅샷 복구
9. `editor`를 `viewer`로 변경한 뒤 기존 연결의 쓰기 거부
10. 재연결과 최신 스냅샷 수신
11. 로그아웃과 계정 정지 후 기존 세션·소켓 거부
12. 서버 종료 후 프로세스·타이머·연결 풀이 남지 않음

각 시나리오에서는 필요한 경우 화면, API 응답, 데이터베이스 상태, 소켓 메시지를 함께 확인합니다.

## 흔한 오류

- 클라이언트가 보낸 좌표와 역할을 신뢰합니다.
- HTTP와 WebSocket에서 서로 다른 권한 정책을 사용합니다.
- 드래그 중 모든 좌표를 데이터베이스에 저장합니다.
- 항목 갱신과 이벤트 삽입을 서로 다른 트랜잭션에서 처리합니다.
- 패치 누락을 무시하고 이후 패치를 계속 적용합니다.
- 재연결 후 이전 연결의 리스너와 대기 상태를 그대로 둡니다.
- 참조 패치를 적용한 결과를 학습 완료로 간주합니다.
- 타입 검사나 E2E 하나로 전체 품질을 대신합니다.

## 완료 기준

- 여덟 단계의 요구사항을 `skeleton/`에서 직접 구현합니다.
- HTTP, 데이터베이스, WebSocket이 같은 사용자·권한·버전 규칙을 사용합니다.
- 임시 상태와 확정 상태를 분리하고 패치 누락, 충돌, 재연결 후 같은 상태로 수렴합니다.
- 실제 PostgreSQL, 두 WebSocket 연결, 브라우저, 프로덕션 빌드를 검증합니다.
- 종료 후 프로세스, 타이머, 소켓, 연결 풀 누수가 없습니다.

## 다음 단계

이 프로젝트가 이 가이드의 종료점입니다. 이후에는 목적에 따라 React·Next.js 전문 과정, 데이터베이스 시스템, 웹 인프라, 분산 서비스 가이드로 이동합니다.
