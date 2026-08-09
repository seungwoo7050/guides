# 보안 검토와 Release 점검표

## Context

- [ ] 사용자 기능과 보호할 상태가 정의됐습니다.
- [ ] build·deployment·policy identity가 확인됐습니다.
- [ ] 변경 범위와 data flow 차이가 기록됐습니다.
- [ ] third-party와 out-of-scope가 표시됐습니다.

## Threat와 요구사항

- [ ] 자산·행위자·경계·flow가 최신입니다.
- [ ] 변경으로 생긴 새 capability를 검토했습니다.
- [ ] high-impact attack path의 choke point가 있습니다.
- [ ] threat가 testable requirement와 연결됩니다.
- [ ] 예외는 owner·근거·expiry가 있습니다.

## 구현과 테스트

- [ ] authorization은 resource와 actor를 같은 decision에서 확인합니다.
- [ ] identity·credential은 최소 scope와 expiry를 가집니다.
- [ ] secret·sensitive data가 source·log·artifact에 남지 않습니다.
- [ ] dependency·artifact identity와 provenance를 확인했습니다.
- [ ] 정상·경계·실패·known-bad test가 있습니다.
- [ ] scanner result를 실제 reachability·impact와 구분했습니다.
- [ ] finding의 validation·treatment·lifecycle 축이 분리되고, confirmed finding의 `treatment: accept`와 권한 있는 수용 근거가 숨겨지지 않았습니다.

## 수정과 배포

- [ ] open finding의 상태와 evidence age가 있습니다.
- [ ] patch가 root cause를 바꿉니다.
- [ ] similar path review가 완료됐습니다.
- [ ] credential·artifact·data cleanup이 있습니다.
- [ ] migration·rollback 경로가 있습니다.
- [ ] 승인된 합성 post-release 결과와 별도의 production validation 계획, rollback·restore·forward-recovery trigger가 구분돼 있습니다.

## 탐지와 대응

- [ ] actor·resource·action·outcome·correlation event가 있습니다.
- [ ] log pipeline 누락·지연·중복을 관찰합니다.
- [ ] 핵심 threat의 known-positive·negative detection fixture가 있습니다.
- [ ] triage와 containment owner가 있습니다.
- [ ] trusted recovery source와 incident runbook이 있습니다.

## 결정

- [ ] `go`, `conditional-go`, `no-go` 중 하나를 명시했습니다.
- [ ] 결정 근거와 반대 evidence를 함께 기록했습니다.
- [ ] residual risk owner와 expiry가 있습니다.
- [ ] 재검토 trigger가 있습니다.
- [ ] 증거가 보장하지 못하는 범위를 기록했습니다.
