# Linux 라우팅·NAT·손실 실습

세 개의 Linux 네트워크 네임스페이스를 veth로 연결해 클라이언트, 라우터와 서버를 한 호스트 안에 격리합니다. 실제 외부 인터페이스, 호스트 방화벽과 기본 경로는 변경하지 않으며 각 실행이 끝나면 네임스페이스를 삭제합니다.

## 목표

고유한 격리 namespace 안에서 TTL, route, SNAT와 반복 SYN을 실제 packet 증거로 재현하고 실행이 소유한 자원만 정리합니다.

```text
클라이언트 c0 ── r0 라우터 r1 ── s0 서버
```

## 요구 환경

다음 조건이 모두 필요합니다.

- Linux와 관리자 권한
- `iproute2`의 `ip`, `tc`
- `ping`, `sysctl`, Python 3
- NAT 실습용 `iptables`
- 재전송 관찰용 `tcpdump`

Ubuntu 계열에서는 다음 패키지로 준비할 수 있습니다.

```sh
sudo apt-get update
sudo apt-get install -y iproute2 iputils-ping iptables tcpdump
```

실습 전 권한과 명령을 확인합니다.

```sh
sudo ./scripts/preflight.sh all
```

## 1. 라우팅과 TTL

```sh
sudo ./scripts/run-routing.sh
```

스크립트는 서로 다른 두 subnet을 연결하고 다음 조건을 검사합니다.

1. 라우터의 IPv4 forwarding을 켜면 양 끝 호스트가 통신합니다.
2. TTL 1인 패킷은 한 홉인 라우터에서 만료됩니다.
3. 클라이언트의 기본 경로를 제거하면 다른 subnet에 도달하지 못합니다.
4. 기본 경로를 복구하면 다시 통신합니다.

## 2. SNAT와 역변환

```sh
sudo ./scripts/run-nat.sh
```

클라이언트는 사설 주소 `10.202.1.2`를 사용하고 서버는 직접 연결된 시험용 대역 `198.18.0.0/24`에 있습니다. 라우터가 SNAT를 적용하면 서버는 요청 출발지를 라우터의 외부 주소 `198.18.0.1`로 관찰합니다. 응답은 연결 추적 상태를 이용해 원래 클라이언트로 역변환됩니다.

이 실습의 NAT 규칙은 주소 변환만 확인합니다. 필터 테이블의 허용·차단 정책은 별도 문제이므로 NAT가 방화벽을 대신한다고 해석하지 않습니다.

## 3. SYN 손실과 재전송

```sh
sudo ./scripts/run-loss-retransmission.sh
```

라우터의 서버 방향 인터페이스에 `netem loss 100%`를 잠시 적용합니다. 클라이언트에서 나간 같은 SYN이 다시 관찰되면 손실 규칙을 제거하고, 다음 재전송으로 연결이 완료되는지 확인합니다.

손실률을 무작위 값으로 두지 않고 첫 구간을 전부 버리므로 검사가 결정적입니다. 실제 네트워크의 재전송 원인은 혼잡, 링크 손실, 방화벽 정책, 경로 변경처럼 다양하므로 이 실험 결과를 일반화하지 마세요.

## 완료 기준

- TTL 1은 router에서 만료되고 TTL 2는 server에 도달하는 차이를 관찰합니다.
- server가 SNAT 뒤 router 외부 주소를 보고 응답이 원래 client로 돌아오는지 확인합니다.
- 첫 SYN을 100% 손실시킨 뒤 반복 SYN과 연결 복구를 같은 capture에서 확인합니다.
- 정상·실패·signal 종료 뒤 이번 실행이 만든 namespace, interface와 process가 남지 않습니다.

## 자기 설명

- NAT mapping이 존재한다는 사실과 firewall이 packet을 허용한다는 사실은 왜 다른가요?
- 고정 100% 손실 구간을 사용하는 것이 무작위 손실률보다 재현성에 유리한 이유는 무엇인가요?
- 다른 실행의 namespace가 보일 때 자동 삭제하지 않아야 하는 이유는 무엇인가요?

## 검증

```sh
sudo ./scripts/run-all.sh
```

모든 스크립트는 `EXIT`, `HUP`, `INT`, `TERM`에서 정리 함수를 실행합니다. 비정상 종료 뒤 namespace가 남았다면 출력에 기록된 실행별 suffix와 소유자를 먼저 확인합니다. 다른 실행이 사용 중인 자원은 삭제하지 않습니다.

```sh
sudo ip netns list
sudo ip link show type veth
```

회사 장비나 원격 서버에서 직접 실행하지 않습니다. 정본 `verify.sh`는 digest로 고정한 privileged Linux container에서 이 실습을 필수 실행하고 `--pull=never`로 검증 중 network fetch를 막습니다. 스크립트는 실행별 고유 이름을 사용하고 소유권을 기록해 다른 실행의 namespace와 interface를 삭제하지 않아야 합니다.
