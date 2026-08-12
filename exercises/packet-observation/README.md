# 패킷 관찰과 재전송 판별 실습

루프백 TCP 연결을 `tcpdump`로 캡처하고 SYN, SYN/ACK, ACK의 방향과 순서 번호를 읽습니다. 권한이나 캡처 도구가 없는 환경에서도 분석 규칙을 검증할 수 있도록 결정적인 텍스트 기준 입력을 함께 제공합니다.

## 목표

TCP handshake와 반복 SYN의 관찰 근거를 추출하되, 캡처 중복과 offload 가능성을 남겨 재전송 원인을 과장하지 않습니다.

## 권장 구현 순서

아래 번호는 analyzer와 loopback capture를 합친 이 관찰 실습 전체의 학습 지향 권장 구현 순서입니다. 파일의 줄 순서나 실제 과거 작성 순서를 뜻하지 않으며, 제공된 source를 읽을 때 책임과 resource 수명을 따라가기 위한 index입니다.

| 번호 | 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 1 | `analyze_tcpdump.py` packet grammar | 지원하는 tcpdump text 경계 |
| 1-1 | `analyze_tcpdump.py::Packet.signature` | 재전송 후보를 비교하는 동등성 key |
| 1-2 | `analyze_tcpdump.py::parse_line`, `parse_trace` | text를 typed observation으로 정규화 |
| 2 | `analyze_tcpdump.py::handshake_complete` | SYN, SYN/ACK, ACK의 방향·sequence 관계 |
| 3 | `analyze_tcpdump.py::retransmission_candidates` | 반복 관찰과 확정 원인의 분리 |
| 4 | `analyze_tcpdump.py::analyze` | packet, handshake와 candidate report 조립 |
| 4-1 | `analyze_tcpdump.py::main` | fixture path와 JSON 출력 경계 |
| 5 | `capture-loopback.sh` 설정 | interface, port, output과 소유 resource |
| 5-1 | `capture-loopback.sh::cleanup` | 자신이 시작한 process와 temporary log 정리 |
| 5-2 | `capture-loopback.sh` capture lifecycle | server → capture → request → analyzer 순서 |

## 휴대 가능한 분석 검사

다음 명령은 정상 핸드셰이크와 반복 SYN fixture를 분석합니다.

```sh
python3 scripts/analyze_tcpdump.py fixtures/handshake.txt
python3 scripts/analyze_tcpdump.py fixtures/retransmission.txt
python3 -m unittest discover -s tests -v
```

핸드셰이크는 방향뿐 아니라 SYN이 소비한 순서 번호 1을 SYN/ACK와 마지막 ACK가 올바르게 확인하는지 검사합니다. 동일한 방향, 플래그와 순서 번호 범위가 다시 나타나면 재전송 **후보**로 표시합니다. 실제 캡처에서는 패킷 미러링, 캡처 중복, TCP 세그먼트 오프로딩 때문에 같은 모양이 보일 수 있으므로 이 결과만으로 원인을 확정하지 않습니다.

## 실제 루프백 캡처

`tcpdump`와 Python 3가 필요합니다. 스크립트는 임시 HTTP 서버를 열고 루프백 인터페이스만 캡처합니다.

```sh
sudo ./scripts/capture-loopback.sh
```

기본 출력은 현재 디렉터리의 `capture.txt`입니다. 포트가 충돌하면 다음처럼 바꿀 수 있습니다.

```sh
sudo PORT=28080 OUTPUT=/tmp/loopback-tcp.txt ./scripts/capture-loopback.sh
```

완료 뒤 스크립트는 서버와 캡처 프로세스를 종료합니다. 캡처 파일에는 로컬 프로세스의 통신 정보가 들어갈 수 있으므로 공개 저장소에 그대로 커밋하지 마세요.

## 관찰할 항목

1. 클라이언트의 SYN은 ACK 플래그 없이 시작하는지 확인합니다.
2. 서버의 SYN/ACK는 방향이 반대이고 클라이언트 sequence에 1을 더해 확인하는지 봅니다.
3. 마지막 ACK가 서버 SYN sequence에 1을 더해 확인하는지 봅니다.
4. 데이터가 생기면 `seq start:end` 범위와 상대의 누적 ACK가 어떻게 연결되는지 따라갑니다.
5. 같은 범위가 다시 보이면 지연 시간과 캡처 위치를 함께 기록합니다.

Linux namespace 안에서 실제 SYN 손실과 재전송을 만들려면 [라우팅·NAT·손실 실습](../linux-routing-nat/README.md)을 이어서 진행하세요.

## 기대 증거

이 실습에는 별도 reference 답안이 없습니다. fixture 검사에서 handshake의 세 packet이 서로의 sequence를 확인하고, 반복 SYN은 원인 확정이 아니라 candidate로 보고되어야 합니다. 수동 캡처를 수행했다면 interface, port, 수집 위치와 offload·중복 가능성을 `capture.txt`와 함께 기록합니다.

## 완료 기준

- SYN, SYN/ACK, 마지막 ACK의 방향과 서로 확인하는 sequence를 fixture에서 찾습니다.
- 동일 SYN 범위를 재전송 후보로 표시하되 확정 원인과 구분합니다.
- 수동 `capture.txt`를 검증 도구가 삭제하지 않고 사용자가 보존·폐기하도록 둡니다.

## 자기 설명

- SYN이 payload가 없어도 sequence 공간 하나를 소비하는 이유는 무엇인가요?
- 같은 packet 모양을 두 번 보았다는 사실만으로 실제 손실을 확정할 수 없는 이유는 무엇인가요?

## 검증

```sh
make observation-check
```

이 검사는 저장된 fixture만 읽으며 수동 캡처 파일을 만들거나 삭제하지 않습니다.
