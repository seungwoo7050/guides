# 운영 비밀값과 설정

설정과 비밀값을 모두 `.env`라고 부르면 공개 가능한 동작 설정, 인증 정보와 versioned contract가 한 파일에 섞입니다. 운영에서는 값의 민감도뿐 아니라 **누가 읽고, 누가 쓰고, 언제 교체하며, 어떤 release와 호환되는지**를 구분해야 합니다.

이 장의 목표는 다음 수명 주기를 구현하는 것입니다.

```text
필요한 secret 정의
→ 최소 권한으로 생성·전달
→ 실행 시점에만 주입
→ 사용 여부 검증
→ 겹치는 기간을 두고 회전
→ 이전 값 폐기
→ 유출 시 영향 범위 확인과 재발급
```

대응 실습은 [`exercises/13-secret-rotation`](../exercises/13-secret-rotation/)입니다.

## 1. 값을 네 종류로 나누기

### 코드에 포함되는 기본값

민감하지 않고 모든 환경에서 같은 값입니다.

```text
기본 page size
지원 protocol version
내부 feature의 안전한 기본값
```

### 공개 환경 설정

환경마다 다르지만 공개돼도 인증 권한을 주지 않는 값입니다.

```text
PUBLIC_BASE_URL
LOG_LEVEL
WORKER_COUNT
DATABASE_HOST
FEATURE_FLAG
```

Git 또는 release manifest에 넣을 수 있지만 변경 이력과 schema를 관리합니다.

### 비밀값

노출되면 인증이나 권한을 제공하는 값입니다.

```text
DATABASE_PASSWORD
REGISTRY_PULL_TOKEN
DNS_API_TOKEN
BACKUP_ENCRYPTION_KEY
SESSION_SIGNING_KEY
```

### 파생·단기 credential

장기 원본에서 짧은 시간 동안 발급됩니다.

```text
OIDC로 교환한 cloud access token
짧은 수명 database credential
일회용 bootstrap token
```

가능하면 장기 고정 secret보다 짧은 수명 credential을 사용합니다.

## 2. Secret을 넣지 말아야 할 곳

- Git commit과 과거 이력
- Dockerfile `ARG`·`ENV`
- container image layer
- Compose 파일의 literal 값
- CI 로그와 debug 출력
- shell history
- process argument
- world-readable environment dump
- backup manifest의 평문 metadata

환경 변수는 편리하지만 다음 경로로 노출될 수 있습니다.

- process inspection 권한을 가진 주체
- crash report
- debug endpoint
- 잘못된 로그
- child process
- 지원 도구의 environment dump

모든 환경 변수가 즉시 위험하다는 뜻은 아닙니다. 민감도와 플랫폼의 노출 모델을 이해하고 file descriptor, mounted file 또는 secret manager를 선택합니다.

## 3. Compose secrets의 실제 경계

Compose는 secret을 service에 선언하고 container 내부의 `/run/secrets/<name>` 같은 파일로 제공할 수 있습니다.

```yaml
services:
  app:
    secrets:
      - db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

중요한 점:

- source file은 host에 존재합니다.
- standalone Compose에서 이 기능은 host 원본을 자동으로 암호화된 secret store에 저장해 주는 것과 같지 않습니다.
- host 파일 권한과 backup 정책이 여전히 중요합니다.
- secret을 허용받은 service만 mount하도록 구성해야 합니다.

Docker Swarm secret의 암호화·Raft 수명 주기와 standalone Compose file secret을 혼동하지 않습니다.

## 4. Secret 원본과 전달 경로

각 secret에 다음을 기록합니다.

| 항목 | 질문 |
|---|---|
| 이름 | 용도를 드러내고 값은 포함하지 않는가? |
| 원본 | password manager, cloud secret manager, offline key 중 어디인가? |
| 발급자 | 누가 만들고 회전할 수 있는가? |
| 소비자 | 어떤 service와 사용자만 필요한가? |
| 전달 | CI, provisioning, agent 중 어떤 경로인가? |
| 저장 | host에서 어디에 어떤 mode로 저장되는가? |
| 수명 | 만료·회전 주기는 무엇인가? |
| 폐기 | 이전 값을 언제 비활성화하는가? |
| 복구 | 원본 손실 시 다시 발급 가능한가? |

production host에 있는 파일 하나만 유일한 원본이면 호스트 손실과 함께 복구 권한도 사라집니다.

## 5. Host 파일 권한

예:

```text
/etc/example/secrets/
  db_password_v2
  session_key_v3
```

확인:

```sh
stat -c '%U %G %a %n' /etc/example/secrets/*
```

일반 원칙:

- 필요한 사용자·그룹만 읽습니다.
- 디렉터리 탐색 권한도 제한합니다.
- 애플리케이션은 secret 원본을 수정하지 못합니다.
- backup 도구가 읽어야 한다면 별도 권한과 감사 경계를 둡니다.
- 값 생성 시 안전한 `umask`를 사용합니다.

`chmod 600`만으로 container 안의 실제 접근 주체가 해결되는 것은 아닙니다. bind mount와 container UID/GID mapping을 확인합니다.

## 6. 시작 시 검증

필수 secret이 없거나 형식이 잘못되면 애플리케이션은 부분적으로 실행된 척하지 않고 명확히 실패해야 합니다.

검증 항목:

- 파일 존재
- 읽기 권한
- 빈 값이 아님
- 예상 encoding과 길이
- 허용된 version
- newline 처리
- 의존 서비스 인증 성공

실제 값은 오류 메시지에 출력하지 않습니다.

좋은 오류:

```text
required secret db_password_v2 is unreadable
```

나쁜 오류:

```text
login failed with password SuperSecret123!
```

## 7. 이름과 version

`DB_PASSWORD` 하나를 제자리에서 덮어쓰면 어느 소비자가 새 값을 읽었는지 판단하기 어렵습니다.

```text
db_password_v1
db_password_v2
```

또는 metadata에 version을 둡니다. release manifest는 필요한 secret **이름과 version**만 기록합니다.

```yaml
required_secrets:
  database_password: db_password_v2
  session_signing_key: session_key_v3
```

값 자체는 manifest에 넣지 않습니다.

## 8. 안전한 회전 패턴

### 두 credential을 동시에 허용할 수 있는 경우

```text
1. 새 credential 생성
2. provider에 old+new 모두 유효하게 등록
3. host에 새 secret 배포
4. 새 release 또는 reload로 소비자 전환
5. 실제 새 credential 사용 확인
6. 모든 소비자 전환 확인
7. old credential 폐기
8. 폐기 뒤 smoke test
```

### 하나의 비밀번호만 허용하는 데이터베이스

중단 없는 회전을 위해 별도 사용자 또는 임시 credential을 사용할 수 있습니다.

```text
app_user_v1 유지
→ app_user_v2 생성·동일 최소 권한 부여
→ application을 v2로 전환
→ connection pool 교체 확인
→ v1 로그인 거부
→ v1 사용자 삭제
```

권한을 복사할 때 과도한 권한까지 복제하지 않습니다.

### 서명 키 회전

session·token 서명 키는 검증과 발급 역할을 분리할 수 있습니다.

```text
새 키로 발급
+ 일정 기간 옛 키로 검증
→ 옛 token 최대 수명 경과
→ 옛 키 제거
```

즉시 옛 키를 제거하면 모든 활성 session을 강제 종료할 수 있습니다. 보안 사고에서는 그 결과가 의도일 수 있습니다.

## 9. 회전의 완료 증거

파일이 바뀐 것만 확인하지 않습니다.

- 새 connection 또는 token이 새 credential을 사용하는가?
- 오래 유지된 connection pool이 옛 credential로 남아 있는가?
- 모든 replica·worker가 reload됐는가?
- 옛 credential 사용 시 실제로 거부되는가?
- 배포·회전 event가 기록됐는가?
- 로그와 metric에 secret 값이 노출되지 않았는가?

회전 뒤 일정 기간 옛 credential 사용 시도를 탐지하면 누락된 소비자를 찾을 수 있습니다.

## 10. CI secret과 production runtime secret

CI가 image를 build하는 데 필요한 권한과 production application이 실행되는 데 필요한 권한을 분리합니다.

```text
CI build:
- source read
- registry push
- attestation write

Production host:
- registry pull
- runtime secret read
- backup write

Application:
- DB 최소 권한
- 필요한 외부 API scope
```

CI가 runtime DB 비밀번호를 알 필요가 없다면 제공하지 않습니다.

## 11. DNS와 backup secret

### DNS API token

- ACME TXT record에 필요한 zone만 허용합니다.
- record read/write 범위를 가능한 한 제한합니다.
- domain transfer·account billing 권한과 분리합니다.
- 사용 로그와 만료를 확인합니다.

### Backup encryption key

backup 파일과 같은 host·같은 저장소에 유일한 복호화 키를 두지 않습니다. 키 복구 절차를 별도로 시험합니다.

암호화 키를 잃으면 정상 backup도 복원할 수 없습니다. 공격자가 backup과 키를 함께 얻으면 암호화 효과가 줄어듭니다.

## 12. 로그와 진단에서 redaction

다음 패턴을 검사합니다.

- request header 전체 출력
- `Authorization`
- cookie
- query string token
- database DSN
- environment dump
- exception에 포함된 credential
- shell `set -x`

Redaction은 값이 저장된 뒤 삭제하는 것이 아니라 기록 전에 수행합니다. 낮은 entropy secret의 직접 hash는 사전 대입으로 원문을 추측하게 할 수 있습니다. 상관관계 식별이 꼭 필요하면 provider가 발급한 key ID·version을 우선 사용하고, 값에서 식별자를 만들어야 한다면 별도 audit key를 사용한 HMAC처럼 로그만으로 오프라인 추측하기 어려운 방식을 사용합니다.

## 13. 유출 대응

secret이 Git이나 로그에 노출되면 파일을 삭제하는 것만으로 끝나지 않습니다.

```text
1. 영향 secret 식별
2. 사용 권한과 접근 가능 기간 확인
3. 즉시 폐기 또는 제한
4. 새 credential 발급
5. 소비자 전환
6. 옛 credential 사용 탐지
7. Git·로그·artifact의 잔존 범위 처리
8. 원인과 예방 조치 기록
```

Git 이력에서 값을 제거하기 전에 먼저 credential을 폐기합니다. 이미 복제된 repository나 cache는 되돌릴 수 없습니다.

## 14. Break-glass credential

자동화와 일반 관리자 경로가 모두 실패했을 때 사용할 비상 권한이 필요할 수 있습니다.

조건:

- 평소에는 사용하지 않습니다.
- 강한 별도 보관과 접근 승인이 있습니다.
- 사용 시 즉시 알림과 감사 기록이 생깁니다.
- 사용 뒤 반드시 회전합니다.
- 정기적으로 접근 가능성과 절차를 시험합니다.

비상 credential이 편리한 상시 우회 경로가 되면 안 됩니다.

## 15. 실습

[`exercises/13-secret-rotation`](../exercises/13-secret-rotation/)은 임시 host root에서 versioned secret을 회전합니다.

학습자는 다음 계약을 구현합니다.

1. 안전한 권한으로 새 version 생성
2. 값 자체를 event log에 기록하지 않음
3. 새 소비자 검증 전 current pointer를 바꾸지 않음
4. 원자적으로 current version 전환
5. 검증 실패 시 이전 version 유지
6. 전환 확인 뒤에만 이전 version 폐기 가능
7. 실제 secret 대신 fingerprint와 metadata만 출력

실습은 외부 secret manager 제품을 흉내 내지 않습니다. 모든 구현에 필요한 회전 순서와 실패 후 상태를 검증합니다.

## 16. 공식 확인 자료

- Docker Compose secrets: <https://docs.docker.com/compose/how-tos/use-secrets/>
- Docker Compose trust model: <https://docs.docker.com/compose/security/trust-model/>
- Docker build secrets: <https://docs.docker.com/build/building/secrets/>
- GitHub Actions OIDC: <https://docs.github.com/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect>

다음 장에서는 배포·secret·서비스 상태가 실제 사용자 영향으로 어떻게 나타나는지 로그, 지표와 경보로 연결합니다.
