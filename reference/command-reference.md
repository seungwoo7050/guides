# 네트워크 관찰 명령 빠른 참조

명령은 상태를 바꾸기 전에 읽기 전용 관찰부터 사용합니다. Linux의 `iproute2`와 macOS의 BSD 계열 도구는 option과 출력이 다르므로 현재 시스템의 `man` page를 함께 확인하세요.

## 인터페이스와 주소

Linux:

```sh
ip -details link show
ip address show
ip -6 address show
```

macOS:

```sh
ifconfig
networksetup -listallhardwareports
```

확인할 값은 인터페이스 상태, MTU, MAC 주소, IPv4·IPv6 주소와 범위입니다.

## 경로와 다음 홉

Linux:

```sh
ip route show table all
ip -6 route show table all
ip route get 203.0.113.10
ip -6 route get 2001:db8::10
ip rule show
```

macOS:

```sh
netstat -rn
route -n get 203.0.113.10
route -n get -inet6 2001:db8::10
```

특정 목적지의 실제 선택 결과를 볼 때는 전체 테이블 출력보다 `route get` 질의를 우선합니다.

## ARP와 Neighbor Discovery

Linux:

```sh
ip neighbor show
ip -6 neighbor show
```

macOS:

```sh
arp -an
ndp -an
```

캐시 삭제는 다른 연결에 영향을 줄 수 있으므로 격리된 실습 환경에서만 실행합니다.

## socket과 연결 상태

Linux:

```sh
ss -lntup
ss -tan state established
ss -ti dst 203.0.113.10
```

macOS:

```sh
netstat -anv
lsof -nP -iTCP -sTCP:LISTEN
```

수신 대기 소켓과 연결된 소켓을 구분하고 로컬·원격 튜플, 프로세스 소유권과 TCP 상태를 함께 확인합니다.

## DNS

```sh
dig example.com A
dig example.com AAAA
dig example.com HTTPS
dig +trace example.com
```

`+trace`는 현재 재귀 이름 해석기의 실제 내부 동작을 그대로 보여 주는 명령이 아니라 클라이언트가 반복 질의를 수행하는 별도 실험입니다. 이름 해석기 캐시와 분할 DNS를 조사할 때 결과를 혼동하지 않습니다.

macOS의 시스템 이름 해석기 설정은 다음 명령으로 확인할 수 있습니다.

```sh
scutil --dns
```

Linux에서는 배포판에 따라 `/etc/resolv.conf`, `resolvectl status`와 NetworkManager 상태를 확인합니다.

## 패킷 캡처

Linux loopback:

```sh
sudo tcpdump -i lo -nn -tt -vv 'tcp port 443'
```

macOS loopback:

```sh
sudo tcpdump -i lo0 -nn -tt -vv 'tcp port 443'
```

파일 저장과 다시 읽기:

```sh
sudo tcpdump -i any -nn -s 0 -w /tmp/capture.pcap 'host 192.0.2.10'
tcpdump -nn -tt -r /tmp/capture.pcap
```

캡처에는 토큰, 쿠키, 내부 주소와 업무 데이터가 들어갈 수 있습니다. 범위와 보관 기간을 제한하고 공개 저장소에 커밋하지 않습니다.

## HTTP와 TLS

```sh
curl -v https://example.com/
curl --connect-timeout 3 --max-time 10 https://example.com/
openssl s_client -connect example.com:443 -servername example.com -alpn h2
```

`curl -v` 출력의 DNS, 연결 주소, TLS, ALPN, HTTP status를 단계별로 읽습니다. `-k` 또는 `--insecure`는 certificate 검증 실패를 숨기므로 원인 조사 결과로 사용하지 않습니다.

## Linux 네임스페이스 실습

```sh
ip netns list
sudo ip netns exec cn-client ip address show
sudo ip netns exec cn-router ip route show
sudo ip netns exec cn-server ss -lntup
```

네임스페이스 안의 명령은 호스트 네임스페이스의 경로와 방화벽 상태를 보여 주지 않습니다. 조사 위치를 기록하세요.

## 손실과 큐

격리 환경에서만 사용합니다.

```sh
sudo ip netns exec cn-router tc qdisc add dev r1 root netem delay 50ms loss 1%
sudo ip netns exec cn-router tc qdisc show dev r1
sudo ip netns exec cn-router tc qdisc del dev r1 root
```

원격 접속 인터페이스에 `tc` 규칙을 적용하면 자신의 연결을 끊을 수 있습니다. 이 저장소의 실습은 veth 네임스페이스 안에서만 규칙을 만듭니다.
