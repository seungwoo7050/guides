# Runbook: Secret·Credential 유출

## 대상 상황과 위험

- Secret이 Git, CI log, application log, support bundle 또는 공개 artifact에 노출됐습니다.
- Host·CI·관리자 장치 침해로 credential이 탈취됐을 가능성이 있습니다.
- 노출 파일을 삭제해도 이미 복제된 값을 회수할 수 없습니다.

## 최우선 원칙

> 이력 정리보다 credential 폐기와 영향 제한이 먼저입니다.

손상 가능 host나 CI에서 새 secret을 생성하지 않습니다. 신뢰할 수 있는 별도 장치와 관리 경로를 사용합니다.

## 1. 사고 범위와 시각 고정

기록하되 값 자체는 적지 않습니다.

```text
Secret 이름·version·권한 범위
최초 노출 가능 시각
발견 시각
노출 위치와 접근 가능 주체
사용한 service·환경
관련 audit log 보존 위치
```

## 2. Credential 종류별 즉시 조치

### DNS API token

- 별도 신뢰 경로에서 token을 폐기합니다.
- 현재 DNS record와 변경 이력을 저장합니다.
- 필요한 최소 zone·record scope로 새 token을 발급합니다.

### Registry·CI credential

- Push·delete 권한을 즉시 제한합니다.
- 최근 tag·digest·attestation 변경을 조사합니다.
- Production은 신뢰한 exact digest만 유지합니다.

### Database credential

- 새 version을 DB에 추가하고 별도 connection으로 검증합니다.
- 소비자를 전환한 뒤 옛 credential을 폐기합니다.
- 무단 query와 data export 흔적을 조사합니다.

### Session·signing key

- Key rotation이 기존 session을 어떻게 무효화하는지 확인합니다.
- 필요하면 전체 session 폐기와 사용자 재인증을 수행합니다.
- Token lifetime 안의 오용 범위를 평가합니다.

### Backup encryption key

- Backup 기밀성 영향과 접근 log를 조사합니다.
- 새 backup은 새 key로 생성합니다.
- 과거 backup을 재암호화할지 보존·폐기 정책을 결정합니다.

## 3. Host·CI 신뢰 판단

공격자가 host root, Docker daemon 또는 CI workflow를 제어했을 가능성이 있으면 단순 secret 교체만으로 충분하지 않습니다.

- Clean host 재구축
- Workflow와 pinned action 검토
- Registry provenance·digest 검증
- 공격 이전 backup 선택
- 관리자 SSH key·OIDC trust·deploy token 회전

현재 host의 로그와 checksum을 유일한 증거로 신뢰하지 않습니다.

## 4. 안전한 회전 순서

```text
새 credential 생성
→ 최소 scope 적용
→ Candidate 소비자 검증
→ 원자 전환
→ 모든 replica·worker 확인
→ 옛 credential 폐기
→ 옛 값 사용 시도 탐지
```

단, 공격자가 즉시 악용할 수 있는 고위험 credential은 서비스 중단을 감수하고 먼저 폐기할 수 있습니다. 사고 지휘자와 보안 소유자가 판단합니다.

## 5. Git·로그·Artifact 잔존 처리

Credential 폐기 뒤 다음을 수행합니다.

- Git history rewrite 필요성 판단
- Fork·clone·cache는 회수할 수 없음을 기록
- CI log와 artifact 접근 제한·삭제
- Log store 보존·법적 증거와 개인정보 정책 조정
- Secret scanner와 pre-commit·CI gate 추가

History rewrite는 이미 노출된 credential을 다시 안전하게 만들지 않습니다.

## 6. 사용자·법적 영향

- 어떤 데이터와 계정에 접근 가능했는가?
- 실제 무단 사용 증거가 있는가?
- 개인정보·계약·규제 통지 의무가 있는가?
- 사용자 password나 session 재설정이 필요한가?

확인되지 않은 안전을 단정하지 않습니다.

## 7. 복구 확인

- 옛 credential이 실제로 거부됩니다.
- 모든 소비자가 새 version을 사용합니다.
- Registry·DNS·DB·backup의 변경 이력을 검토했습니다.
- 새 image와 release provenance가 신뢰됩니다.
- Secret 값이 log·metric·trace에 남지 않습니다.
- 새 credential의 scope와 expiry가 최소화됐습니다.
- 재유출 탐지와 alert가 작동합니다.

## 8. 증거와 후속 작업

```text
Secret 이름·version, 값 제외
노출 window·접근 범위
폐기·발급·전환 시각
영향 조사 결과
신뢰 재설정 범위
사용자 통지 결정
Scanner·scope·rotation 개선
```
