# DNS, ACME와 공개 TLS

로컬 self-signed 인증서는 암호화 흐름과 Nginx 설정을 학습하는 데 유용하지만, 공개 사용자는 그 인증서가 올바른 서비스의 것인지 자동으로 신뢰할 수 없습니다. 공개 운영에서는 **도메인 제어권, DNS 해석, 인증서 발급·갱신과 gateway reload**가 하나의 수명 주기를 이룹니다.

이 장의 목표는 다음 계약을 만들고 검증하는 것입니다.

```text
도메인이 의도한 공개 주소를 가리킴
→ ACME가 도메인 제어권을 확인함
→ gateway가 올바른 인증서와 개인키를 사용함
→ 사용자가 hostname·chain·유효기간을 검증함
→ 만료 전에 자동 갱신되고 gateway가 새 인증서를 읽음
→ 실패를 충분히 일찍 탐지함
```

대응 실습은 [`exercises/10-public-tls`](../exercises/10-public-tls/)입니다. 인터넷 도메인 없이도 로컬 CA, SAN과 만료 검증을 재현합니다.

## 1. DNS가 제공하는 것과 제공하지 않는 것

DNS는 이름을 주소나 다른 이름에 연결합니다.

```text
service.example A     198.51.100.20
service.example AAAA  2001:db8::20
www.example     CNAME service.example
```

DNS 응답 자체가 다음을 보장하지는 않습니다.

- 해당 주소의 서버가 올바른 애플리케이션을 실행하는가?
- TLS 개인키를 안전하게 보관하는가?
- HTTP 응답이 정상인가?
- 최근 배포가 성공했는가?

DNS는 연결의 첫 단계입니다. TLS와 애플리케이션 검사를 별도로 수행합니다.

## 2. 권한이 있는 DNS부터 확인하기

브라우저 cache나 로컬 resolver 한 곳만 보지 않습니다.

```sh
dig NS example.com
dig A service.example.com
dig AAAA service.example.com
dig +trace service.example.com
```

질문:

- authoritative nameserver는 어디인가?
- A와 AAAA가 모두 의도한 주소인가?
- 오래된 record가 남아 있는가?
- CNAME chain이 예상과 같은가?
- TTL은 변경 계획과 맞는가?

실제 record 변경 전 현재 값을 저장합니다. 잘못된 변경 뒤 되돌릴 원본이 필요합니다.

## 3. TTL과 변경 계획

TTL은 resolver가 응답을 cache할 수 있는 시간입니다. TTL을 낮추면 모든 사용자가 즉시 새 주소를 보게 된다는 뜻은 아니지만, 계획된 이전의 전파 시간을 줄이는 데 도움이 됩니다.

안전한 이전 흐름:

```text
이전 며칠 전 TTL 축소
→ 새 호스트를 별도 이름으로 검증
→ 인증서와 smoke test 확인
→ A/AAAA 전환
→ 여러 resolver와 외부 위치에서 확인
→ 이전 호스트 유지
→ 오류율 안정화 뒤 이전 호스트 종료
→ TTL 정상화
```

TTL 축소는 장애 발생 뒤 처음 수행해도 기존 cache의 TTL을 바꾸지 못합니다.

## 4. A와 AAAA의 일관성

IPv4만 새 호스트로 바꾸고 기존 AAAA가 남으면 일부 사용자는 오래된 IPv6 호스트에 연결할 수 있습니다.

검증:

```sh
curl -4I https://service.example
curl -6I https://service.example
```

IPv6를 제공하지 않는다면 AAAA를 남겨 두지 않습니다. 제공한다면 gateway, firewall, 인증서와 관측이 IPv4와 같은 계약을 만족해야 합니다.

## 5. ACME의 역할

ACME 클라이언트는 인증 기관과 통신해 도메인 제어권을 증명하고 인증서를 발급·갱신합니다. 대표적인 도전 방식은 HTTP-01과 DNS-01입니다.

### HTTP-01

인증 기관이 다음과 같은 HTTP 경로를 조회합니다.

```text
http://service.example/.well-known/acme-challenge/<token>
```

일반적인 조건:

- 공개 DNS가 검증 대상 호스트를 가리킵니다.
- 인터넷에서 TCP 80에 접근할 수 있습니다.
- gateway가 challenge 파일 또는 ACME 응답을 올바르게 제공합니다.
- 여러 frontend가 있으면 모든 요청이 동일한 token을 제공해야 합니다.

HTTP-01은 wildcard 인증서 발급에 사용할 수 없습니다.

### DNS-01

DNS TXT record를 사용해 제어권을 증명합니다.

```text
_acme-challenge.service.example TXT <token>
```

장점:

- wildcard 인증서를 발급할 수 있습니다.
- web server가 인터넷의 80 포트에 직접 응답하지 않아도 됩니다.

운영 위험:

- DNS API token을 사용하게 될 수 있습니다.
- token scope가 너무 넓으면 전체 도메인을 변경할 수 있습니다.
- DNS 전파와 provider API 오류를 처리해야 합니다.

가능하면 검증에 필요한 zone·record 권한만 가진 별도 자격 증명을 사용합니다.

## 6. 인증서 저장 위치와 소유권

인증서에는 공개 가능한 certificate chain과 비밀인 private key가 있습니다.

```text
공개 가능:
- leaf certificate
- intermediate chain

비밀:
- private key
- DNS API token
- ACME account key
```

private key를 다음 위치에 넣지 않습니다.

- Docker image layer
- Git repository
- CI 일반 로그
- application container가 쓸 수 있는 shared directory
- world-readable host path

인증서 수명 주기의 소유자를 하나 정합니다.

### 방식 A: host ACME agent

호스트에서 인증서를 발급·갱신하고 gateway에 read-only로 mount합니다.

장점:

- gateway image와 인증서 상태가 분리됩니다.
- host scheduler와 권한을 명확히 사용할 수 있습니다.

주의:

- host 경로와 container 경로를 정확히 연결해야 합니다.
- 갱신 뒤 gateway reload가 필요합니다.
- 새 호스트 재구축 시 account와 발급 절차가 필요합니다.

### 방식 B: gateway가 ACME를 직접 소유

Caddy나 Traefik처럼 gateway가 인증서를 자동 관리할 수 있습니다.

장점:

- routing과 인증서 수명 주기가 한 구성에 모입니다.

주의:

- 인증서 저장소를 영속화해야 합니다.
- gateway 교체와 scale-out 시 저장소·동시성 계약을 알아야 합니다.
- image rollback이 인증서 저장소를 되돌려서는 안 됩니다.

### 방식 C: 별도 ACME container

가능하지만 단순히 container를 하나 더 추가한다고 계약이 해결되지는 않습니다.

- 인증서 volume의 쓰기 소유자는 누구인가?
- gateway는 갱신을 언제 감지하는가?
- 실패한 갱신을 누가 관찰하는가?
- container가 멈추면 다음 갱신 전에 알 수 있는가?

## 7. HTTP에서 HTTPS로 전환

일반적인 공개 경계:

```text
80/tcp
  ├─ ACME HTTP-01 경로 제공
  └─ 나머지 요청은 HTTPS로 redirect

443/tcp
  └─ TLS 종료 후 애플리케이션으로 전달
```

redirect를 검사합니다.

```sh
curl -I http://service.example/
```

확인:

- 상태 코드가 의도한 영구 또는 임시 redirect인가?
- `Location`의 hostname과 path가 맞는가?
- query string이 보존되는가?
- ACME challenge 경로가 redirect 때문에 깨지지 않는가?

## 8. 인증서 검증

`curl -k`는 인증서 검증을 끕니다. 공개 운영의 성공 검사에는 사용하지 않습니다.

```sh
curl --fail --show-error --silent https://service.example/healthz
```

인증서 세부 확인:

```sh
openssl s_client \
  -connect service.example:443 \
  -servername service.example \
  -showcerts </dev/null
```

확인할 것:

- SAN에 실제 hostname이 포함되어 있는가?
- server가 intermediate chain을 함께 제공하는가?
- 만료 시각은 언제인가?
- 기대한 CA가 서명했는가?
- SNI를 보냈을 때 올바른 virtual host 인증서가 오는가?

CN만 보고 hostname 일치를 판단하지 않습니다. 현대 검증은 Subject Alternative Name을 사용합니다.

## 9. 갱신과 reload는 별도 단계

인증서 파일이 새로 발급돼도 실행 중 gateway가 자동으로 읽지 않을 수 있습니다.

```text
갱신 시도
→ 새 certificate와 key를 임시 위치에 기록
→ chain·hostname·유효기간 검사
→ 원자적으로 현재 파일 교체
→ gateway config 검사
→ graceful reload
→ 외부에서 새 serial·expiry 확인
```

reload 전에 설정 검사를 수행합니다.

```sh
nginx -t
```

container 안의 명령 경로와 실제 설정 위치를 사용합니다. reload가 실패하면 기존 worker가 기존 인증서로 계속 동작할 수 있는지 확인합니다.

## 10. 인증서 갱신 실패 감시

“자동 갱신을 설정했다”는 완료 조건이 아닙니다. 다음을 관찰합니다.

- 마지막 성공 갱신 시각
- 다음 만료까지 남은 시간
- ACME client 최근 종료 코드
- DNS API 또는 HTTP challenge 오류
- gateway가 현재 제공하는 인증서의 serial·expiry

경보는 충분한 수정 시간을 줘야 합니다.

예:

```text
만료 30일 전 경고
만료 14일 전 긴급도 상승
만료 7일 전 즉시 대응
```

실제 임계값은 인증서 수명과 조직 대응 속도에 맞춥니다. 파일의 만료일만 보지 말고 외부 endpoint가 제공하는 인증서를 확인합니다.

## 11. HSTS를 적용하기 전

HSTS는 브라우저가 일정 기간 해당 도메인에 HTTPS만 사용하도록 지시합니다. 강력하지만 잘못 적용하면 인증서나 HTTPS 구성 오류 때 사용자가 HTTP로 우회할 수 없습니다.

적용 전 확인:

- 모든 하위 도메인이 HTTPS를 지원하는가?
- `includeSubDomains`가 안전한가?
- preload 요구사항과 되돌리기 지연을 이해하는가?
- 인증서 갱신과 경보가 실제로 검증됐는가?
- HTTP 의존 서비스가 남아 있지 않은가?

처음에는 짧은 `max-age`로 동작을 관찰한 뒤 늘립니다. preload는 별도의 장기 결정입니다.

## 12. staging과 rate limit

ACME 구성을 반복 시험할 때 production CA endpoint만 사용하면 발급 제한에 도달할 수 있습니다. 지원되는 staging 환경을 먼저 사용하고, challenge·저장·reload 흐름이 완성된 뒤 production으로 전환합니다.

인증서 이름 집합과 재발급 정책을 계획합니다. 무작위로 새 이름을 생성하거나 실패할 때마다 새 인증서를 요청하는 자동화는 제한과 운영 혼란을 만듭니다.

## 13. 장애 상황

### DNS는 새 호스트, 인증서는 옛 hostname

TLS hostname 검증이 실패합니다. DNS 전환 전에 새 호스트가 실제 public hostname 인증서를 제공하도록 준비합니다.

### 인증서 파일은 갱신됐지만 gateway는 옛 인증서 제공

reload가 누락되었거나 다른 파일 경로를 읽고 있습니다. 파일과 외부 endpoint의 serial을 비교합니다.

### HTTP-01이 404

- challenge location 우선순위
- reverse proxy rewrite
- 여러 frontend 간 token 공유
- port 80 firewall
- A·AAAA 주소 불일치

순서로 확인합니다.

### DNS-01 record가 보이지만 검증 실패

authoritative nameserver에서 TXT를 직접 확인하고, 잘못된 zone이나 오래된 record가 아닌지 봅니다. 로컬 resolver cache 한 곳만 확인하지 않습니다.

## 14. 실습

[`exercises/10-public-tls`](../exercises/10-public-tls/)은 임시 디렉터리에서 다음을 수행합니다.

1. 로컬 root CA 생성
2. SAN에 `service.example.test`가 있는 server certificate 생성
3. chain과 hostname 검증
4. 만료 임계값 검사
5. 잘못된 hostname 인증서 거부
6. private key 권한 검사
7. 갱신 뒤 certificate serial 변경 확인

실습은 공인 CA를 흉내 내지 않습니다. 대신 공개 TLS 자동화에서 반드시 분리해야 하는 `발급`, `검증`, `교체`, `외부 확인` 계약을 재현합니다.

## 15. 공식 확인 자료

- Let’s Encrypt challenge types: <https://letsencrypt.org/docs/challenge-types/>
- Let’s Encrypt integration guide: <https://letsencrypt.org/docs/integration-guide/>
- Let’s Encrypt rate limits: <https://letsencrypt.org/docs/rate-limits/>
- OpenSSL verification options: <https://docs.openssl.org/master/man1/openssl-verify/>

다음 장에서는 호스트에서 소스를 빌드하는 대신, 검증된 image와 release manifest를 배포 단위로 만듭니다.
