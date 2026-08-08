# 공개 서비스 재구축 Capstone

이 과정의 최종 검증은 기존 서버에서 설정을 조금 고치는 일이 아닙니다. **기존 host가 사라졌다고 가정하고**, 외부에 보존한 원본만으로 새 host에 서비스를 복구합니다.

```text
새 Linux host
+ versioned provisioning 계약
+ exact release manifest와 image digest
+ secret 원본 또는 재발급 권한
+ 외부 backup
+ DNS 제어권
+ 관측·runbook
= 복구 가능한 공개 서비스
```

대응 실습은 [`exercises/18-production-rebuild`](../exercises/18-production-rebuild/)입니다. 자동 실습은 계획과 증거 schema를 검증하고, 실제 완료는 별도의 폐기 가능한 VPS에서 수행합니다.

## 1. Capstone의 목표

다음 상황을 가정합니다.

- 기존 production host에 접근할 수 없습니다.
- 기존 container와 local volume을 사용할 수 없습니다.
- 새 public IP가 할당됩니다.
- registry, Git, secret 원본, DNS provider와 외부 backup에는 접근할 수 있습니다.
- 복구 작업자는 기존 host의 shell history를 볼 수 없습니다.

완료 조건:

1. 새 host를 준비합니다.
2. exact release image를 실행합니다.
3. 외부 backup을 복원합니다.
4. 새 public TLS를 발급합니다.
5. DNS를 새 host로 전환합니다.
6. 외부 핵심 읽기·쓰기 경로를 확인합니다.
7. 로그·metric·경보가 정상임을 확인합니다.
8. 실제 RPO·RTO를 기록합니다.
9. 이전 host 없이 rollback·재배포할 수 있습니다.

## 2. 사용하면 안 되는 것

- 기존 host의 파일을 즉석에서 복사
- `latest` tag
- 개인 PC에만 있는 secret
- 기억에 의존한 수동 설정
- 검증되지 않은 가장 최근 backup
- `curl -k`만 사용하는 성공 판정
- production DNS를 먼저 바꾸고 나중에 검증
- 복구 중 production 외부 효과를 무제한 실행

숨은 의존성을 발견하는 것이 capstone의 목적입니다.

## 3. 시작 전 증거 묶음

### Release

```text
release manifest
image digest와 registry 위치
source revision
schema·config 호환 범위
SBOM·provenance 검증 결과
이전 rollback release
```

### Infrastructure

```text
지원 OS와 host 크기
필요 공개·관리 port
Docker·Compose 설치 절차
host directory와 permission
systemd 또는 시작 정책
firewall·IPv6 정책
```

### Identity와 secret

```text
SSH 관리자 키
registry pull credential
runtime secret 원본 또는 재발급 절차
DNS API·관리 접근
backup 복호화 key
ACME account 또는 재등록 절차
```

실제 값이 아니라 접근 경로와 소유자를 문서화합니다.

### Data

```text
선택한 backup ID
manifest와 checksum
DB schema version
upload snapshot
복원 명령
기대 row·object 검증치
```

### Operations

```text
외부 smoke test
관측 endpoint
alert test
incident·rollback runbook
RTO·RPO 목표
연락 경로
```

## 4. Stage 0: 복구 선언

작업 시작 시각과 목표를 기록합니다.

```yaml
exercise_id: rebuild-2026-08-07
started_at: 2026-08-07T13:00:00Z
target_rto_minutes: 240
target_rpo_minutes: 1440
selected_release: 2026-08-01.2
selected_backup: 2026-08-07T020000Z
incident_commander: operator-a
```

복구 중 새 쓰기를 허용할지, maintenance page를 제공할지 정합니다.

## 5. Stage 1: 새 host 준비

- 기대 OS·architecture 확인
- update와 reboot
- 관리자 사용자·SSH 검증
- 시간 동기화
- Docker Engine·Compose 설치
- Docker daemon 접근 주체 확인
- host firewall와 공개 port
- 운영 directory와 permission
- disk·inode 여유

증거:

```text
os-release
Docker·Compose version
관리 사용자와 group
listen port
firewall 결과
filesystem layout
```

설정 변경 뒤 별도 SSH 세션으로 재접속을 확인합니다.

## 6. Stage 2: Release 획득과 검증

```text
manifest 서명·schema 확인
→ image digest pull
→ provenance·SBOM 정책 확인
→ OCI label과 source revision 비교
→ Compose rendered config 확인
```

production host에서 source를 build하지 않습니다.

```sh
docker compose config >/dev/null
```

모든 image가 manifest의 exact digest인지 검사합니다.

## 7. Stage 3: Secret 주입

- 안전한 `umask`
- versioned secret 파일
- owner·group·mode 확인
- Compose에 필요한 secret 이름 확인
- 값은 로그에 출력하지 않음
- 폐기된 credential이 아닌지 확인
- DNS·backup credential은 application container와 분리

secret이 누락되면 application을 부분 공개하지 않습니다.

## 8. Stage 4: 데이터 복원

DNS 전환 전에 격리된 상태로 수행합니다.

```text
backup manifest 검증
→ checksum
→ 복호화
→ 빈 DB·upload target 준비
→ 복원
→ schema·row·object 검증
→ 외부 효과 비활성 application 시작
→ 내부 smoke
```

복원 실패 시 backup 원본을 수정하지 않습니다. 다른 backup 선택이 RPO에 어떤 영향을 주는지 기록합니다.

## 9. Stage 5: Gateway와 TLS

새 host를 임시 이름 또는 직접 주소로 검증합니다.

- port 80·443 접근
- ACME challenge
- hostname SAN
- full chain
- 만료 시각
- HTTP→HTTPS redirect
- gateway→application→DB 경로

DNS 전환 전에 가능한 검사를 최대한 수행합니다. public hostname 인증서 발급에 DNS가 새 host를 가리켜야 한다면 TTL과 전환 window를 계획합니다.

## 10. Stage 6: DNS 전환

- 변경 전 record 저장
- A·AAAA 일관성
- 새 IP 적용
- authoritative nameserver 확인
- 여러 외부 resolver 확인
- IPv4·IPv6 외부 요청
- 이전 endpoint와 cache window 관찰

DNS가 전파되는 동안 이전 host가 없다면 maintenance 또는 일부 실패를 수용해야 합니다. RTO 측정에 포함합니다.

## 11. Stage 7: 외부 기능 검증

다음 순서로 검사합니다.

```text
DNS
→ TCP 443
→ TLS hostname·chain
→ gateway health
→ application readiness
→ 핵심 읽기
→ 격리된 안전한 쓰기
→ 쓰기 결과 재조회
→ background 처리
```

성공 판정은 응답 코드뿐 아니라 필요한 본문·데이터 계약을 포함합니다.

## 12. Stage 8: 관측과 경보

- log에 새 host·release가 나타남
- request ID로 외부 smoke 추적
- metric scrape 또는 export 성공
- 외부 probe 성공
- certificate expiry metric
- backup age metric
- test alert 전달
- host disk·memory 관찰

관측 시스템이 새 host를 자동 발견한다고 가정하지 않습니다.

## 13. Stage 9: 운영 상태 확정

모든 검증 뒤에만 다음을 기록합니다.

```yaml
current_release: 2026-08-01.2
previous_release: null
host_id: provider-instance-...
public_ip: 198.51.100.20
activated_at: 2026-08-07T15:25:00Z
restored_backup: 2026-08-07T020000Z
external_smoke: passed
```

이전 host가 없으므로 `previous_release`는 registry에 남아 있는 호환 release를 별도 지정할 수 있습니다.

## 14. 실제 RPO와 RTO

### RPO

```text
장애 직전 마지막 알려진 정상 write 시각
- 복원된 최신 정상 write 시각
```

### RTO

```text
복구 선언 시각
→ 외부 핵심 읽기·쓰기 성공 시각
```

목표를 초과했다면 실패로 숨기지 않습니다. 가장 오래 걸린 단계와 자동화 후보를 기록합니다.

## 15. 의도적 실패 주입

한 번의 정상 재구축만으로 충분하지 않습니다. 다음 중 일부를 별도 폐기 환경에서 재현합니다.

### 잘못된 image digest

preflight가 실행 상태 변경 전에 거부해야 합니다.

### 누락된 secret

application이 명확히 실패하고 gateway가 정상인 척 핵심 기능을 제공하지 않아야 합니다.

### 손상된 backup

checksum 또는 restore validation에서 중단해야 합니다.

### 인증서 hostname 불일치

외부 smoke가 `-k` 없이 실패해야 합니다.

### disk 부족

복원·image pull 전에 preflight가 여유 부족을 발견해야 합니다.

### bad release

현재 데이터와 호환되는 이전 exact digest로 rollback하고 외부 smoke를 다시 통과해야 합니다.

## 16. 호스트 폐기 검증

재구축 완료 뒤 기존 host나 임시 복원 host를 폐기할 때:

- DNS·traffic이 더 이상 향하지 않음
- 필요한 log·evidence 보존
- backup staging 외부 전송 확인
- credential 폐기
- registry·DNS·backup 접근 token 회전 필요성 판단
- provider volume·snapshot 삭제 정책 적용
- 자산 목록에서 제거

host 삭제 버튼만 누르고 credential과 DNS record를 남기지 않습니다.

## 17. 산출해야 할 증거

압축파일이나 학습 repository에 실제 운영 secret을 넣지 않습니다. 별도 접근 통제 위치에 다음을 보존합니다.

```text
실행한 runbook version
release·backup manifest digest
단계별 시작·종료 시각
검사 명령과 redacted 결과
실제 RPO·RTO
실패와 수동 개입
경보 test 결과
rollback test 결과
후속 작업 owner·기한
```

## 18. Capstone 평가 기준

### 재현성

다른 작업자가 문서와 권한만으로 실행할 수 있습니다.

### 정본성

image, 설정, secret과 data의 원본이 명확합니다.

### 안전성

production 전환 전 격리 검증을 수행하고, 파괴적 조치에 안전 장치가 있습니다.

### 관측 가능성

각 단계의 성공·실패를 외부와 내부 증거로 확인합니다.

### 복구 가능성

손상된 backup·bad release·누락 secret을 안전하게 거부하거나 되돌립니다.

### 정직한 범위

단일 호스트의 중단과 잔여 위험을 숨기지 않습니다.

## 19. 자동 실습

[`exercises/18-production-rebuild`](../exercises/18-production-rebuild/)은 실제 VPS를 만들지 않습니다. 대신 완전한 rebuild plan과 evidence index를 검사합니다.

자동 검증:

- 단계 순서가 안전한가?
- exact digest와 backup ID가 있는가?
- secret 값이 포함되지 않았는가?
- DNS 전환 전 restore·internal smoke가 있는가?
- 외부 TLS 검증이 `-k`를 사용하지 않는가?
- RPO·RTO 측정 시각이 있는가?
- alert·rollback·corrupt backup failure drill이 있는가?
- 각 수동 단계에 owner와 중단 조건이 있는가?

이 검사를 통과한 뒤 실제 폐기 가능한 host에서 runbook을 실행해야 capstone이 완료됩니다.

## 20. 과정 종료 질문

다음에 정확한 경로와 증거로 답합니다.

1. 현재 production image digest는 무엇인가?
2. 호스트가 사라졌을 때 어느 backup과 release를 선택하는가?
3. 복호화 key와 DNS 권한에 누가 접근할 수 있는가?
4. 데이터 복원 성공을 어떤 사용자 기능으로 확인하는가?
5. 인증서 갱신 실패를 언제 발견하는가?
6. 배포 실패 시 어느 schema·release 조합으로 돌아가는가?
7. disk와 memory 고갈까지 남은 시간을 어떻게 추정하는가?
8. 사용자 사고에서 첫 15분에 누가 무엇을 결정하는가?
9. 마지막 실제 복원 훈련의 RPO·RTO는 얼마였는가?
10. 단일 host 구조에서 여전히 수용하는 위험은 무엇인가?

모든 답을 가지고 있다면 단순히 Docker를 사용할 줄 아는 것이 아니라, 작은 공개 서비스를 책임 있게 운영할 수 있는 기준선을 갖춘 것입니다.
