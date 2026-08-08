# Linux 호스트 강화 감사

실제 서버를 자동으로 수정하기 전에 현재 상태를 정확히 판정합니다. 이 실습은 두 개의 host snapshot을 읽어 구조화된 finding을 반환하는 감사기를 구현합니다.

관련 문서: [`docs/09-linux-host-provisioning-and-hardening.md`](../../docs/09-linux-host-provisioning-and-hardening.md)

## 구현 계약

`skeleton/audit.py`의 `audit(snapshot)` 함수를 완성합니다.

반환값은 다음 필드를 가진 finding 목록입니다.

```json
{
  "id": "unprotected-docker-tcp",
  "severity": "critical",
  "evidence": "tcp://0.0.0.0:2375",
  "remediation": "인증되지 않은 listener를 제거하고 SSH 또는 상호 TLS 경로를 사용한다.",
  "safe_order": "별도 관리 경로를 먼저 검증한 뒤 listener를 제거한다."
}
```

## 찾아야 할 경계

- 공유된 관리자 SSH key
- password 인증과 root 직접 로그인
- 인증되지 않은 Docker TCP listener
- application의 Docker socket mount
- 관리자가 아닌 사용자의 docker 그룹 포함
- 데이터베이스·dashboard의 공개 port
- 제한되지 않은 SSH 출발지
- 검토하지 않은 IPv6 firewall
- 비활성 시간 동기화
- disk 경보 부재
- host 로컬에만 있는 backup

증거가 없는 항목을 추측해서 finding으로 만들지 않습니다.

## 검증

```sh
cd exercises/09-host-hardening
./verify.sh skeleton
./verify.sh reference
```

`skeleton`은 구현 전 실패합니다. 완성 뒤 secure snapshot에는 false positive가 없어야 하고, insecure snapshot의 의도된 결함을 모두 찾아야 합니다.
