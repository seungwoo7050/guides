# Capstone 3: 공유 메모

세 번째 프로젝트는 브라우저·API·DB·세션·권한을 하나의 작은 풀스택 애플리케이션으로 연결합니다. 실시간 기능은 아직 넣지 않습니다. 먼저 요청마다 사용자를 식별하고, 공유된 자원에서 역할별 허용 동작이 일관되게 지켜지는지 완성합니다.

> **형태:** 이 문서는 보안 실습 뒤 선택해서 수행하는 self-directed expected-evidence brief입니다. 저장소에는 이 brief 전용 skeleton, 자동 verifier 또는 reference 구현이 없습니다. 저장소 밖의 학습자 소유 프로젝트에서 구현하고 아래 evidence rubric으로 완료를 검토합니다.

## 목표

사용자는 다음 일을 할 수 있습니다.

1. 회원가입·로그인·로그아웃합니다.
2. 자신의 메모를 만들고 목록·상세를 봅니다.
3. 다른 사용자를 editor 또는 viewer로 초대합니다.
4. editor는 내용을 수정하지만 구성원 역할은 바꾸지 못합니다.
5. viewer는 읽을 수 있지만 수정할 수 없습니다.
6. 소유자는 구성원의 역할을 바꾸거나 제거합니다.
7. conflict가 발생하면 최신 내용과 자신의 draft를 비교합니다.
8. 작은 화면과 keyboard로 핵심 흐름을 사용할 수 있습니다.

이 프로젝트의 책임 경계는 최종 [`collaboration-board`](../../exercises/collaboration-board/README.md) Stage 01–06과 개념적으로 대응합니다. 그러나 협업 보드 검사기는 board 전용 경로·script·계약을 요구하므로 notes 프로젝트를 검증하지 않습니다. 해당 skeleton이나 verifier를 우회해 재사용하지 말고, 이 문서의 수동 evidence rubric을 사용합니다. WebSocket·Canvas는 다음 capstone의 별도 도메인에서 추가합니다.

## 사용자 흐름

### 로그인

```text
로그인 form 제출
→ API가 password 검증
→ server session 생성
→ HttpOnly cookie 발급
→ /me로 현재 사용자 확인
→ 메모 목록 표시
```

page가 localStorage token을 직접 읽지 않습니다. 새로고침해도 cookie session으로 사용자를 복원합니다.

### 공유

```text
owner가 이메일로 사용자 검색
→ 초대 또는 membership 생성
→ 대상 사용자의 목록에 메모 표시
→ 현재 role과 허용 동작 표시
```

이메일을 body로 보냈다고 해당 사용자와 관계가 자동으로 생기지 않습니다. server가 대상 계정·상태와 중복 membership을 검증합니다.

## HTTP 표면

```text
POST   /auth/register
POST   /auth/login
POST   /auth/logout
GET    /me

GET    /notes
POST   /notes
GET    /notes/:id
PATCH  /notes/:id
DELETE /notes/:id

GET    /notes/:id/members
POST   /notes/:id/members
PATCH  /notes/:id/members/:userId
DELETE /notes/:id/members/:userId

GET    /notes/:id/activity
```

모든 상태 변경은 trusted Origin과 CSRF 정책을 통과해야 합니다.

## 역할 불변식

- 메모에는 항상 한 명 이상의 owner가 있어야 합니다.
- owner만 구성원을 추가·변경·제거할 수 있습니다.
- 마지막 owner를 제거하거나 강등할 수 없습니다.
- editor는 title·body를 수정할 수 있습니다.
- viewer는 읽기만 가능합니다.
- 정지된 계정은 기존 session으로도 접근할 수 없습니다.
- role 변경과 activity 기록은 같은 transaction입니다.

UI는 허용되지 않은 button을 숨기거나 disabled로 안내하되, server 정책이 최종 방어선입니다.

## 데이터 모델

기존 `users`, `sessions`, `notes`, `note_activity`에 다음을 추가합니다.

```sql
create table note_members (
  note_id uuid not null references notes(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('owner', 'editor', 'viewer')),
  created_at timestamptz not null,
  primary key (note_id, user_id)
);
```

소유자 정보가 `notes.owner_id`와 `note_members`에 중복되면 두 값이 어긋날 수 있습니다. 하나의 정본을 선택합니다. 기본안은 membership의 `owner` role을 정본으로 사용하고, 생성 transaction에서 첫 owner membership을 함께 만듭니다.

## 프런트엔드 구조

```text
app/
├── login/
├── notes/
│   ├── page.tsx
│   └── [id]/page.tsx
└── layout.tsx

features/notes/
├── note-api.ts
├── note-editor.tsx
├── member-list.tsx
└── note-state.ts
```

필수 구분:

- URL: 선택된 note와 검색·page
- server state: note·members·activity
- component state: form draft·dialog
- session state: `/me` 결과

API response는 adapter에서 Zod로 다시 parse합니다.

## Server·Client 경계

첫 page 데이터는 server component에서 읽을 수 있지만, browser cookie와 API origin, cache 정책을 명확히 합니다. 편집 form, dialog와 낙관적 갱신은 client component입니다.

교육 목적상 모든 요청을 client fetch로 시작해도 되지만, 어떤 파일이 browser에서 실행되고 비밀 환경 변수가 bundle에 들어가지 않는지 설명할 수 있어야 합니다.

## 편집과 conflict

```text
editor가 version 5를 열음
→ draft 수정
→ PATCH baseVersion=5
→ 다른 사용자가 먼저 version 6 저장
→ 409 stale_note + 최신 DTO
→ 화면에 최신 내용과 draft를 모두 보존
```

사용자 입력을 조용히 버리거나 마지막 도착 값으로 덮지 않습니다. “최신 내용으로 다시 시작”, “내 draft 복사” 같은 복구 경로를 제공합니다.

## 세션과 CSRF

- password hash는 검증된 library 사용
- session token digest 저장
- HttpOnly·Secure·SameSite cookie
- login·password change 시 session 회전
- logout 시 server session 폐기
- 상태 변경의 Origin 검증과 CSRF token 정책
- CORS allowlist와 credential 설정

브라우저 E2E에서 실제 cookie jar와 logout 후 접근 거부를 확인합니다.

## 접근성과 반응형

- login·편집 form의 label과 오류 연결
- 저장 중·완료·conflict 상태 알림
- member role을 색뿐 아니라 text로 표시
- dialog focus 진입·복귀
- keyboard로 저장·취소 가능
- 320px에서 editor와 member panel 재배치

## 검사 행렬

### 인증

```text
잘못된 비밀번호
로그아웃 뒤 /me
만료 session
정지 사용자 기존 session
cookie 발급·삭제 path
```

### 권한

```text
비구성원 읽기
viewer 수정
editor 구성원 관리
owner 역할 변경
마지막 owner 제거
다른 note ID로 요청
```

### 데이터

```text
note 생성 + owner membership
수정 + activity rollback
role 변경 + activity rollback
같은 version 경쟁
```

### Browser

```text
login → 목록 → 상세 → 수정 → logout
owner 초대 → viewer 로그인 → 읽기 성공·수정 거부
409 conflict에서 draft 보존
직접 상세 URL 새로고침
keyboard와 작은 화면
```

## 구현 순서

1. 공유 HTTP·response schema를 고정합니다.
2. session 없는 note UI를 API와 연결합니다.
3. users·password·sessions migration을 추가합니다.
4. authentication hook과 `/me`를 연결합니다.
5. membership과 role policy를 추가합니다.
6. CSRF·CORS·session 폐기 검사를 추가합니다.
7. conflict UI와 browser 흐름을 완성합니다.
8. typecheck·API·DB·build·E2E를 독립 실행합니다.

## 범위 밖

- WebSocket과 presence
- Canvas
- 여러 server instance 사이 실시간 broadcast
- OAuth provider
- 이메일 발송 인프라
- production 배포·TLS

## 완료 기준

- React·Next.js 화면과 Fastify·PostgreSQL을 계약으로 연결합니다.
- password·session·cookie 수명을 구현하고 logout 뒤 server 상태를 폐기합니다.
- 역할·소유권을 HTTP와 데이터베이스 transaction에서 보호합니다.
- 409 conflict에서도 사용자 draft와 최신 상태를 함께 보존합니다.
- 핵심 인증·권한 흐름을 실제 browser와 DB로 검사합니다.

## Expected evidence rubric

학습자 프로젝트에 다음 증거를 남깁니다. 자동 채점 답안이 아니라 명령과 결과를 다시 실행할 수 있는 review record입니다.

| 증거 | 최소 내용 |
|---|---|
| state ownership | URL·server·component·session 상태의 정본과 adapter 경계 |
| security | cookie 속성, session 폐기, Origin/CSRF, 401·403·404 선택 근거 |
| authorization | owner·editor·viewer 행렬과 마지막 owner·다른 note 거부 결과 |
| transaction | note·membership·activity의 commit/rollback·경쟁 결과 |
| browser | 로그인부터 logout, viewer 거부, 409 draft 보존, keyboard·320px 결과 |
| lifecycle | app·pool·browser와 외부 resource의 시작·종료 명령 |

guides 저장소에는 이 결과와 비교할 reference가 없으며 collaboration-board gate 통과를 공유 메모의 완료 증거로 주장할 수 없습니다. 자동 검증이 필요한 기본 경로는 `06-security`에서 Part 05로 이어집니다.

## 다음 단계

기본 학습 경로의 `07-websocket`과 `08-testing`을 먼저 완료한 뒤, 연결 수명·임시 상태·여러 사용자의 수렴을 통합하는 최종 runnable 프로젝트 [`실시간 협업 보드`](04-collaboration-board.md)로 이동합니다.
