# 세션, 권한과 브라우저 보안 경계

서버 세션의 발급·조회·폐기, 인증과 권한의 구분, 자원 소유권, 쿠키 범위, CORS와 CSRF 경계를 구현합니다. `skeleton/`에는 의도적인 취약점이 들어 있습니다.

## 선행 문서

- [`비밀번호, 세션과 쿠키`](../../docs/04-data-and-security/04-passwords-sessions-cookies.md)
- [`권한, CSRF와 CORS`](../../docs/04-data-and-security/05-authorization-csrf-cors.md)

## 작업하기

```sh
pnpm workspace:create 06-security
pnpm --dir exercises/06-security/work install
pnpm --dir exercises/06-security/work typecheck
pnpm --dir exercises/06-security/work test
```

테스트를 무조건 수정하지 말고, 실패 응답과 저장소 상태가 어떤 공격 경로를 나타내는지 먼저 적습니다.

## 반드시 수정할 취약점

- 로그아웃이 브라우저 쿠키만 지우고 서버 세션을 남깁니다.
- 관리 API가 로그인 여부만 확인하고 관리자 역할을 확인하지 않습니다.
- 사용자가 URL의 id를 바꿔 다른 사용자 프로필을 수정할 수 있습니다.
- 쿠키 발급과 삭제의 `path`가 달라 삭제가 실패합니다.
- credential 요청에서 요청 `Origin`을 그대로 CORS 허용 값으로 반사합니다.

## 완료 계약

- 인증 정보 없음은 401, 신원은 알지만 권한 부족은 403입니다.
- 로그아웃 뒤 같은 세션 토큰으로 보호 자원에 접근할 수 없습니다.
- 사용자 A는 사용자 B의 자원을 수정할 수 없습니다.
- 쿠키는 `httpOnly`, 환경에 맞는 `secure`, 명시적 `sameSite`, 일관된 `path`를 가집니다.
- 상태 변경 요청은 허용된 Origin과 필요한 CSRF 계약을 검사합니다.
- 인증 헤더, 세션 토큰과 비밀번호는 로그·응답에 노출되지 않습니다.

## Reference 구현 순서

아래 번호는 역사적 작성 순서가 아니라 하나의 security reference가 공유하는 권장 construction order입니다. JSON config는 직접 주석하지 않고 이 표가 bootstrap 책임을 설명합니다.

| 번호 | 위치 | 책임 |
|---:|---|---|
| [Implementation 0] | `pnpm install`, `package.json`, `tsconfig.json` | Fastify cookie·CORS·Zod와 TypeScript 실행 기반을 준비합니다. |
| 1 | `src/app.ts` identity state | 사용자·역할·server session과 입력 schema의 소유자를 정합니다. |
| 2 | `buildApp` plugin setup | 정확한 Origin allowlist와 credential cookie 처리를 구성합니다. |
| 3 | `preHandler` | session cookie가 있는 상태 변경 요청의 Origin invariant를 강제합니다. |
| 4 | login route | server session과 제한된 cookie를 함께 발급합니다. |
| 5 | logout route | server token과 같은 path의 browser cookie를 함께 폐기합니다. |
| 6 | `currentUser`, 401·403 helpers | authentication과 authorization 실패 의미를 분리합니다. |
| 7 | profile route | resource ownership과 admin 예외를 server에서 검사합니다. |
| 8 | admin route | 인증 뒤 role authorization을 별도 경계로 적용합니다. |
| 9 | `src/server.ts` | app을 만들고 network listen을 시작합니다. |

## 실패 주입

버튼 숨김만으로 권한을 막아 보고 직접 HTTP 요청이 성공하는지 확인합니다. 또한 404로 자원 존재를 숨길 경우와 403으로 권한 부족을 알릴 경우의 제품 계약 차이를 기록합니다.

## Reference 비교

자동 검증을 모두 통과한 뒤에만 `diff -ru exercises/06-security/work exercises/06-security/reference`로 구현을 비교합니다. 파일 배치나 표현이 달라도 계약을 만족하면 올바른 구현이며, 차이를 선택한 이유를 설명합니다.

## 완료 기준

정상 사용자의 흐름뿐 아니라 미인증, 역할 부족, 다른 사용자 자원, 폐기된 세션과 허용되지 않은 Origin이 자동 검사에서 거부되어야 합니다.
