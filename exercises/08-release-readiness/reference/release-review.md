# release readiness 검토 예시 해설

## candidate identity

- client build: `relay-client@1.0.0-rc3`
- server build: `relay-server@1.0.0-rc3` evidence가 있으나 client와 protocol/content 조합의 별도 manifest 확인이 필요하다.
- content/save/replay/protocol: build manifest에 고정된 값을 사용하며 서로 다른 candidate의 evidence를 대체하지 않는다.
- 현재 판정: **block**. fail 두 건과 unknown/stale evidence를 waiver 없이 ship으로 바꿀 수 없다.

## evidence validity

| evidence | status | correct candidate | age valid | scope sufficient | decision |
|---|---|---|---|---|---|
| tests-rules | pass | yes | yes | rule 범위 | accept |
| replay-regression | pass | yes | yes | replay 회귀 | accept |
| old-save-matrix | pass | no (`rc2`) | no (26h) | 현재 candidate 아님 | rerun; unknown gate |
| handheld-profile | fail | yes | yes | cold-load budget | blocking failure |
| controller-remap | pass | yes | yes | remap 경로 | accept |
| subtitle-review | unknown | yes | unknown | evidence 없음 | unknown; review 필요 |
| protocol-compat | pass | server rc3 | yes | client/server 조합 확인 필요 | conditional evidence |
| crash-symbolication | pass | yes | yes | operations | accept |
| suspend-result-commit | fail | yes | yes | result/save invariant | blocking failure |

## known issue와 residual risk

| issue | impact | affected users/platform | fallback | owner | re-review trigger | ship/block |
|---|---|---|---|---|---|---|
| ISSUE-42 | cold-load p95 5s 초과 | handheld cold start | control-ready 뒤 cosmetic 지연 | content-streaming | 새 rc3 profile p95 ≤5s | conditional 가능, 현재 fail |
| ISSUE-47 | suspend 중 result commit 중복 | suspend 가능한 플랫폼 | 없음 | platform-save | duplicate commit을 거부하는 fault test 통과 | block |
| subtitle evidence 없음 | 정보 접근 불가 가능성 | subtitles가 필요한 사용자 | 없음 | accessibility | completeness review 첨부 | block/unknown |
| save matrix stale | old save 손실 가능성 | rc2 save 보유 사용자 | 이전 build 유지 | platform-save | rc3에서 v1 migration 재실행 | block/unknown |

## release decision

- decision: `block`
- blocking evidence: `handheld-profile`, `suspend-result-commit`, `subtitle-review`, stale `old-save-matrix`
- waiver: 없음. 특히 중복 best-time commit에는 fallback이 없다.
- 재검토: 수정된 candidate identity로 save migration, subtitle completeness, suspend fault, cold-load profile을 다시 수집한다.
- rollback: 실행 파일만 내리는 것으로 save/content/protocol 호환이 보장되지 않으므로 previous-compatible 조합과 feature-disable 경로를 먼저 검증한다.

자동 검사는 candidate/status/evidence 연결과 block 조건을 확인한다. 실제 waiver 승인, 사용자 영향과 배포 책임은 사람이 결정한다.
