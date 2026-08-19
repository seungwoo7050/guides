# Linux 호스트 준비와 강화

공개 서비스의 가장 바깥쪽 신뢰 경계는 컨테이너가 아니라 호스트입니다. 호스트의 관리자 계정, SSH, 방화벽, Docker daemon, 디스크가 손상되면 내부 컨테이너 분리만으로는 충분히 보호할 수 없습니다.

이 장의 목표는 특정 배포판의 명령을 모두 외우는 것이 아닙니다. 다음 계약을 만족하는 호스트를 반복해서 준비하는 것입니다.

```text
관리 경로는 제한되고 검증됨
공개 포트는 의도적으로 열림
Docker daemon 접근 주체가 명확함
운영 파일과 영속 데이터 경로가 분리됨
시간·디스크·업데이트 상태를 관찰할 수 있음
호스트를 버리고 다시 만들 수 있음
```

대응 실습은 [`exercises/09-host-hardening`](../exercises/09-host-hardening/)입니다. 실습은 실제 호스트 설정을 변경하지 않고 제공된 상태 스냅샷을 점검합니다.

## 1. 재현 가능한 호스트 기준선

서버를 수동으로 오래 수정할수록 새 호스트에서 동일한 상태를 재현하기 어려워집니다. 처음부터 다음 정보를 기록합니다.

- 공급자와 리전
- 배포판과 정확한 버전
- CPU, 메모리, 디스크 크기
- 네트워크 주소와 공개 IP
- 설치한 Docker Engine·Compose 버전
- 호스트 사용자와 그룹
- 열린 포트
- `/srv`, `/etc`, `/var/lib`, `/var/backups` 아래의 운영 경로
- 적용한 보안 업데이트 시점
- 프로비저닝 절차의 원본 위치

명령 기록만으로 충분하지 않습니다. 각 단계 뒤의 검증 결과도 함께 남깁니다.

## 2. 호스트를 처음 받을 때

공급자 콘솔 또는 임시 관리자 접근으로 다음을 확인합니다.

```sh
cat /etc/os-release
uname -a
id
ip address
ip route
lsblk -f
df -h
df -i
```

확인할 질문:

1. 기대한 배포판과 아키텍처인가?
2. 루트 파일 시스템과 데이터 디스크는 어디인가?
3. IPv4와 IPv6가 모두 활성화되어 있는가?
4. 기본 라우트와 DNS 해석이 되는가?
5. 디스크뿐 아니라 inode 여유가 있는가?
6. 공급자 스냅샷이나 콘솔 복구 경로가 있는가?

문제가 있으면 애플리케이션을 설치하기 전에 해결합니다.

## 3. 관리자 사용자와 SSH

### 3.1 별도 관리자 계정

일상적인 운영에 root 직접 로그인을 기본으로 사용하지 않습니다. 별도 사용자를 만들고 필요한 관리 작업만 `sudo`로 수행합니다.

```text
공급자 초기 관리자
→ 운영 사용자 생성
→ 공개키 설치
→ sudo 동작 확인
→ 새 세션으로 재접속 확인
→ 불필요한 로그인 경로 제한
```

가장 중요한 원칙은 **기존 경로를 제한하기 전에 새 관리 경로가 실제로 동작하는지 확인하는 것**입니다. 현재 SSH 세션 하나만 믿고 설정을 바꾸면 서버에 다시 접속하지 못할 수 있습니다.

### 3.2 공개키 인증

- 운영자마다 별도 키를 사용합니다.
- 개인키는 서버에 복사하지 않습니다.
- 공유 계정 하나에 여러 사람이 같은 개인키를 사용하지 않습니다.
- 오래된 키를 제거할 소유자와 절차를 정합니다.
- 가능한 경우 개인키에 암호 문구(passphrase)를 설정합니다.

SSH 설정은 배포판과 버전에 따라 파일 위치와 기본값이 다를 수 있습니다. 변경 전 다음을 수행합니다.

```sh
sshd -T
sudo sshd -t
```

`sshd -t`가 성공해도 실제 로그인 정책이 의도와 같다는 뜻은 아닙니다. 별도 터미널에서 새 연결을 확인합니다.

### 3.3 관리 포트 변경의 의미

SSH 포트를 22가 아닌 값으로 바꾸면 자동 스캔 로그는 줄어들 수 있지만 인증과 권한 통제를 대신하지 않습니다. 다음 항목이 우선입니다.

- 키 기반 인증
- 불필요한 사용자 로그인 제한
- 공급자 방화벽 또는 호스트 방화벽
- 실패·성공 로그인 관찰
- 키 폐기 절차

## 4. 최소 권한과 Docker daemon

Docker 데몬은 호스트에서 매우 강한 권한을 가집니다. 데몬 소켓에 접근할 수 있는 주체는 컨테이너 생성, 호스트 경로 마운트, `privileged` 옵션 등을 통해 호스트 전체에 영향을 줄 수 있습니다.

따라서 다음을 명시합니다.

- 누가 `docker` 명령을 실행할 수 있는가?
- 애플리케이션 컨테이너가 `/var/run/docker.sock`을 마운트하는가?
- CI 러너가 운영 Docker 데몬에 직접 접근하는가?
- 원격 데몬 API가 열려 있는가?
- 소켓 프록시를 사용한다면 실제로 어떤 API를 허용하는가?

### 4.1 `docker` 그룹

일반적인 rootful Docker 설치에서 `docker` 그룹 접근은 단순한 “컨테이너 관리 권한”보다 강합니다. 이 그룹의 구성원을 관리자와 같은 수준으로 신뢰해야 합니다.

```sh
getent group docker || true
find /var/run -maxdepth 1 -name 'docker.sock' -ls 2>/dev/null || true
```

애플리케이션 사용자와 웹 컨테이너에는 데몬 소켓 접근 권한을 주지 않습니다.

### 4.2 Rootless 모드

Rootless 모드는 데몬과 컨테이너를 일반 사용자 네임스페이스 안에서 실행해 rootful 데몬의 위험을 줄이는 선택지입니다. 하지만 모든 환경에서 자동으로 더 단순하거나 완전히 격리되는 것은 아닙니다.

검토할 항목:

- 낮은 포트 바인딩 방식
- cgroup과 자원 제한 지원
- 스토리지 드라이버
- 네트워크 성능과 기능
- systemd 사용자 서비스의 시작 정책
- 운영 사용자의 linger와 세션 수명
- 백업해야 할 Rootless 모드의 데이터 루트

이 과정의 실습은 rootful과 rootless 방식 중 하나를 강제하지 않습니다. 선택과 잔여 위험을 운영 계약에 기록합니다.

### 4.3 원격 데몬

인증되지 않은 TCP 소켓으로 Docker 데몬을 공개하지 않습니다. 원격 관리가 필요하면 공식 문서가 설명하는 SSH 또는 상호 TLS 보호 방식을 사용하고 네트워크 노출과 인증 주체를 별도로 제한합니다.

## 5. 공개 포트와 방화벽

운영 기준선에서 외부에 필요한 포트는 보통 다음 정도입니다.

```text
80/tcp   ACME HTTP-01과 HTTPS redirect
443/tcp  공개 HTTPS
관리 경로 SSH  제한된 출발지 또는 별도 관리망
```

데이터베이스, FastCGI, 애플리케이션 런타임, 모니터링 관리 포트는 인터넷에 직접 게시하지 않습니다.

```yaml
services:
  db:
    # ports 없음: Compose 내부 network에서만 접근
  app:
    # ports 없음
  gateway:
    ports:
      - "80:80"
      - "443:443"
```

관리용 대시보드가 필요하면 다음 중 하나를 사용합니다.

- `127.0.0.1`에만 바인드하고 SSH 터널 사용
- 인증된 VPN 또는 관리망
- 별도의 강한 인증 게이트웨이

### 5.1 Docker와 호스트 방화벽의 상호작용

Docker는 Linux에서 브리지 네트워크와 포트 게시를 위해 방화벽·NAT 규칙을 만듭니다. 일부 호스트 방화벽 도구의 단순 규칙만 보고 게시된 포트가 차단됐다고 가정하면 안 됩니다.

검증은 외부 위치에서도 수행합니다.

```sh
ss -lntp
# 다른 호스트에서
curl -I https://service.example
```

Docker의 방화벽 규칙 생성을 무작정 끄지 않습니다. 공식 문서는 이 설정을 끄면 컨테이너 네트워킹이 깨질 수 있음을 경고합니다. 추가 필터가 필요하다면 사용하는 iptables 또는 nftables 백엔드와 Docker가 제공하는 필터 지점을 정확히 확인합니다.

### 5.2 IPv6

A 레코드만 확인하고 AAAA 레코드와 IPv6 수신 소켓를 놓치면 프로토콜에 따라 서로 다른 경로가 노출될 수 있습니다.

- DNS에 AAAA가 있는가?
- 호스트 방화벽이 IPv6에도 적용되는가?
- 게이트웨이가 IPv6에서 수신하는가?
- 외부 검사에서 IPv4·IPv6가 모두 같은 인증서와 애플리케이션을 제공하는가?

IPv6를 사용하지 않는다면 DNS와 호스트 양쪽에서 그 결정을 일관되게 적용합니다.

## 6. 운영 파일 경로

소스 체크아웃, 설정, 데이터, 비밀값, 백업을 한 디렉터리에 섞지 않습니다. 한 가지 예는 다음과 같습니다.

```text
/srv/example/
  compose.yaml
  releases/
  current-release.json

/etc/example/
  public.env
  secrets/

/var/lib/example/
  # host bind mount를 사용하는 경우의 영속 데이터

/var/backups/example/
  # 외부 전송 전 임시 staging만 허용

/var/log/example/
  # host에 별도 저장할 때
```

Compose named volume을 사용한다면 실제 Docker 데이터 루트 안의 경로를 애플리케이션이 직접 조작하지 않습니다. 백업은 데이터베이스가 제공하는 일관된 덤프 또는 스냅샷 절차를 사용합니다.

권한 원칙:

- 공개 설정은 필요한 주체만 읽을 수 있게 합니다.
- 비밀값 디렉터리는 최소 사용자·그룹만 읽습니다.
- 애플리케이션이 릴리스 파일을 수정하지 못하게 합니다.
- 백업 스테이징과 암호화 키의 쓰기·읽기 주체를 분리합니다.

## 7. Docker Compose를 systemd로 관리할 때

호스트 부팅 뒤 스택을 자동으로 시작하려면 systemd 유닛을 사용할 수 있습니다. 다음 예시는 기본 계약을 보여 줍니다.

```ini
[Unit]
Description=Example web stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/srv/example
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

이 예를 그대로 복사하기 전에 다음을 결정합니다.

- `down`이 운영 중 볼륨이나 네트워크에 어떤 영향을 주는가?
- Docker daemon 자체의 재시작 정책과 Compose `restart` 정책은 무엇인가?
- 부팅 시 레지스트리 인증이 필요한가?
- 마이그레이션은 자동 시작과 분리되어 있는가?
- 유닛 실행 사용자는 누구인가?
- 경로와 환경 파일 권한은 올바른가?

`systemctl start`가 성공했다고 애플리케이션이 준비된 것은 아닙니다. 유닛 상태, Compose 상태, 외부 스모크 테스트를 각각 확인합니다.

## 8. 컨테이너 실행 권한 줄이기

가능한 서비스에는 다음 설정을 검토합니다.

```yaml
services:
  app:
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    pids_limit: 200
```

이 설정은 애플리케이션이 실제로 필요한 쓰기 경로와 capability를 알고 있을 때 적용합니다. 무작정 추가한 뒤 오류가 나면 전부 제거하는 방식으로는 권한 모델을 만들 수 없습니다.

다음 순서로 적용합니다.

1. 현재 쓰기 경로와 Linux capability 사용을 관찰합니다.
2. 임시 쓰기와 영속 쓰기를 구분합니다.
3. 한 항목씩 제한합니다.
4. 정상·실패 경로를 모두 검사합니다.
5. 왜 남긴 권한인지 기록합니다.

Docker의 기본 seccomp와 AppArmor 또는 SELinux 정책도 호스트 보안 경계의 일부입니다. 비활성화가 필요한 경우 원인과 대체 통제를 문서화합니다.

## 9. 업데이트와 재부팅

보안 업데이트를 적용하지 않는 호스트는 시간이 지날수록 위험이 커집니다. 반대로 자동 업데이트와 재부팅을 아무 검증 없이 적용하면 서비스 중단을 만들 수 있습니다.

운영 계약에 다음을 정합니다.

- 보안 업데이트 확인 주기
- 자동 적용 범위
- 커널·Docker 업데이트 뒤 재부팅 창
- 재부팅 전 백업·상태 확인
- 재부팅 뒤 Compose 시작과 스모크 테스트
- 실패 시 공급자 콘솔 또는 이전 스냅샷 사용 조건

재부팅을 두려워해 영원히 미루지 않습니다. 정기적인 계획 재부팅은 “호스트가 다시 시작돼도 서비스가 복구되는가?”를 검증하는 운영 시험입니다.

## 10. 시간, 로그와 디스크

### 시간 동기화

TLS 검증, 로그 순서, 토큰 만료, 인증서 갱신은 정확한 시간에 의존합니다.

```sh
timedatectl status 2>/dev/null || true
```

시간 동기화 실패를 관찰할 방법을 둡니다.

### 디스크와 inode

```sh
df -h
df -i
docker system df
```

다음 항목이 계속 증가할 수 있습니다.

- 컨테이너 로그
- 이미지와 빌드 캐시
- 데이터베이스 볼륨
- 백업 스테이징
- 코어 덤프
- 임시 업로드

자동 `docker system prune -a`를 운영 cron에 넣지 않습니다. 사용 중이지 않다는 판정을 잘못하면 롤백에 필요한 이미지까지 지울 수 있습니다. 보존 정책과 삭제 대상을 명시합니다.

### 로그 보존

Docker 로깅 드라이버와 로그 순환 설정을 확인합니다. 무제한 JSON 로그는 호스트 디스크를 채울 수 있습니다. 애플리케이션 로그 보존과 운영 감사 로그 보존은 목적이 다르므로 분리합니다.

## 11. 호스트 감사 증거

최소한 다음을 정기적으로 수집합니다.

```text
OS·kernel 버전
보안 업데이트 상태
관리 사용자와 SSH 키 소유자
sudo·docker 그룹 구성원
열린 TCP/UDP 포트
Docker 데몬 소켓과 원격 수신 주소
Docker·Compose 버전
firewall backend와 적용 규칙
filesystem·inode 사용률
시간 동기화 상태
실패한 systemd 유닛
최근 재부팅과 배포 시각
```

민감한 설정과 실제 비밀값 내용은 보고서에 포함하지 않습니다.

## 12. 실습

[`exercises/09-host-hardening`](../exercises/09-host-hardening/)은 두 호스트 스냅샷을 제공합니다.

- `secure.json`: 기준선을 만족하는 예
- `insecure.json`: Docker socket 원격 공개, 과도한 공개 포트, 공유 SSH 키, 비활성 시간 동기화 등 의도적인 결함 포함

저장소 루트에서 `python3 scripts/new-workspace.py exercises/09-host-hardening`을 실행한 뒤 학습자는 `workspace/audit.py`를 완성해 다음을 수행합니다.

1. 구조화된 점검 결과를 출력합니다.
2. 심각도와 영향을 구분합니다.
3. 증거가 없는 항목을 추측하지 않습니다.
4. 안전한 수정 순서를 제시합니다.
5. 잠금 사고나 네트워크 단절을 만들 수 있는 변경은 사전 검증을 요구합니다.

실제 호스트를 자동으로 고치는 스크립트보다 먼저 상태를 정확히 판정하는 감사를 학습합니다.

## 13. 공식 확인 자료

- Docker Engine security: <https://docs.docker.com/engine/security/>
- Docker rootless mode: <https://docs.docker.com/engine/security/rootless/>
- Protect the Docker daemon socket: <https://docs.docker.com/engine/security/protect-access/>
- Docker packet filtering and firewalls: <https://docs.docker.com/engine/network/packet-filtering-firewalls/>
- Docker default seccomp profile: <https://docs.docker.com/engine/security/seccomp/>
- Docker AppArmor: <https://docs.docker.com/engine/security/apparmor/>

다음 장에서는 공개 이름을 호스트에 연결하고 자동 갱신 가능한 공인 TLS 경계를 만듭니다.
