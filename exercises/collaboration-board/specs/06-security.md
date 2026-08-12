# 06. 인증과 권한

## 목표

비밀번호 검증, 불투명 server session, board role과 admin 작업을 HTTP와 WebSocket이 공유하는 정책으로 구현합니다.

## 구현할 변경

- password hash만 저장하고 로그인에서 일정한 실패 응답을 사용합니다.
- 충분히 무작위인 raw token을 발급하고 DB에는 token digest와 만료를 저장합니다.
- `httpOnly`, `secure`, `sameSite`, `path`가 명시된 cookie를 발급·삭제합니다.
- authentication, account status, board membership와 role 검사를 분리합니다.
- 상태 변경 요청의 Origin·CSRF 계약과 정확한 CORS allowlist를 구현합니다.
- 계정 정지, session 폐기와 admin audit 기록을 transaction으로 묶습니다.

## 실패 조건

- 화면에서 button을 숨긴 것을 권한 검사로 간주합니다.
- logout이 cookie만 지우고 DB session을 남깁니다.
- URL id를 바꾸면 다른 사용자의 자원을 수정할 수 있습니다.
- 인증·cookie·password가 log에 기록됩니다.

## 검증

401·403 구분, 다른 board·다른 사용자 접근, session 만료·폐기, 잘못된 Origin, viewer 쓰기와 admin 권한을 실제 요청으로 검사합니다.

검증 진입점은 다음과 같습니다. `work/package.json`의 `verify:06`는 이 단계까지의 형 검사·테스트·build를 누적 실행해야 합니다.

```sh
node exercises/collaboration-board/checks/verify-work.mjs exercises/collaboration-board/work 6
```

## 완료 계약

HTTP와 WebSocket이 같은 신원·역할 정책을 사용하며, 권한 변경은 기존 연결에도 반영됩니다.
