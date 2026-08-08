# Runbook: 인증서 만료·갱신 실패

## 대상 증상과 사용자 영향

- 외부 TLS handshake 또는 hostname 검증이 실패합니다.
- 인증서 만료 임계값 경보가 발생합니다.
- ACME 갱신은 성공했다고 기록됐지만 gateway가 옛 인증서를 제공할 수 있습니다.

## 사전 안전 조건

- 공개 성공 검증에 `curl -k`를 사용하지 않습니다.
- 기존 동작 인증서와 개인키를 새 파일 검증 전에 덮어쓰지 않습니다.
- Production CA를 반복 시험하지 않고 staging endpoint를 사용합니다.
- Private key와 DNS API token을 로그에 출력하지 않습니다.

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
- SAN에 hostname이 있는가?
- Chain 검증이 되는가?
- Not Before·Not After는 언제인가?
- 여러 IP·IPv4·IPv6가 같은 인증서를 제공하는가?
- Serial은 무엇인가?

## 2. ACME 최근 결과 확인

사용 중인 ACME client의 service·timer와 로그를 확인합니다.

```sh
systemctl list-timers --all
systemctl status '<acme-service-or-timer>'
journalctl -u '<acme-service>' --since '24 hours ago'
```

Container 소유 방식이면 해당 service 상태와 log를 봅니다.

실패를 다음으로 분류합니다.

- Account·API 인증
- HTTP-01 reachability
- DNS-01 record·scope·propagation
- Rate limit
- File permission·disk
- 새 certificate 검증
- Gateway reload

## 3. Challenge 확인

### HTTP-01

- A·AAAA가 실제 challenge host를 가리키는지 확인합니다.
- 인터넷에서 port 80에 접근 가능한지 확인합니다.
- `/.well-known/acme-challenge/`가 application redirect·rewrite에 가려지지 않는지 봅니다.
- 여러 frontend가 같은 token을 제공하는지 확인합니다.

### DNS-01

```sh
dig TXT _acme-challenge.service.example
```

- Authoritative nameserver에 직접 질의합니다.
- API token이 필요한 zone·record만 수정할 권한이 있는지 확인합니다.
- 오래된 TXT와 새 TXT를 혼동하지 않습니다.

## 4. 새 파일과 Gateway 상태 분리

새 certificate가 생성됐다면 실행 중 gateway와 별도로 검증합니다.

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

Reload 뒤 외부 endpoint의 serial을 다시 확인합니다. 파일 serial과 외부 serial이 다르면 gateway가 다른 경로를 읽거나 reload되지 않은 것입니다.

## 5. 가역 완화

- 아직 유효한 기존 인증서를 유지하며 갱신 원인을 수정합니다.
- 새 인증서를 candidate 경로에 발급하고 검증 뒤 원자 교체합니다.
- HTTP-01 routing 오류만 수정하고 application 전체를 재배포하지 않습니다.
- DNS-01 token이 의심되면 별도 신뢰 장치에서 최소 scope token을 재발급합니다.

만료가 임박했고 자동화 수정 시간이 부족하면 승인된 수동 발급 절차를 사용하되, 다음 자동 갱신 전에 근본 원인을 수정합니다.

## 6. 고위험·중단 조건

- Private key 유출 가능성이 있으면 일반 갱신이 아니라 secret compromise 절차로 전환합니다.
- DNS 계정이 손상됐을 가능성이 있으면 신뢰할 수 있는 별도 경로에서 record와 token을 복구합니다.
- HSTS·preload 때문에 우회가 불가능한 경우 사용자 소통과 DNS 전환 영향을 함께 판단합니다.

## 7. 복구 확인

- 외부 hostname·chain 검증이 성공합니다.
- 모든 A·AAAA endpoint가 새 serial을 제공합니다.
- 만료까지 남은 시간이 정책 임계값보다 큽니다.
- HTTP→HTTPS와 핵심 application 경로가 성공합니다.
- 다음 자동 갱신 timer가 활성 상태입니다.
- 갱신 실패와 expiry alert의 test notification이 도착합니다.

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
