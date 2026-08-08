# 네트워크 실습 안전 수칙

패킷 캡처, 경로, 방화벽과 트래픽 제어 명령은 다른 사용자의 통신과 원격 접속을 끊을 수 있습니다. 이 저장소의 자동 실험은 루프백 또는 별도 Linux 네트워크 네임스페이스만 사용하도록 구성했습니다.

## 실행 전 확인

```sh
pwd
id
uname -a
ip netns list 2>/dev/null || true
```

현재 디렉터리, 권한, 운영체제와 이미 존재하는 네임스페이스를 확인합니다. `cn-client`, `cn-router`, `cn-server` 또는 `cnc0`, `cnr0`, `cnr1`, `cns0` 이름이 이미 있으면 스크립트는 덮어쓰지 않고 중단합니다. 이전 실습의 잔여물인지 확인하지 않은 채 삭제하지 않습니다.

## 실제 interface를 변경하지 않기

다음 작업은 문서를 이해하지 못한 상태에서 host의 기본 interface에 실행하지 않습니다.

- 기본 경로 삭제
- 전체 이웃 캐시 삭제
- 호스트 방화벽 기본 정책 변경
- 원격 접속 interface에 `tc netem` 추가
- 모든 ICMP 차단
- 인터페이스 MTU 임의 축소

실습 스크립트는 veth 인터페이스 `c0`, `r0`, `r1`, `s0`만 변경합니다.

## 캡처 데이터 보호

pcap과 text capture에는 다음 정보가 들어갈 수 있습니다.

- 내부 IP와 service 이름
- HTTP header와 cookie
- DNS 질의
- 인증 토큰과 평문 프로토콜 페이로드
- 통신 시간과 사용자 행동

필터로 범위를 줄이고, 필요한 시간만 캡처하고, 저장 위치의 권한을 제한합니다. 분석 뒤 불필요한 파일은 삭제하고 공개 issue나 저장소에 원본을 첨부하지 않습니다.

## 관리자 권한 스크립트 검토

`sudo`로 실행하기 전에 다음을 확인합니다.

```sh
sed -n '1,240p' scripts/run-all.sh
for file in scripts/*.sh; do sh -n "$file"; done
```

스크립트가 만드는 네임스페이스, 경로, NAT와 정리 트랩을 확인합니다. 출처를 모르는 셸 스크립트를 관리자 권한으로 실행하지 않습니다.

## 비정상 종료 뒤 정리

```sh
sudo ip netns del cn-client 2>/dev/null || true
sudo ip netns del cn-router 2>/dev/null || true
sudo ip netns del cn-server 2>/dev/null || true
```

호스트에 veth가 남았으면 피어 한쪽을 삭제할 때 쌍도 함께 제거되는지 확인합니다.

```sh
sudo ip link del cnc0 2>/dev/null || true
sudo ip link del cnr0 2>/dev/null || true
sudo ip link del cnr1 2>/dev/null || true
sudo ip link del cns0 2>/dev/null || true
```

정리 뒤 호스트 경로와 방화벽이 변경되지 않았는지 확인합니다.

## 권장 실행 위치

개인 Linux VM 또는 일회성 CI 실행기를 권장합니다. 회사 VPN, 운영 서버, 공유 개발 호스트와 원격 SSH의 유일한 경로에서는 권한이 필요한 실습을 실행하지 마세요.
