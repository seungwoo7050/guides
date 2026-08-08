# Runbook: 잘못된 배포와 Rollback

## 대상 증상과 사용자 영향

- 새 release 직후 error rate, latency, restart 또는 업무 실패가 증가합니다.
- Smoke test는 통과했지만 관찰 창에서 문제가 나타날 수 있습니다.
- Database migration 때문에 단순 image rollback이 불가능할 수 있습니다.

## 사전 안전 조건

- 추가 배포를 잠그고 동일 환경의 동시 상태 변경을 막습니다.
- `current`, `previous`, candidate manifest와 실제 실행 digest를 보존합니다.
- Schema·config·secret 호환성을 확인하기 전 image만 바꾸지 않습니다.

## 1. 영향과 시간 상관관계 확인

```text
배포 시작·확정 시각
오류 시작 시각
영향 경로·사용자·비율
현재 release marker
최근 migration·secret 회전
```

배포와 시간상 가까워도 원인으로 단정하지 않습니다. 외부 dependency나 host 자원도 함께 확인합니다.

## 2. 실제 상태 확인

```sh
cd /srv/example
docker compose ps -a
docker compose config >/dev/null
docker compose images
docker compose logs --since 30m --no-color
```

Manifest와 비교:

- Current exact digest
- Previous exact digest
- DB schema min·max
- Config schema
- Required secret version
- Smoke path

## 3. Rollback 가능성 판정

다음이 모두 참이면 자동 또는 신속 rollback 후보입니다.

- 이전 image가 registry에 존재합니다.
- 현재 DB schema가 이전 release 허용 범위 안입니다.
- 현재 config와 secret을 이전 release가 읽을 수 있습니다.
- 데이터 파괴 migration이 없습니다.
- 문제 release만 제거해 사용자 영향이 줄어들 근거가 있습니다.

다음이면 사람 판단과 roll-forward를 검토합니다.

- Column·table 삭제나 비가역 data 변환이 적용됐습니다.
- 이전 release가 새 schema를 읽지 못합니다.
- 현재와 이전 모두 동일하게 실패합니다.
- 보안 사고 또는 데이터 정합성 위반 가능성이 있습니다.

## 4. Rollback 실행

```text
증거와 현재 상태 기록
→ Previous manifest 재검증
→ Exact digest pull
→ Rendered Compose config 검사
→ 필요한 호환 migration만 실행
→ 이전 release 재생성
→ Readiness
→ 외부 smoke
→ current release 원자 갱신
→ 관찰 창
```

`latest`나 tag를 다시 해석하지 않습니다.

## 5. Roll-forward 선택

Rollback보다 수정 release가 안전할 수 있습니다.

- 문제 범위가 작고 수정이 검증됐는가?
- Data 변환을 되돌릴 수 없는가?
- 수정 release 준비 시간이 사용자 영향보다 짧은가?
- 임시 feature disable로 시간을 확보할 수 있는가?

긴급 수정을 production host에서 직접 build하지 않습니다. 동일 CI·attestation·manifest 경계를 유지합니다.

## 6. 가역 완화

- 문제 feature flag 비활성화
- 특정 쓰기 경로 maintenance
- Traffic·worker 제한
- 안전한 이전 exact release rollback

Data를 임의 수정해 code 오류를 숨기지 않습니다.

## 7. 복구 확인

- 외부 읽기·안전한 쓰기 성공
- Error·latency·restart 정상화
- Current file, 실제 digest와 deployment record 일치
- Schema·config·secret 호환성 확인
- 관찰 창 동안 재발 없음
- 실패 release가 자동 재배포되지 않도록 gate 적용

## 8. 증거와 후속 작업

```text
Candidate·current·previous manifest digest
실행 image digest 전후
Migration 결과
Smoke와 관찰 지표
Rollback 또는 roll-forward 판단 근거
승인자·실행자
재발 방지 test·deployment gate
```
