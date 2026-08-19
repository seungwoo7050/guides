# 런북: 인증서 만료·갱신 실패

## 대상 증상과 사용자 영향

- 외부 TLS 핸드셰이크 또는 호스트 이름 검증이 실패합니다.
- 인증서 만료 임계값 경보가 발생합니다.
- ACME 갱신은 성공했다고 기록됐지만 게이트웨이가 이전 인증서를 제공할 수 있습니다.

## 사전 안전 조건

- 공개 성공 검증에 `curl -k`를 사용하지 않습니다.
- 기존 동작 인증서와 개인키를 새 파일 검증 전에 덮어쓰지 않습니다.
- 운영 CA를 반복 시험하지 않고 스테이징 엔드포인트를 사용합니다.
- 개인키와 DNS API 토큰을 로그에 출력하지 않습니다.

## 1. 외부에서 실제 제공 인증서 확인

```sh
openssl s_client \
  -connect service.example:443 \
  -servername service.example \
  -showcerts </dev/null

curl --fail --show-error --silent \
  https://service.example/healthz
```

기록:

- DNS가 어느 IP를 반환하는가?
- SAN에 호스트 이름이 있는가?
- 체인 검증이 되는가?
- Not Before·Not After는 언제인가?
- 여러 IP·IPv4·IPv6가 같은 인증서를 제공하는가?
- Serial은 무엇인가?

## 2. ACME 최근 결과 확인

사용 중인 ACME 클라이언트의 서비스·타이머와 로그를 확인합니다.

```sh
systemctl list-timers --all
systemctl status '<acme-service-or-timer>'
journalctl -u '<acme-service>' --since '24 hours ago'
```

컨테이너가 소유하는 방식이라면 해당 서비스 상태와 로그를 봅니다.

실패를 다음으로 분류합니다.

- 계정·API 인증
- HTTP-01 reachability
- DNS-01 레코드·권한 범위·전파
- 발급 제한
- 파일 권한·디스크
- 새 인증서 검증
- 게이트웨이 리로드

## 3. Challenge 확인

### HTTP-01

- A·AAAA가 실제 challenge 호스트를 가리키는지 확인합니다.
- 인터넷에서 port 80에 접근 가능한지 확인합니다.
- `/.well-known/acme-challenge/`가 애플리케이션 리디렉션·rewrite에 가려지지 않는지 봅니다.
- 여러 프런트엔드가 같은 토큰을 제공하는지 확인합니다.

### DNS-01

```sh
dig TXT _acme-challenge.service.example
```

- 권한 있는 네임서버에 직접 질의합니다.
- API 토큰이 필요한 zone·record만 수정할 권한이 있는지 확인합니다.
- 오래된 TXT와 새 TXT를 혼동하지 않습니다.

## 4. 새 파일과 게이트웨이 상태 분리

새 인증서가 생성됐다면 실행 중 게이트웨이와 별도로 검증합니다.

```sh
openssl verify -CAfile '<trusted-chain>' '<candidate-certificate>'
openssl x509 -in '<candidate-certificate>' -noout \
  -checkhost service.example
openssl x509 -in '<candidate-certificate>' -noout -dates -serial
```

Nginx 예:

```sh
docker compose exec gateway nginx -t
docker compose exec gateway nginx -s reload
```

리로드 뒤 외부 엔드포인트의 serial을 다시 확인합니다. 파일 serial과 외부 serial이 다르면 게이트웨이가 다른 경로를 읽거나 리로드되지 않은 것입니다.

## 5. 가역 완화

- 아직 유효한 기존 인증서를 유지하며 갱신 원인을 수정합니다.
- 새 인증서를 후보 경로에 발급하고 검증 뒤 원자적으로 교체합니다.
- HTTP-01 라우팅 오류만 수정하고 애플리케이션 전체를 재배포하지 않습니다.
- DNS-01 토큰이 의심된다면 별도 신뢰 장치에서 최소 권한 범위 토큰을 재발급합니다.

만료가 임박했고 자동화 수정 시간이 부족하면 승인된 수동 발급 절차를 사용하되 다음 자동 갱신 전에 근본 원인을 수정합니다.

## 6. 고위험·중단 조건

- 개인키 유출 가능성이 있다면 일반 갱신이 아니라 비밀값 유출 절차로 전환합니다.
- DNS 계정이 손상됐을 가능성이 있다면 신뢰할 수 있는 별도 경로에서 레코드와 토큰을 복구합니다.
- HSTS·preload 때문에 우회가 불가능하다면 사용자 소통과 DNS 전환 영향을 함께 판단합니다.

## 7. 복구 확인

- 외부 호스트 이름·체인 검증이 성공합니다.
- 모든 A·AAAA 엔드포인트가 새 serial을 제공합니다.
- 만료까지 남은 시간이 정책 임계값보다 큽니다.
- HTTP→HTTPS와 핵심 애플리케이션 경로가 성공합니다.
- 다음 자동 갱신 타이머가 활성 상태입니다.
- 갱신 실패와 만료 경보의 테스트 알림이 도착합니다.

## 8. 증거와 후속 작업

```text
옛·새 serial과 expiry
실패 challenge와 CA 응답 분류
DNS·HTTP 변경
Gateway config test·reload 결과
외부 검증 결과
Token·key 회전 여부
다음 갱신 시험 날짜
```
