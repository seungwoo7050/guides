# 비밀번호, 세션과 Cookie

로그인은 비밀번호가 맞는지 한 번 확인하는 과정과, 이후 요청에서 같은 사용자를 안전하게 식별하는 과정을 분리합니다. 비밀번호 원문과 세션 token은 유출 시 직접 악용될 수 있으므로 데이터베이스에도 그대로 저장하지 않습니다.

## 목표

- 비밀번호를 검증된 password hashing 함수로 저장·확인합니다.
- 예측할 수 없는 불투명 session token을 발급하고 digest만 저장합니다.
- cookie 속성과 session 수명을 일관되게 관리합니다.
- 로그인·로그아웃·만료·회전·계정 정지 후 상태를 정의합니다.
- 인증 오류와 운영 로그에서 비밀값을 노출하지 않습니다.

## 비밀번호는 암호화해서 되돌리는 값이 아닙니다

서비스는 원문 비밀번호를 복원할 필요가 없습니다. 검증된 password hashing library를 사용해 salt와 비용 설정이 포함된 hash를 저장합니다.

```ts
const passwordHash = await passwordHasher.hash(password);
const matches = await passwordHasher.verify(user.passwordHash, candidate);
```

일반 해시 함수인 SHA-256을 한 번 적용하거나 직접 salt 형식을 설계하지 않습니다. Argon2id, scrypt처럼 비밀번호용으로 검토된 방법을 검증된 라이브러리로 사용하고, 현재 배포 환경에서 허용 가능한 지연과 메모리 비용을 측정합니다.

## 입력 계약

비밀번호 정책은 사용자 경험과 공격 비용의 균형입니다.

- 충분한 최대 길이를 두고 지나치게 짧은 값은 거부합니다.
- 임의의 대·소문자·특수문자 조합만 강요하기보다 긴 passphrase를 허용합니다.
- Unicode normalization 정책을 명시합니다.
- 로그, validation detail와 telemetry에 원문을 남기지 않습니다.
- 회원가입과 변경 시 같은 규칙을 사용합니다.

로그인 실패 응답으로 이메일 존재 여부를 과도하게 드러내지 않습니다. 내부 로그에는 rate-limit과 조사에 필요한 식별자를 남기되 비밀번호는 절대 기록하지 않습니다.

## hash 갱신

시간이 지나 비용 설정을 높일 수 있습니다. 로그인 성공 시 저장된 hash가 옛 설정인지 확인하고 새 설정으로 다시 hash할 수 있습니다.

```text
verify 성공
→ rehash 필요 여부 확인
→ 새 hash 저장
→ 로그인 계속
```

비밀번호 변경은 기존 비밀번호 재확인, 새 hash 저장과 기존 session 폐기 정책을 함께 정의합니다.

## session token

세션 token은 충분한 entropy를 가진 cryptographic random bytes로 만듭니다.

```ts
const token = randomBytes(32).toString("base64url");
const digest = createHash("sha256").update(token).digest("hex");
```

여기서 SHA-256은 비밀번호가 아니라 이미 무작위인 token의 저장용 digest입니다. DB에는 digest만 저장하고 원문 token은 cookie로 한 번 전달합니다.

```sql
create table sessions (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  token_digest text not null unique,
  expires_at timestamptz not null,
  created_at timestamptz not null,
  last_seen_at timestamptz,
  revoked_at timestamptz
);
```

요청마다 cookie token을 digest로 바꾸어 session을 찾고, 만료·폐기·사용자 상태를 함께 확인합니다.

## Cookie 속성

```ts
reply.setCookie("app_session", token, {
  path: "/",
  httpOnly: true,
  secure: config.production,
  sameSite: "lax",
  maxAge: 60 * 60 * 24 * 14
});
```

- `HttpOnly`: JavaScript가 session token을 읽지 못하게 합니다.
- `Secure`: HTTPS에서만 전송합니다. 운영에서는 필수입니다.
- `SameSite`: cross-site 전송을 제한하지만 CSRF 전체를 대신하지 않습니다.
- `Path`: 필요한 범위만 전송하며 삭제할 때도 같은 값이 필요합니다.
- `Domain`: 꼭 필요하지 않으면 host-only cookie를 유지합니다.
- `Max-Age` 또는 `Expires`: browser 수명과 server 만료를 함께 설정합니다.

cookie 이름, path, domain을 발급과 삭제에서 다르게 쓰면 browser cookie가 남습니다.

## 로그인 흐름

```text
email·password parse
→ 사용자 조회
→ password verify
→ 계정 활성 상태 확인
→ 새 session token 생성
→ digest 저장
→ cookie 발급
→ 안전한 사용자 DTO 반환
```

password verify는 CPU·memory 비용이 있으므로 로그인 시도 제한이 필요합니다. IP 하나만 차단하면 공유 네트워크를 막을 수 있고, 계정 하나만 차단하면 공격자가 사용자를 잠글 수 있습니다. 여러 신호와 점진적 제한을 사용합니다.

## 세션 고정과 회전

인증 전 session id를 인증 후 그대로 사용하지 않습니다. 로그인, 권한 상승, 비밀번호 변경 같은 경계에서 새 token을 발급하고 이전 session을 폐기합니다.

동시에 허용할 session 수, 기기 목록, 전체 로그아웃 기능을 제품 계약으로 정합니다. “로그아웃”은 browser cookie 삭제뿐 아니라 server session 폐기까지 완료돼야 합니다.

## 요청 인증

Fastify hook이나 authentication plugin이 cookie를 읽고 actor context를 만듭니다.

```ts
interface Actor {
  userId: string;
  sessionId: string;
  accountStatus: "active" | "suspended";
}
```

route마다 token parsing을 복사하지 않습니다. 인증이 선택인 route와 필수인 route를 명시적으로 구분합니다. 사용자 행이 정지되거나 삭제됐으면 아직 만료되지 않은 session도 거부합니다.

## 만료와 정리

server의 `expires_at`가 최종 기준입니다. cookie가 browser에 남아도 만료된 session은 거부합니다. sliding expiration을 사용한다면 매 요청 DB 쓰기를 만들지 않도록 갱신 간격과 최대 절대 수명을 둡니다.

만료·폐기된 session 행은 정기적으로 정리하되, 감사 요구와 데이터 보존 정책을 고려합니다.

## 비밀번호 재설정

재설정 token도 무작위 원문은 사용자에게 보내고 digest만 저장합니다.

- 짧은 만료
- 한 번 사용 후 폐기
- 새 요청 시 이전 token 폐기 정책
- 성공 후 기존 session 전체 폐기 여부
- 계정 존재 여부를 과도하게 드러내지 않는 응답

메일 전송 성공과 token DB 저장 사이 실패도 정의합니다. 자세한 email 운영은 범위 밖이지만 token 수명 계약은 인증의 일부입니다.

## 로그와 오류

다음은 기록하지 않습니다.

- 원문 비밀번호
- session cookie
- authorization header
- reset token
- 전체 password hash

로그에는 request ID, user ID, session ID의 비민감 내부 식별자, 결과 code와 rate-limit 결과를 남길 수 있습니다. client에는 로그인 실패를 안정된 일반 오류로 반환합니다.

## 실패 조건

- 비밀번호를 암호화하거나 일반 hash 한 번으로 저장합니다.
- 직접 salt·hash 형식을 설계합니다.
- session 원문 token을 DB에 저장합니다.
- browser cookie만 지우고 server session을 남깁니다.
- 만료된 session이나 정지된 사용자 상태를 확인하지 않습니다.
- 로그인 전후에 같은 session token을 유지합니다.
- cookie·비밀번호를 로그에 남깁니다.

## 연결 실습

[`세션과 권한`](../../exercises/06-security/README.md)의 취약한 skeleton에서 session 폐기, cookie path와 인증 결과를 검사합니다.

## 완료 기준

- 비밀번호 hash와 무작위 session token digest의 차이를 설명합니다.
- 로그인·로그아웃·만료·회전 흐름을 구현할 수 있습니다.
- cookie의 `HttpOnly`, `Secure`, `SameSite`, `Path` 계약을 설명합니다.
- 계정 상태와 session 상태를 매 요청에서 함께 확인합니다.
- 인증 비밀값을 저장·로그·오류 응답에서 노출하지 않습니다.

## 다음 단계

인증된 사용자가 특정 자원에 무엇을 할 수 있는지 판정하고 cross-site 요청을 방어하는 방법은 [`권한, CSRF와 CORS`](05-authorization-csrf-cors.md)에서 다룹니다.
