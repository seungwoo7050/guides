# Linux 호스트 준비와 강화

공개 서비스의 가장 바깥 신뢰 경계는 컨테이너가 아니라 호스트입니다. 호스트의 관리자 계정, SSH, 방화벽, Docker daemon과 디스크가 손상되면 내부 컨테이너 분리는 충분한 보호가 되지 못합니다.

이 장의 목표는 특정 배포판의 명령을 전부 외우는 것이 아닙니다. 다음 계약을 만족하는 호스트를 반복해서 준비하는 것입니다.

```text
관리 경로는 제한되고 검증됨
공개 포트는 의도적으로 열림
Docker daemon 접근 주체가 명확함
운영 파일과 영속 데이터 경로가 분리됨
시간·디스크·업데이트 상태를 관찰할 수 있음
호스트를 버리고 다시 만들 수 있음
```

대응 실습은 [`exercises/09-host-hardening`](../exercises/09-host-hardening/)입니다. 실습은 실제 호스트 설정을 변경하지 않고 안전한 snapshot을 감사합니다.

## 1. 재현 가능한 호스트 기준선

서버를 수동으로 오래 수정할수록 새 호스트에서 동일한 상태를 재현하기 어려워집니다. 처음부터 다음 정보를 기록합니다.

- 공급자와 region
- 배포판과 정확한 버전
- CPU, 메모리와 디스크 크기
- 네트워크 주소와 공개 IP
- 설치한 Docker Engine·Compose 버전
- 호스트 사용자와 그룹
- 열린 포트
- `/srv`, `/etc`, `/var/lib`, `/var/backups` 아래의 운영 경로
- 적용한 보안 업데이트 시점
- provisioning 절차의 원본 위치

명령 기록만으로 충분하지 않습니다. 각 단계 뒤의 검증 결과를 함께 남깁니다.

## 2. 호스트를 처음 받을 때

공급자 console 또는 임시 관리자 접근으로 다음을 확인합니다.

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

1. 기대한 배포판과 architecture인가?
2. root filesystem과 데이터 disk는 어디인가?
3. IPv4와 IPv6가 모두 활성화되어 있는가?
4. 기본 route와 DNS 해석이 되는가?
5. disk뿐 아니라 inode 여유가 있는가?
6. 공급자 snapshot이나 console 복구 경로가 있는가?

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

가장 중요한 순서는 **제한하기 전에 새 경로를 검증하는 것**입니다. 현재 SSH 세션 하나만 믿고 설정을 바꾸면 서버에서 잠길 수 있습니다.

### 3.2 공개키 인증

- 각 운영자마다 별도 키를 사용합니다.
- 개인키는 서버에 복사하지 않습니다.
- 공유 계정 하나에 여러 사람이 같은 개인키를 사용하지 않습니다.
- 오래된 키를 제거할 소유자와 절차를 정합니다.
- 키에 가능한 경우 passphrase를 사용합니다.

SSH 설정은 배포판과 버전에 따라 파일 위치와 기본값이 다를 수 있습니다. 변경 전 다음을 수행합니다.

```sh
sshd -T
sudo sshd -t
```

`sshd -t`가 성공해도 실제 로그인 정책이 의도와 같다는 뜻은 아닙니다. 별도 터미널에서 새 연결을 확인합니다.

### 3.3 관리 포트 변경의 의미

SSH 포트를 22가 아닌 값으로 바꾸면 자동 스캔 로그는 줄 수 있지만 인증과 권한 통제를 대체하지 않습니다. 다음이 우선입니다.

- 키 기반 인증
- 불필요한 사용자 로그인 제한
- 공급자 firewall 또는 host firewall
- 실패·성공 로그인 관찰
- 키 폐기 절차

## 4. 최소 권한과 Docker daemon

Docker daemon은 호스트에서 강한 권한을 가집니다. daemon socket에 접근할 수 있는 주체는 컨테이너 생성, host path mount와 privileged 옵션 등을 통해 호스트 전체에 영향을 줄 수 있습니다.

따라서 다음을 명시합니다.

- 누가 `docker` 명령을 실행할 수 있는가?
- 애플리케이션 컨테이너가 `/var/run/docker.sock`을 mount하는가?
- CI runner가 production Docker daemon에 직접 접근하는가?
- 원격 daemon API가 열려 있는가?
- socket proxy를 사용한다면 실제로 어떤 API를 허용하는가?

### 4.1 `docker` 그룹

일반적인 rootful Docker 설치에서 `docker` 그룹 접근은 단순한 “컨테이너 관리 권한”보다 강합니다. 이 그룹 구성원을 관리자와 같은 신뢰 수준으로 다룹니다.

```sh
getent group docker || true
find /var/run -maxdepth 1 -name 'docker.sock' -ls 2>/dev/null || true
```

애플리케이션 사용자와 웹 컨테이너에 socket 접근을 주지 않습니다.

### 4.2 Rootless mode

Rootless mode는 daemon과 컨테이너를 일반 사용자 namespace 안에서 실행해 rootful daemon의 위험을 줄이는 선택지입니다. 그러나 모든 환경에서 자동으로 더 단순하거나 완전히 격리되는 것은 아닙니다.

검토할 항목:

- 낮은 포트 binding 방식
- cgroup과 resource limit 지원
- storage driver
- 네트워크 성능과 기능
- systemd user service의 시작 정책
- 운영 사용자의 linger와 세션 수명
- 백업해야 할 rootless data root

이 과정의 실습은 rootful과 rootless 중 하나를 강제하지 않습니다. 선택과 잔여 위험을 운영 계약에 기록합니다.

### 4.3 원격 daemon

인증되지 않은 TCP socket으로 Docker daemon을 공개하지 않습니다. 원격 관리가 필요하면 공식 문서가 설명하는 SSH 또는 상호 TLS 보호 방식을 사용하고, 네트워크 노출과 인증 주체를 별도로 제한합니다.

## 5. 공개 포트와 방화벽

운영 기준선에서 외부에 필요한 포트는 보통 다음뿐입니다.

```text
80/tcp   ACME HTTP-01과 HTTPS redirect
443/tcp  공개 HTTPS
관리 경로 SSH  제한된 출발지 또는 별도 관리망
```

데이터베이스, FastCGI, application runtime과 monitoring admin port는 인터넷에 직접 게시하지 않습니다.

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

관리용 dashboard가 필요하면 다음 중 하나를 사용합니다.

- `127.0.0.1`에만 bind하고 SSH tunnel 사용
- 인증된 VPN 또는 관리망
- 별도의 강한 인증 gateway

### 5.1 Docker와 host firewall의 상호작용

Docker는 Linux에서 bridge network와 port publishing을 위해 firewall·NAT 규칙을 만듭니다. 일부 host firewall 도구의 단순 규칙만 보고 published port가 차단됐다고 가정하면 안 됩니다.

검증은 외부 위치에서 수행합니다.

```sh
ss -lntp
# 다른 호스트에서
curl -I https://service.example
```

Docker의 firewall rule 생성을 무작정 끄지 않습니다. 공식 문서는 대부분의 사용자에게 이 설정이 container networking을 깨뜨릴 수 있다고 경고합니다. 추가 필터가 필요하면 사용 중인 iptables 또는 nftables backend와 Docker가 제공하는 삽입 지점을 정확히 확인합니다.

### 5.2 IPv6

A record만 확인하고 AAAA record와 IPv6 listener를 놓치면 한 프로토콜에서는 보호가 다르게 적용될 수 있습니다.

- DNS에 AAAA가 있는가?
- host firewall이 IPv6도 적용하는가?
- gateway가 IPv6에서 listen하는가?
- 외부 검사에서 IPv4·IPv6가 모두 같은 인증서와 애플리케이션을 제공하는가?

IPv6를 사용하지 않는다면 DNS와 호스트 양쪽에서 그 결정을 일관되게 적용합니다.

## 6. 운영 파일 경로

소스 checkout, 설정, 데이터, 비밀값과 백업을 한 디렉터리에 섞지 않습니다. 한 가지 예는 다음과 같습니다.

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

Compose named volume을 사용한다면 실제 Docker data root 안의 경로를 애플리케이션이 직접 조작하지 않습니다. backup은 데이터베이스가 제공하는 일관된 dump 또는 snapshot 절차를 사용합니다.

권한 원칙:

- 공개 설정은 읽을 주체만 허용합니다.
- secret 디렉터리는 최소 사용자·그룹만 읽습니다.
- 애플리케이션이 release 파일을 수정하지 못하게 합니다.
- backup staging과 암호화 키의 쓰기·읽기 주체를 분리합니다.

## 7. Docker Compose를 systemd로 관리할 때

호스트 부팅 뒤 스택을 자동 시작하려면 systemd unit을 사용할 수 있습니다. 예시는 다음 계약을 보여 줍니다.

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

- `down`이 운영 중 volume이나 network에 어떤 영향을 주는가?
- Docker daemon 자체의 restart policy와 Compose `restart` 정책은 무엇인가?
- 부팅 시 registry 인증이 필요한가?
- migration은 자동 시작과 분리되어 있는가?
- unit 실행 사용자는 누구인가?
- 경로와 환경 파일 권한은 올바른가?

`systemctl start`가 성공했다고 애플리케이션이 준비된 것은 아닙니다. unit 상태, Compose 상태와 외부 smoke test를 각각 확인합니다.

## 8. 컨테이너 실행 권한 줄이기

가능한 서비스에는 다음을 검토합니다.

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

이 설정은 애플리케이션이 실제로 필요한 쓰기 경로와 capability를 알고 있을 때 적용합니다. 무작정 추가한 뒤 오류가 나면 전부 제거하는 방식은 권한 모델을 만들지 못합니다.

다음 순서가 좋습니다.

1. 현재 쓰기 경로와 capability 사용을 관찰합니다.
2. 임시 쓰기와 영속 쓰기를 구분합니다.
3. 한 항목씩 제한합니다.
4. 정상·실패 경로를 모두 검사합니다.
5. 왜 남긴 권한인지 기록합니다.

Docker의 기본 seccomp와 AppArmor 또는 SELinux 정책도 host 보안 경계의 일부입니다. 비활성화가 필요한 경우 원인과 대체 통제를 문서화합니다.

## 9. 업데이트와 재부팅

보안 업데이트를 적용하지 않는 호스트는 시간이 지날수록 위험이 커집니다. 반대로 자동 업데이트와 재부팅을 아무 검증 없이 적용하면 서비스 중단을 만들 수 있습니다.

운영 계약에 다음을 정합니다.

- 보안 업데이트 확인 주기
- 자동 적용 범위
- kernel·Docker 업데이트 뒤 재부팅 창
- 재부팅 전 backup·상태 확인
- 재부팅 뒤 Compose 시작과 smoke test
- 실패 시 공급자 console 또는 이전 snapshot 사용 조건

재부팅을 두려워해 영원히 미루지 않습니다. 정기적인 계획 재부팅은 “호스트가 다시 시작돼도 서비스가 복구되는가?”를 검증하는 운영 시험입니다.

## 10. 시간, 로그와 디스크

### 시간 동기화

TLS 검증, 로그 순서, token 만료와 인증서 갱신은 정확한 시간에 의존합니다.

```sh
timedatectl status 2>/dev/null || true
```

시간 동기화 실패를 관찰할 방법을 둡니다.

### disk와 inode

```sh
df -h
df -i
docker system df
```

다음이 자랄 수 있습니다.

- container logs
- image와 build cache
- database volume
- backup staging
- core dump
- 임시 업로드

자동 `docker system prune -a`를 운영 cron에 넣지 않습니다. 사용 중이지 않다는 판정을 잘못하면 rollback에 필요한 image까지 지울 수 있습니다. 보존 정책과 삭제 대상을 명시합니다.

### 로그 보존

Docker logging driver와 rotation을 확인합니다. 무제한 JSON log는 host disk를 채울 수 있습니다. 애플리케이션 로그 보존과 운영 감사 로그 보존은 목적이 다르므로 분리합니다.

## 11. 호스트 감사 증거

최소한 다음을 정기적으로 수집합니다.

```text
OS·kernel 버전
보안 업데이트 상태
관리 사용자와 SSH 키 소유자
sudo·docker 그룹 구성원
열린 TCP/UDP 포트
Docker daemon socket과 원격 listener
Docker·Compose 버전
firewall backend와 적용 규칙
filesystem·inode 사용률
시간 동기화 상태
실패한 systemd unit
최근 재부팅과 배포 시각
```

민감한 설정과 실제 secret 내용은 보고서에 포함하지 않습니다.

## 12. 실습

[`exercises/09-host-hardening`](../exercises/09-host-hardening/)은 두 호스트 snapshot을 제공합니다.

- `secure.json`: 기준선을 만족하는 예
- `insecure.json`: Docker socket 원격 공개, 과도한 공개 포트, 공유 SSH 키, 비활성 시간 동기화 등 의도적 결함 포함

학습자는 `skeleton/audit.py`를 완성해 다음을 수행합니다.

1. 구조화된 finding을 출력합니다.
2. 심각도와 영향을 구분합니다.
3. 증거가 없는 항목을 추측하지 않습니다.
4. 안전한 수정 순서를 제시합니다.
5. 잠금 사고나 네트워크 단절을 만들 수 있는 변경은 사전 검증을 요구합니다.

실제 호스트를 자동으로 고치는 스크립트보다, 먼저 상태를 정확히 판정하는 감사를 학습합니다.

## 13. 공식 확인 자료

- Docker Engine security: <https://docs.docker.com/engine/security/>
- Docker rootless mode: <https://docs.docker.com/engine/security/rootless/>
- Protect the Docker daemon socket: <https://docs.docker.com/engine/security/protect-access/>
- Docker packet filtering and firewalls: <https://docs.docker.com/engine/network/packet-filtering-firewalls/>
- Docker default seccomp profile: <https://docs.docker.com/engine/security/seccomp/>
- Docker AppArmor: <https://docs.docker.com/engine/security/apparmor/>

다음 장에서는 공개 이름을 호스트에 연결하고, 자동 갱신 가능한 공인 TLS 경계를 만듭니다.
