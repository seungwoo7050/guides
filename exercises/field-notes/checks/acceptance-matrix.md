# Acceptance matrix

각 행을 자신의 구현 결과로 채운다. 이 표는 파일·함수·정답 문자열의 존재가 아니라 **초기 durable 상태 + 사건 + 공개 행동/불변식 + 관측 결과**를 판정한다.

## 사용 규칙

- 결과는 `통과`, `실패`, `미검사`, `비적용` 중 하나다.
- `미검사`는 통과가 아니다. tool·device·account가 없으면 이유와 필요한 후속 evidence를 적는다.
- `비적용`은 제품 계약상 이유와 reviewer가 있을 때만 사용한다.
- 자동 검사는 command, exit status, normalized trace와 final repository/server snapshot을 연결한다.
- 사람/기기 검토는 device/build, 수행자/date, 평가 질문과 관측을 연결한다.
- 자동+사람 행은 둘 다 만족해야 통과다. 한쪽이 없으면 `미검사` 또는 `실패`다.
- reference는 자동 public contract를 통과해야 하고, skeleton/known-wrong behavior는 같은 검사에서 거부돼야 한다.

## 공통 matrix

| ID | Stage | 초기 durable 상태 | 사건/대표 실패 | 기대 공개 행동·불변식 | 판정 | 결과 | 증거 |
|---|---:|---|---|---|---|---|---|
| NAV-01 | 01 | cold start, valid local record | valid record link | readiness 뒤 current record detail; DB 변경 없음 | 자동+기기 | 미검사 | |
| NAV-02 | 01 | cold start | malformed/stale link | crash·private route 진입 없이 deterministic fallback | 자동+기기 | 미검사 | |
| NAV-03 | 01 | unsaved edit draft | system back/gesture | 정책에 따른 confirm/복귀, draft 보존 | 자동+기기 | 미검사 | |
| DB-01 | 02 | offline, clean record | save transaction 중 fault | record와 outbox 모두 이전 상태; draft와 실패 action 유지 | 자동 | 미검사 | |
| DB-02 | 02 | committed pending record/outbox | callback 없는 process kill/restart | record·command snapshot 복원, pending 표시 | 자동+기기 | 미검사 | |
| DB-03 | 02 | 이전 schema + pending/outbox | migration | record/outbox 보존 또는 명시적 recovery; 빈 DB 성공 금지 | 자동 | 미검사 | |
| PERM-01 | 03 | camera not-determined | permission deny | text record 흐름 유지, 대체 action | 자동+기기 | 미검사 | |
| PERM-02 | 03 | previously granted | Settings에서 revoke | current 상태 재조회, stale granted 사용 금지 | 자동+기기 | 미검사 | |
| FILE-01 | 03 | owned file copy 완료 | DB attach transaction 실패 | orphan 탐지/cleanup 가능, attachment 성공 표시 금지 | 자동 | 미검사 | |
| FILE-02 | 03 | pending attachment row | local file 누락 | `missing-local-file`와 recovery action; network busy retry 금지 | 자동+사람 | 미검사 | |
| SYNC-01 | 04 | attempted pending command A | server apply 후 response loss·restart·retry | 같은 command snapshot 재전송, server apply count 1, 최종 synced | 자동 | 미검사 | |
| SYNC-02 | 04 | attempted command A | duplicate request/response | remote/local 업무 효과·version 전이 한 번 | 자동 | 미검사 | |
| SYNC-03 | 04 | A in-flight | newer local edit B + A success | A snapshot 불변, 최신 local payload 보존, B가 새 base/ID로 pending | 자동 | 미검사 | |
| SYNC-04 | 04 | A/B attempted | B response 뒤 A response | arrival order와 무관하게 known remote/local version 회귀 없음 | 자동 | 미검사 | |
| SYNC-05 | 04 | baseVersion stale | conflict | local+remote+base+command durable 보존, 자동 overwrite/retry 없음 | 자동+사람 | 미검사 | |
| SYNC-06 | 04 | conflict 저장 | local/remote/merge 해결 | 선택 결과와 새 command가 transaction으로 남음 | 자동+사람 | 미검사 | |
| SYNC-07 | 04 | 여러 pending command | transport 401 | 모두 `blocked-auth`/preserved; busy retry·data 삭제 없음 | 자동 | 미검사 | |
| SYNC-08 | 04 | attempted command | malformed success body 반복 | success 금지; retry-wait 뒤 configured permanent evidence | 자동 | 미검사 | |
| SYNC-09 | 04 | known remote version 5 | success body version 4 | version regression 거절, local/remote snapshot 불변 | 자동 | 미검사 | |
| SYNC-10 | 04 | attempted command | explicit permanent failure | failed reason/snapshot 보존, 자동 retry 없음, recovery action | 자동+사람 | 미검사 | |
| SYNC-11 | 04 | eligible queue | foreground/background 동시 claim | 한 command lease/attempt, 다른 trigger는 duplicate effect 없음 | 자동 | 미검사 | |
| BG-01 | 05 | pending outbox | scheduler가 실행되지 않음 | pending 보존, app-active가 같은 bounded worker로 재개 | 자동+기기 | 미검사 | |
| BG-02 | 05 | active lease | task expiration/process death | checkpoint/attempt 보존, lease expiry 뒤 재개 | 자동+기기 | 미검사 | |
| BG-03 | 05 | 같은 fixture/fault | manual·app-active·background trigger | trigger와 무관한 final durable state | 자동 | 미검사 | |
| PUSH-01 | 05 | Android 13+, not-determined | notification setup | channel→permission→granted 뒤 token; denied에서 registration 없음 | 자동+실제 기기 | 미검사 | |
| PUSH-02 | 05 | app process 없음, current conflict | valid notification tap | migration/session 준비 뒤 current conflict route | 자동+실제 기기 | 미검사 | |
| PUSH-03 | 05 | response already claimed | same message/response 재전달 | duplicate trace, 추가 navigation·업무 효과 없음 | 자동 | 미검사 | |
| PUSH-04 | 05 | conflict already resolved | stale conflict notification | current repository 기준 detail/fallback, conflict 재생성 금지 | 자동+기기 | 미검사 | |
| PUSH-05 | 05 | any route/session | malformed payload 또는 이전 account | crash/navigation/data disclosure 없이 invalid/drop trace | 자동 | 미검사 | |
| REL-01 | 06 | 이전 schema+outbox+attachment/conflict | app upgrade | durable data와 attempted snapshot 보존, 정상/recovery 시작 | 자동+실제 기기 | 미검사 | |
| NATIVE-01 | 06 | clean source/config | 선택 module boundary review | JS→config/autolink→Android/iOS→runtime failure trace와 source 근거 | 사람 | 미검사 | |
| BUILD-01 | 06 | clean source | CNG + JS bundle | generated source/bundle로만 기록; native build 통과로 표시 안 함 | 자동+사람 | 미검사 | |
| BUILD-02 | 06 | Android preview artifact | 실제 Android install/upgrade/smoke | APK/install path, source/build/runtime/digest와 device 결과 연결 | 실제 기기 | 미검사 | |
| BUILD-03 | 06 | iOS preview artifact | 실제 iOS install/upgrade/smoke | device-signed artifact, source/build/runtime/digest와 device 결과 연결 | 실제 기기 | 미검사 | |
| BUILD-04 | 06 | incompatible native change | update compatibility 판정 | old binary에 incompatible JS update 전달 금지; 새 binary 근거 | 자동+사람 | 미검사 | |
| A11Y-01 | 06 | large font + TalkBack | create/permission/offline/conflict flow | 모든 상태·오류·action 접근, focus/draft 보존 | 실제 기기+사람 | 미검사 | |
| A11Y-02 | 06 | large font + VoiceOver | create/permission/offline/conflict flow | 모든 상태·오류·action 접근, focus/draft 보존 | 실제 기기+사람 | 미검사 | |
| PERF-01 | 06 | release-like build + fixed fixture | launch/scroll/save/100-command workload | 목표·측정 조건과 결과, interaction failure 여부 기록 | 실제 기기+사람 | 미검사 | |
| RELEASE-01 | 06 | release candidate | manifest review | source·lock/config·app/build/runtime·artifact digest 연결 | 자동+사람 | 미검사 | |
| RELEASE-02 | 06 | privacy/data inventory | declaration review | 실제 storage/permission/telemetry와 일치, 법률 판단 분리 | 사람 | 미검사 | |

## 결과 값

```text
통과
실패
미검사 — 이유와 필요한 도구/device/account/evidence 필수
비적용 — 범위 근거와 reviewer 필수
```

## evidence 최소 조건

각 행의 증거는 [`evidence-template.md`](evidence-template.md)를 사용하고 최소 다음을 포함한다.

- source revision과 app/build/runtime identity
- test name/command와 exit status 또는 reviewer/date/device
- 초기 DB/outbox/file/session/remote 상태
- fault/event 순서
- final DB/outbox/file/UI/server apply history 또는 artifact digest
- 보장하지 않는 platform·provider·store·UX 범위

자동 log가 green이어도 실제 기기 행을 채우지 않는다. screenshot/recording만 있고 초기 상태·사건·판정 질문이 없으면 근거가 아니다.
