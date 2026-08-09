# Capstone — Offline Field Notes release candidate

## 결과물

현장 조사자가 Android와 iOS에서 사용할 수 있는 local-first 기록 앱의 **하나의 release candidate**를 만든다. Stage 과제를 화면 수만 늘려 반복하지 않는다. 서로 다른 owner와 failure가 연속해서 발생할 때 같은 사용자 의도와 artifact를 끝까지 추적한다.

필수 사용자 결과:

```text
offline record 작성·편집·삭제
system picker와 camera로 app-owned 사진 첨부
사용자가 선택할 때만 foreground 위치 추가
process restart와 이전 schema upgrade 뒤 local 상태 복원
연결 복구 뒤 outbox sync
response loss·중복·새 편집·conflict 처리
background 미실행 뒤 foreground resume 수렴
notification cold start에서 최신 DB 상태로 navigation
Android·iOS build/config/artifact identity 검토
```

앱 화면 수나 디자인 화려함보다 상태 소유권, 중단·실패 뒤 불변식, 실제 관측 결과와 증거의 한계를 평가한다.

## 시작 상태

Stage 01~06을 순서대로 수행한 Field Notes 또는 같은 공개 계약을 가진 프로젝트에서 시작한다. 저장소에는 최소 다음이 있어야 한다.

- list/detail/edit/settings route와 startup/navigation coordinator
- SQLite `records`, `attachments`, `outbox`, `conflicts`, `processed_intents`
- app-owned file staging/reconciliation
- camera·picker·foreground-location adapter와 permission degradation
- foreground/background가 공유하는 bounded sync worker와 deterministic fault server
- notification intent adapter
- CNG app config, development/preview/production profile와 고정 lockfile

의도적으로 제공하지 않는 것:

- production backend, push provider, signing credential와 store project
- 완성된 privacy/store 문구와 rollout 판단
- 모든 실제 device/OS 조합
- Kotlin·Swift custom module 정답

reference app는 공개 행동의 한 구현이다. 유일한 architecture나 제출물을 뜻하지 않는다.

## 필수 통합 failure journey

같은 record와 release candidate identity를 유지하며 아래 순서를 수행한다. 중간 상태를 새로 초기화해 각 단계만 따로 시연하면 capstone 증거가 아니다.

1. 이전 app/schema fixture에 **unsynced outbox**를 둔 채 새 preview build로 upgrade한다.
2. network를 차단하고 record를 편집해 text와 outbox를 한 transaction으로 commit한다.
3. system picker와 camera를 각각 사용해 사진을 app-owned file로 옮긴다.
4. foreground location을 사용자가 선택하지만 permission은 거절한다. text·사진 record 저장은 계속 성공해야 한다.
5. save commit 직후 process를 종료한다. 재시작 뒤 route, record, attachment와 command identity를 복원한다.
6. sync server가 command를 적용한 뒤 response를 잃게 한다. **같은 command id·payload·baseVersion**으로 retry한다.
7. 이전 command가 in-flight인 동안 같은 record를 다시 편집한다. 늦은 성공이 새 local edit를 덮지 않아야 한다.
8. server에 다른 변경을 만들어 version conflict를 발생시키고 local/base/remote를 모두 보존한다.
9. background task가 전혀 실행되지 않는 조건을 만든다. 다음 foreground resume가 같은 bounded worker로 pending 상태를 전진시킨다.
10. 오래되거나 중복된 conflict notification으로 cold start한다. payload를 정본으로 쓰지 않고 migration/session 뒤 최신 DB 상태를 읽어 한 번만 올바른 route를 연다.
11. 선택한 native dependency 하나를 TypeScript call→plugin/autolinking→Android/iOS source/config→thread/lifecycle/error→binary/runtime mismatch까지 추적한다.
12. 같은 source/profile/version/runtime identity를 가진 플랫폼별 manifest pair에서 Android AAB+APK/Play split, iOS xcarchive canonical tree+IPA/TestFlight를 고유 artifact ref로 연결한다. 설치 artifact·관찰 runtime/launch, artifact별 signing claim/review, store build와 전달 bytes declaration/review를 분리하고 수행하지 못한 항목은 `not-run`으로 둔다.

fault server와 test fixture는 허가된 local 환경에서만 사용한다. production push, 사용자 data나 store release에 failure를 주입하지 않는다.

## owns와 exit capability 결합

| catalog owns | journey 근거 | 연결 exit capability |
|---|---|---|
| 모바일 앱 수명 주기와 navigation | 1·5·10의 upgrade/restart/cold-start trace | Android·iOS에서 동작하는 앱을 만든다; 오프라인·권한·기기 기능 실패를 처리한다 |
| 오프라인 캐시·동기화 | 2·5~9의 DB/outbox/file/fault history | Android·iOS에서 동작하는 앱을 만든다; 오프라인·권한·기기 기능 실패를 처리한다 |
| 카메라·위치·알림·background 작업 | 3·4·9·10의 정상·거절·미실행·중복 evidence | Android·iOS에서 동작하는 앱을 만든다; 오프라인·권한·기기 기능 실패를 처리한다 |
| Android·iOS 빌드·서명·배포 | 1·12의 upgrade, config, build와 artifact identity | 실제 빌드와 배포 산출물을 검증한다 |
| 네이티브 모듈 경계 읽기 | 11의 양 플랫폼 boundary review와 대표 불일치 | Android·iOS에서 동작하는 앱을 만든다; 실제 빌드와 배포 산출물을 검증한다 |

## 제출 문서

- [architecture contract](architecture-contract.md)
- [data·sync contract](data-sync-contract.md)
- [device test matrix](device-test-matrix.md)
- [release evidence](release-evidence.md)
- redacted raw test/log/screenshot/profile artifact와 failure journey timeline

template의 빈칸을 그대로 제출하거나 결과를 `OK` 한 단어로 요약하지 않는다. 각 증거에는 initial state, 사건, expected/actual invariant, source/build/device identity와 비보장 범위가 있어야 한다.

## 완료 gate

### Gate 1 — local durability와 navigation

- offline save와 outbox 생성이 같은 transaction이다.
- file/DB partial failure가 orphan 또는 missing-file 상태로 수렴한다.
- 이전 schema와 unsynced command를 지우지 않고 upgrade한다.
- process 종료와 notification cold start 뒤 readiness를 거쳐 route를 복원한다.

### Gate 2 — sync correctness

- attempted command snapshot은 불변이고 duplicate execution은 한 업무 결과다.
- response loss·malformed response·version regression·401·permanent failure가 서로 다른 durable 상태다.
- 오래된 success가 최신 local edit를 덮지 않는다.
- conflict가 local/base/remote를 보존하고 해결은 새 command를 만든다.
- background 실행 없이 foreground resume로 수렴한다.

### Gate 3 — capability degradation

- system picker와 camera 두 경로가 app-owned file을 만든다.
- foreground location adapter를 구현하되 사용자가 위치를 선택하지 않거나 거절해도 record를 저장한다.
- availability와 permission을 분리하고 denied·revoked·unavailable을 대체 행동으로 연결한다.
- notification은 최신 record가 아닌 validated intent다.

### Gate 4 — cross-platform usability

- Android와 iOS 실제 기기에서 핵심 journey를 수행한다.
- TalkBack·VoiceOver에서 record 생성과 conflict 해결이 가능하다.
- 큰 글자·작은 화면·keyboard에서 action과 draft를 잃지 않는다.
- 사용할 수 없는 기기나 도구는 `pass`가 아니라 `not-run`과 필요 증거로 남긴다.

### Gate 5 — native/release traceability

- existing native dependency의 JS→config→Android/iOS→runtime 경계를 읽었다.
- release-contract의 플랫폼별 schema v2 manifest pair에서 같은 source·lockfile·profile·app version·runtime과 고유 `artifacts[]` ref가 연결된다.
- Android AAB+APK/Play split, iOS xcarchive+IPA/TestFlight를 구분하고 installation이 실제 설치 후보 ref·physical device·관찰 runtime/policy·launch 결과를 가리킨다.
- signing의 `claimed`/`manually-reviewed`, store-delivered bytes의 `declared`/`manually-reviewed`를 자동 trust·delivery 검증으로 확대하지 않는다.
- signing·store 처리·rollout을 실행하지 않았으면 `not-run`을 자동화 결과로 대체하지 않는다.

## 대표 비합격 사례

- remote 성공 뒤에만 local save를 완료함
- process restart를 Metro reload로만 검사함
- picker/camera 임시 URI를 영구 file처럼 보존함
- location·notification 거절을 app 오류나 startup prompt로 처리함
- retry할 때 command id·payload·baseVersion을 바꿈
- permanent failure나 malformed/version-regressed response를 `synced`로 표시함
- background scheduler를 완료 보장으로 표현함
- notification body를 최신 업무 상태로 사용함
- native module 경계 “읽기” 대신 한 플랫폼 custom module만 구현함
- Expo Go, CNG generation 또는 AAB 생성만으로 Android/iOS 동작과 설치를 주장함
- simulator `.app`을 iOS physical evidence로, IPA를 simulator evidence로 기록하거나 upload artifact digest를 store-delivered bytes로 재사용함
- evidence에 token·record text·정확한 위치·사진 원본을 포함함

## 사람 검토 질문

1. 각 durable state의 owner와 변경 사건이 code, schema와 UI에서 같은가?
2. journey 어느 지점에서 process가 사라져도 이미 commit한 사용자 의도가 남는가?
3. attempted command가 retry 사이에 바뀌지 않았음을 어떤 trace가 보여 주는가?
4. permission 거절과 background 미실행이 핵심 text/photo 기록을 막지 않는가?
5. notification cold start가 stale payload가 아니라 latest repository를 읽는가?
6. 선택한 native dependency의 양 플랫폼 entry, thread, lifecycle과 error 의미가 실제 source/config에 근거하는가?
7. device·accessibility evidence가 특정 build identity와 연결되는가?
8. 각 artifact ref/digest가 무엇을 식별하고 signing claim, store build·전달 bytes declaration 중 무엇은 증명하지 못하는가?
9. `not-run` 항목이 exit capability 판단에 어떤 제한을 남기는가?
10. 인접 브랜치가 소유하는 backend 운영·일반 보안·native 전문 영역을 모바일 완료 주장에 섞지 않았는가?

## 알려진 한계와 확장

기본 capstone은 production backend·push delivery SLA·store review·조직 credential 운영, background location, payment와 native 전문 구현을 보장하지 않는다. 기본 gate를 통과한 뒤에만 resumable upload, field merge, encrypted DB key lifecycle, custom Kotlin·Swift Expo module 중 하나를 선택 확장할 수 있다.

이 capstone과 자동 검사가 통과하면 결과는 `stable` 자동 선언이 아니라 **사람의 stable 검토 준비 완료**다.
