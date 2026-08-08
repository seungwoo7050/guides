# 네트워크 엔드포인트와 연결 진단

서버 프로세스가 존재해도 원하는 주소와 포트에서 수신 대기하지 않으면 연결할 수 없습니다. 이름 해석, 주소 계열, 라우팅, listener, 연결과 애플리케이션 응답을 분리해야 “네트워크가 안 된다”는 증상을 좁힐 수 있습니다.

## 학습 목표

- 인터페이스, 주소, 포트, listener와 연결을 구분합니다.
- `localhost`, `127.0.0.1`, `::1`과 wildcard bind의 차이를 설명합니다.
- 이름 해석 성공과 TCP 연결 성공을 분리합니다.
- connection refused, timeout과 protocol-level failure를 구분합니다.
- 실제 listener와 프로세스 소유자를 확인합니다.
- 애플리케이션 프로토콜 내부로 들어가기 전에 OS 수준 경계를 확인합니다.

## 선행 개념

- process/FD/socket 소유와 hostname·address·port·family 구분

## 연결 경로

```text
클라이언트 입력 이름
  │ name resolution
  ▼
주소 후보와 address family
  │ route와 source interface 선택
  ▼
클라이언트 socket
  │ connect
  ▼
network path / local stack
  │
  ▼
서버 listener(address, port, protocol)
  │ accept
  ▼
서버 connection socket
  │ application protocol
  ▼
응답
```

각 단계의 성공은 다음 단계를 보장하지 않습니다.

## 인터페이스, 주소와 포트

호스트는 여러 인터페이스와 주소를 가질 수 있습니다.

- loopback
- Wi-Fi 또는 Ethernet
- VPN·tunnel
- container·VM 가상 인터페이스
- IPv4와 IPv6 주소

Linux:

```sh
ip address
```

macOS:

```sh
ifconfig
```

출력 전체를 외우기보다 다음을 확인합니다.

```text
인터페이스 이름
up/down 상태
주소 계열
배정된 주소
loopback인지 외부 경로인지
```

포트는 transport protocol과 주소 계열을 포함해 해석합니다.

```text
TCP 127.0.0.1:8080
TCP [::1]:8080
UDP 127.0.0.1:8080
```

같은 숫자라도 다른 엔드포인트입니다.

## Loopback, localhost와 wildcard

### Loopback

- IPv4 대표: `127.0.0.1`
- IPv6: `::1`

같은 호스트 안에서 통신하며 외부 인터페이스로 나가지 않습니다.

### `localhost`

`localhost`는 이름입니다. 환경에 따라 IPv4와 IPv6 주소 후보를 반환할 수 있습니다. 클라이언트가 `::1`을 시도하는데 서버가 `127.0.0.1`에만 바인드했다면 같은 호스트에서도 실패할 수 있습니다.

Python으로 주소 후보 관찰:

```sh
python3 - <<'PY'
import socket
for item in socket.getaddrinfo('localhost', 0, type=socket.SOCK_STREAM):
    print(item[0], item[4])
PY
```

### Wildcard bind

- IPv4 `0.0.0.0`: 사용 가능한 IPv4 local address에 대해 수신
- IPv6 `::`: IPv6 wildcard, IPv4 동시 수신 여부는 플랫폼과 socket option에 따라 다름

wildcard 주소는 일반적인 클라이언트 접속 대상이 아닙니다. 서버의 수신 범위를 나타냅니다. 로컬 전용 서비스는 loopback에 명시적으로 바인드하는 편이 노출 범위를 좁힙니다.

## Listener 확인

프로세스가 실행 중인 사실과 socket이 수신 대기 중인 사실을 분리합니다.

Linux:

```sh
ss -lnt
ss -lntp 2>/dev/null || true
```

macOS:

```sh
lsof -nP -iTCP -sTCP:LISTEN
```

확인할 항목:

- protocol
- address family
- local bind address
- port
- listener owner PID
- expected process identity

권한 때문에 owner 정보가 보이지 않을 수 있습니다. 그 경우 port와 process 정보를 별도 관찰해 연결합니다.

## 이름 해석과 라우팅

### 이름 해석

이름을 주소 후보로 바꾸는 단계입니다. 숫자 주소로는 되지만 이름으로 실패하면 DNS·hosts·search domain·resolver 설정을 의심합니다.

### 라우팅

대상 주소에 어떤 source address, interface와 gateway를 사용할지 결정합니다.

Linux:

```sh
ip route get 127.0.0.1
```

macOS:

```sh
route -n get 127.0.0.1
```

이름 해석이 성공해도 route, firewall, listener나 application이 실패할 수 있습니다.

## 실패 의미 분리

### Connection refused

대상 host가 즉시 거부 응답을 보냈거나 local stack이 listener 부재를 알린 경우가 흔합니다.

확인:

- 정확한 address family와 port
- listener 존재
- server bind address
- server startup failure
- container/host port confusion

### Timeout

응답이 제한 시간 안에 오지 않은 상태입니다. 처리되지 않았다는 뜻은 아닙니다.

가능성:

- packet drop 또는 firewall
- route 문제
- server overload
- application이 accept했지만 응답하지 않음
- 응답 경로 문제

timeout 뒤 같은 요청을 무조건 재전송하면 중복 효과가 생길 수 있습니다. 업무 요청의 멱등성은 `guide-web-applications`와 `guide-distributed-services`가 더 깊게 다룹니다.

### 연결 성공 후 protocol failure

TCP 연결은 성공했지만 다음이 실패할 수 있습니다.

- TLS handshake
- HTTP status
- authentication
- application framing
- response validation

OS 수준 연결과 애플리케이션 성공을 구분합니다.

## 주소 계열 불일치

대표 상황:

```text
server listener: IPv4 127.0.0.1:PORT
client target:   IPv6 [::1]:PORT
```

프로세스와 port 숫자만 보면 정상처럼 보이지만 실제 endpoint는 다릅니다.

진단 순서:

```text
1. client가 사용한 정확한 이름과 주소를 기록합니다.
2. 이름 해석 결과의 순서와 address family를 확인합니다.
3. listener의 address family와 bind address를 확인합니다.
4. 숫자 IPv4와 숫자 IPv6를 각각 시험합니다.
5. server가 의도한 노출 범위에 맞게 bind를 수정합니다.
6. 새 connection과 기존 경로를 회귀 검사합니다.
```

## Container와 host 경계

이 가이드는 container 구성 자체를 가르치지 않지만 진단에서는 범위를 구분해야 합니다.

```text
host localhost
≠ container localhost

container internal port
≠ host published port
```

어느 namespace에서 관찰한 주소·listener인지 기록합니다. Docker·Compose·port publishing은 `guide-web-infrastructure`가 담당합니다.

## 안전한 관찰 순서

```text
1. 정확한 client target(name/address/port/protocol)을 기록합니다.
2. 이름을 주소 후보로 해석합니다.
3. 선택된 address family와 route를 확인합니다.
4. 서버가 실제로 어느 endpoint에서 listen하는지 확인합니다.
5. listener owner가 예상 프로세스인지 확인합니다.
6. TCP 연결과 application request를 분리해 시험합니다.
7. firewall·container·proxy 경계를 한 단계씩 추가합니다.
```

외부 대상에 무단 scan을 수행하지 않습니다. 실습은 loopback과 OS가 배정한 임시 port만 사용합니다.

## 실습 연결

- `06-address-family-mismatch`: IPv4 listener에 IPv6 loopback으로 연결해 실패 계층을 확인합니다.
- `07-running-not-ready`: TCP listener는 존재하지만 health 요청이 실패하는 다음 계층을 확인합니다.

[시스템 조사 실습](../../exercises/system-investigation/README.md)

## 연결 실습

- [사례 06과 07](../../exercises/system-investigation/README.md)에서 IPv4/IPv6 불일치와 running/not-ready를 분리합니다.

## 완료 기준

- `localhost`와 `127.0.0.1`을 같은 문자열처럼 취급하면 안 되는 이유를 설명할 수 있습니다.
- listener와 accepted connection을 구분할 수 있습니다.
- connection refused와 timeout이 주는 단서 차이를 설명할 수 있습니다.
- TCP 연결 성공이 애플리케이션 정상 상태를 보장하지 않는 이유를 설명할 수 있습니다.
- container와 host의 loopback 범위를 구분할 수 있습니다.

다음 문서: [서비스 감독, 로그와 준비 상태](../03-services-and-troubleshooting/01-service-supervision-logs-and-readiness.md)
