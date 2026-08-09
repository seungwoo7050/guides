# Stage 03 — picker·camera·permission·선택적 위치

## 학습 결과

사용자가 system picker 또는 camera로 사진을 추가하고, 원할 때만 현재 위치를 record에 첨부하게 한다. capability가 없거나 permission을 거절·제한·철회하고, 외부 system UI 중 process가 재생성돼도 text record와 이미 commit된 local data를 보존한다.

이 Stage를 마치면 다음을 수행할 수 있어야 한다.

- capability availability와 user permission을 독립된 상태 축으로 모델링한다.
- camera와 system photo picker를 서로 다른 adapter·실패 계약으로 구현한다.
- foreground one-shot location adapter를 구현·검사하되 record 위치 첨부는 사용자 선택으로 둔다.
- permission을 startup이 아니라 기능 action 문맥에서만 요청한다.
- denied·restricted·limited·revoked·unavailable·cancel을 application result와 대체 행동으로 바꾼다.
- 외부 URI를 app-owned file로 전환하고 file/DB/outbox partial state를 Stage 02 정책으로 조정한다.
- picker/camera 중 background·process recreation과 duplicate result를 안전하게 처리한다.
- generated native config, installed development build와 실제 Android/iOS 결과를 연결한다.

## 시작 상태와 의도적 미완성

시작점은 Stage 02를 완료한 learner 앱이다.

- record, attachment metadata와 outbox는 SQLite가 소유한다.
- file ownership, orphan와 missing-file reconciliation이 있다.
- offline save·delete와 v1 migration이 통과한다.
- route, malformed/stale link와 dirty-back behavior는 Stage 01 계약을 유지한다.
- 실제 server upload와 background scheduler는 아직 없다.

아래 미완성 목록은 Stage 02를 끝낸 learner 작업 복사본의 **Stage 03 시작 기준선**이다. 누적 [`../reference`](../reference/)에 camera·system picker·foreground location adapter와 후속 기능이 있더라도 그 구현 모양이 유일한 정답이거나 실제 Android/iOS 기기 검토까지 끝났다는 뜻은 아니다. 자동 범위는 현재 package scripts와 verify 결과로 확인한다.

Stage 03 시작 시 다음은 의도적으로 미완성이다.

- camera·photo-picker·foreground-location production adapter
- capability/permission 상태 UI
- app config의 실제 permission description과 generated native 확인
- external operation pending marker와 result reconciliation
- 실제 Android/iOS device evidence

development build를 Stage 01부터 사용했더라도 native dependency·permission config를 바꾸면 새 binary를 생성해 다시 설치한다. Metro reload나 Expo Go로 native 변경을 검증하지 않는다.

## public contract

정본은 [`../shared/src/contracts.ts`](../shared/src/contracts.ts)와 [`../shared/src/ports.ts`](../shared/src/ports.ts)다.

두 상태 축은 섞지 않는다.

```ts
type CapabilityAvailability =
  | { kind: "available" }
  | { kind: "limited"; description: string }
  | { kind: "unavailable"; reason: string };

type PermissionState =
  | { kind: "not-required" }
  | { kind: "not-determined" }
  | { kind: "granted" }
  | { kind: "limited"; description: string }
  | { kind: "denied"; canAskAgain: boolean }
  | { kind: "restricted"; reason: string };
```

다음 조합은 서로 다른 제품 상태다.

| availability | permission | 의미·행동 예 |
|---|---|---|
| available | granted | action 실행 가능, 실행 중 hardware/provider failure는 여전히 가능 |
| available | not-determined | 사용자 action 설명 뒤 필요한 경우 요청 |
| available | denied | text save·다른 photo source 제공, 반복 prompt 금지 |
| limited | limited/granted | 현재 제한 범위와 가능한 action 설명 |
| unavailable | 어떤 값이든 | permission prompt가 아니라 capability/build/device 대체 경로 |

`available`을 permission 허용으로, `denied`를 camera hardware 부재로 바꾸지 않는다. availability query와 permission query가 완료되기 전 loading/checking은 screen/application state가 소유한다.

필수 port:

- `CameraPort`: availability, permission query/request, capture cancel/success
- `PhotoPickerPort`: availability, permission query/request, choose cancel/success
- `LocationPort`: availability, permission query/request, foreground current measurement/failure
- `AttachmentFileStore`: temporary URI ownership·checksum·byte size·cleanup
- `AttachmentRepository`: owned file 연결과 missing-file state

camera, picker와 location **세 adapter 모두 필수**다. `RecordPayload.location`이 optional인 것은 사용자가 위치를 첨부하지 않을 수 있다는 뜻이지 `LocationPort` 구현·fault 검사를 생략해도 된다는 뜻이 아니다.

system picker가 photo-library 전체 permission을 요구하지 않는 platform/API라면 `not-required`로 정규화하고 실제 dialog를 만들지 않는다. 이는 “사용자가 고른 항목 선택은 허용되지만 library 전체 grant를 받은 것은 아님”이라는 뜻이다. `requestPermission()`을 불필요하게 호출하지 않고, system picker의 선택 범위와 library API의 `limited` permission을 같은 상태로 취급하지 않는다.

## 상태·자원 소유권과 불변식

| 상태·자원 | 소유자 | 바꾸는 사건 | 불변식 |
|---|---|---|---|
| hardware/API/build availability | device·OS·installed binary | OS update, build/install, device policy | permission과 별도로 다시 조회할 수 있다. |
| permission | OS와 사용자 | request, Settings 변경, policy | cached `granted`를 영구 신뢰하지 않는다. |
| picker/camera UI·temporary result | OS/provider/native adapter | open, cancel, capture/select, interruption | cancel을 error/save success로 바꾸지 않는다. |
| pending external operation | application/repository | launch external UI, result claim, expiry | process restart·duplicate delivery 뒤 한 번만 effect를 만든다. |
| attachment bytes | app-owned file store | copy, validation, cleanup | provider URI를 durable identity로 쓰지 않는다. |
| attachment metadata·record location | SQLite | attach/remove, user location choice, reconciliation | text record commit과 optional capability 실패를 분리한다. |

정상 경로는 system picker에서 한 장을 골라 owned file로 연결하는 것이다. 대표 경계는 사용자가 camera permission을 거절하고 picker로 전환하거나 location을 생략하는 흐름이고, 대표 실패는 external UI 중 process recreation 뒤 같은 result가 두 번 조정되는 경우다.

## 사용자 action과 permission 요청

startup에서 camera·photo·location permission을 일괄 요청하지 않는다.

```text
사용자가 "사진 추가" 선택
→ "사진 선택" 또는 "직접 촬영" source 선택
→ 해당 availability 조회
→ 해당 API에 실제 permission이 필요한지 조회
→ 필요한 경우 현재 문맥에서 설명하고 OS 요청
→ granted/limited이면 source 실행
→ denied/restricted/unavailable이면 대체 action과 text save 유지
```

`canAskAgain: true`여도 거절 직후 같은 dialog를 반복하지 않는다. 다음 명시적 action에서 이유를 다시 설명할 수 있다. `canAskAgain: false` 또는 `restricted`이면 Settings 안내와 기능 없는 경로를 제공한다.

Settings에서 돌아오거나 app가 active가 되면 관련 availability/permission을 재조회한다. 이전 `granted`가 `denied`로 바뀌면 열린 session을 닫고 UI를 현재 상태로 갱신한다. 복귀만으로 camera/location을 자동 재실행하지 않고 사용자의 원래 action을 다시 확인한다.

## picker와 camera를 둘 다 구현합니다

### system photo picker

- 가능한 platform에서는 사용자가 선택한 item만 받는 최소 권한 경로를 기본으로 둔다.
- cancel은 정상 완료이며 record·outbox를 바꾸지 않는다.
- returned URI, filename, MIME, size와 identifier가 모두 영구적·정확하다고 가정하지 않는다.
- remote/iCloud/provider asset은 bytes 준비가 늦거나 실패할 수 있다.
- library-wide limited access와 system picker selection scope를 구분한다.

### camera

- camera hardware/build availability와 camera permission을 각각 확인한다.
- capture cancel, hardware/session failure, app background, screen lock와 전화 interruption을 구분한다.
- 촬영 result도 temporary file이며 같은 ownership pipeline을 거친다.
- camera가 unavailable/denied여도 picker와 text-only record를 제공한다.

picker 성공만으로 Stage를 끝내거나 camera를 optional extension으로 미루지 않는다. 두 source의 application result는 공통 attachment workflow로 수렴하되 platform raw error를 하나의 `failed` 문자열로 지우지 않는다.

## app-owned file 연결

Stage 02의 비원자 경계를 그대로 사용한다.

```text
selected/captured temporary URI
→ operation/result identity 확인
→ app-owned staging copy
→ size·MIME·checksum 검증
→ SQLite attachment metadata + 필요한 outbox 관계 transaction
→ local-ready/upload-pending UI
→ orphan/missing-file reconciliation
```

필수 정책:

- zero-byte, too-large와 unsupported type은 attachment row로 확정하지 않는다.
- MIME, extension, filename이 모순될 수 있으므로 신뢰 수준을 기록한다.
- file copy 성공 뒤 DB transaction 실패는 orphan이 되고 cleanup 대상이다.
- DB row 뒤 file이 사라지면 `missing-local-file`로 바꾸고 upload를 시도하지 않는다.
- 같은 operation/result/checksum을 다시 처리해 attachment와 outbox를 중복 생성하지 않는다.
- attachment 실패가 이미 commit된 text record를 rollback하지 않는다.

크기·MIME·metadata 정책은 client의 UX/저장 보호다. remote content 검증과 malware policy를 대신하지 않는다.

## foreground location adapter는 필수, 첨부는 선택

Field Notes는 record 편집 화면에서 사용자가 누르는 `위치 추가` action만 제공한다.

```text
사용자 action
→ location availability
→ foreground permission 조회/필요 시 요청
→ one-shot current measurement
→ latitude·longitude·accuracy·measuredAt 검증
→ 결과 preview
→ 사용자가 record에 포함하거나 버림
```

application에는 `LocationPort` production adapter와 fake/fault adapter가 반드시 존재해야 한다. 그러나 다음은 모두 정상적인 record 결과다.

- 사용자가 위치 action을 누르지 않음
- permission을 거절함
- 측정 timeout/unavailable
- accuracy가 제품 threshold보다 낮아 사용자가 제외함
- 측정 결과를 preview한 뒤 제거함

어떤 경우에도 title/notes record save를 막지 않는다. 위치를 포함하면 latitude/longitude뿐 아니라 accuracy meter와 측정 시각을 함께 저장한다. last-known인지 새 측정인지, 낮은 accuracy를 경고 후 허용할지 제외할지는 정책과 evidence에 기록한다.

background location, 지속 tracking과 geofencing은 구현하지 않는다.

## process recreation과 duplicate result

external UI를 열기 전에 최소한 다음 의미의 pending marker를 durable하게 남긴다.

```text
operation id
source: picker | camera
target record id
created time/expiry
state: launched | result-received | ownership-complete | failed/cancelled
```

startup reconciliation:

```text
만료되지 않은 pending operation 조회
→ platform adapter가 제공하는 pending result가 있는지 확인
→ operation/target/result identity 검증
→ 이미 완료된 attachment인지 확인
→ ownership copy와 DB transaction 재개 또는 cancelled/failed 종료
→ completion marker와 orphan cleanup
```

Android picker처럼 platform API가 pending result 복구를 제공할 때만 사용한다. 한 platform의 API를 iOS, 모든 camera flow나 provider에 일반화하지 않는다. 복구 API가 없으면 pending marker를 성공으로 추측하지 않고 사용자에게 다시 선택/촬영할 수 있는 상태를 제공한다.

callback이 정상 전달된 뒤 startup reconciliation이 같은 result를 발견해도 업무 effect는 한 번이어야 한다. dedupe identity가 raw temporary URI 하나에만 의존하면 URI 변경·재사용을 견디지 못하므로 operation id, target과 verified content identity를 함께 고려한다.

## native configuration과 rebuild

permission description과 native module은 installed binary의 입력이다.

```text
package + app config/plugin
→ clean CNG/prebuild 결과
→ Android manifest / iOS plist·entitlement
→ 새 development binary
→ 실제 device permission·capability behavior
```

Stage evidence에는 다음을 연결한다.

- source revision과 lockfile package version
- app config/plugin input
- generated Android/iOS permission·module 결과
- installed app/build identity
- 실제 dialog 또는 no-dialog system picker behavior
- config를 바꾼 뒤 rebuild한 사실

generated native file을 손으로 고쳐 통과시키지 않는다. manifest/plist snippet에는 signing secret, device token과 private identifier를 넣지 않는다.

## privacy와 data inventory

다음 표를 실제 정책으로 채운다.

| 데이터 | 수집 trigger | local 위치 | remote 전송 | 보존·삭제 | 사용자 control |
|---|---|---|---|---|---|
| record text | Save | SQLite | Stage 04 sync | 제품 정책 | 편집·삭제 |
| selected/captured photo | 명시적 사진 action | app-owned file + SQLite metadata | Stage 03에서는 전송하지 않음; Stage 04+ sync 계약에서 별도 판정 | 제거·record 삭제 정책 | source 선택·제거 |
| foreground location | 명시적 위치 action + 포함 선택 | record SQLite field | Stage 03에서는 전송하지 않음; Stage 04+ sync 계약에서 별도 판정 | record와 같은 정책 | 거절·생략·제거 |
| permission state | OS query | memory/필요 최소 cache | 전송하지 않음 | 재조회 | Settings |

사진 EXIF 위치·기기 정보·촬영 시각을 보존/제거할지 명시한다. 사용자가 별도로 선택하지 않은 EXIF 위치를 record 위치로 자동 승격하지 않는다. log·crash report·evidence에 exact coordinate, record text, local URI와 selected photo content를 넣지 않는다.

## 정상·경계·대표 실패 시나리오

| ID | 초기 상태 | 사건 | 기대 durable 상태 | 기대 사용자 결과 |
|---|---|---|---|---|
| PICK-01 | picker available | 사진 선택 | owned file + attachment row 한 번 | preview와 제거 action |
| PICK-02 | picker open | cancel | DB/file/outbox 변화 없음 | edit draft 유지 |
| CAM-01 | camera available, granted | capture | 같은 ownership pipeline | photo attached |
| CAM-02 | camera permission not-determined | deny, canAskAgain true | text record/draft 보존 | picker·text-only, 즉시 재요청 없음 |
| CAM-03 | denied, canAskAgain false/restricted | camera action | attachment 없음 | Settings 또는 picker, save 가능 |
| CAP-01 | camera module/hardware 없음 | camera action | permission과 무관한 unavailable | picker/text alternative |
| PERM-01 | 이전 granted | Settings에서 revoke→active | cached state 폐기, record 보존 | 현재 denied UI, 자동 camera 실행 없음 |
| PERM-02 | library limited | picker/library action | 허용 범위 밖 data 추측 없음 | 현재 범위·추가 선택 안내 |
| PROC-01 | picker/camera launched | background/process recreation | pending marker + 기존 record 보존 | result 재조정 또는 다시 시도 |
| PROC-02 | result 이미 연결됨 | callback/reconciliation duplicate | attachment/outbox 한 개 | 화면 재초기화·중복 없음 |
| FILE-01 | result returned | zero-byte/too-large/type mismatch | attachment row 없음, staging 정리 | 실패 이유와 source 재선택 |
| FILE-02 | owned file copied | DB transaction fault | orphan 탐지, existing record 유지 | attachment 미연결, retry 가능 |
| FILE-03 | attachment row exists | file 삭제 | `missing-local-file`, upload 차단 | 제거·재선택 action |
| LOC-01 | location available, granted | valid one-shot | 선택 시 accuracy/time 포함 | preview 후 포함/버림 |
| LOC-02 | denied/timeout/low accuracy | record Save | location 없음, text command 정상 | 설명과 위치 없는 저장 |

## 자동 검사와 실패 거부

production adapter와 같은 application union을 반환하는 fake/fault adapter를 둔다. 최소 자동 검사는 다음 behavior를 관찰한다.

- camera/picker/location 각각의 raw availability→`CapabilityAvailability` mapping
- 각 capability의 raw permission→`PermissionState` mapping
- availability와 permission이 독립적으로 화면 decision에 반영됨
- startup에서는 permission request를 호출하지 않고 사용자 action에서만 호출함
- denied/restricted/limited/unavailable 뒤 text save가 정상 commit됨
- picker/camera cancel이 error·attachment·outbox를 만들지 않음
- selected/captured result가 같은 ownership validation을 거침
- zero-byte/too-large/unsupported·copy failure의 DB/file final state
- pending external operation expiry, recovery와 duplicate result 거부
- Settings revoke/active event 뒤 state 재조회와 자동 민감 action 미실행
- valid/invalid location value, timeout, low accuracy와 user include/omit
- data inventory 필수 field와 log redaction policy

known-wrong adapter에서 `permission === granted`만 보고 unavailable camera를 실행하거나, location failure가 record save를 막거나, duplicate result가 attachment 두 개를 만드는 경우를 검사에서 거부한다.

자동 검사에는 실제 photo bytes·coordinate·private URI 대신 deterministic fixture와 redacted identity를 사용한다.

## Android/iOS development build 관찰

두 platform에서 camera와 picker를 모두 실행한다.

1. fresh permission 상태에서 app startup이 dialog를 열지 않는지 확인한다.
2. system picker cancel과 성공을 각각 실행한다.
3. camera permission을 거절한 뒤 picker와 text save가 가능한지 확인한다.
4. camera를 허용하고 실제 capture→owned attachment를 확인한다.
5. 가능한 platform에서는 limited photo access와 추가 선택 flow를 확인한다.
6. Settings에서 camera/location permission을 철회하고 app로 돌아온다.
7. foreground location을 성공·거절·timeout/낮은 accuracy 상태로 실행하고 위치 없는 record도 저장한다.
8. picker/camera 중 background, screen lock와 process recreation을 수행한다.
9. callback/restart reconciliation이 겹쳐도 attachment가 하나인지 DB/file evidence로 확인한다.
10. generated manifest/plist와 설치 binary의 실제 permission dialog를 source/build identity에 연결한다.

Android 개발자 옵션의 “활동 유지 안 함”은 Activity recreation을 관찰하는 보조 수단이지 모든 production process-kill 순서를 재현한다는 증거가 아니다. iOS에서 Android pending-result API가 없으면 같은 복구를 구현했다고 추정하지 말고 재시도/fallback 결과를 기록한다.

실제 camera가 없는 emulator/simulator 결과만 있다면 camera hardware, provider URI, permission dialog와 process interruption은 `미검사`로 남긴다.

## 제출 evidence

```text
stage-03/
├── capability-permission-matrix.md
├── generated-native-config.md
├── adapter-result-cases.md
├── file-lifecycle-and-reconciliation.md
├── pending-operation-history.md
├── location-policy.md
├── data-inventory.md
├── android-device-results.md
├── ios-device-results.md
├── automatic-test-output.txt
└── known-limits.md
```

permission dialog screenshot만 제출하지 않는다. `capability-permission-matrix.md`에는 availability·permission 두 축, 사용자 action, final record/file/outbox와 다음 UI action을 적는다. `pending-operation-history.md`에는 process state, operation identity, callback/reconciliation 순서와 중복 거부 결과를 기록한다.

사람 검토 질문:

1. permission을 거절하거나 capability가 없어도 사용자가 text record를 끝낼 수 있는가?
2. picker와 camera가 서로 다른 OS 실패를 보존하면서 같은 attachment 의미로 수렴하는가?
3. 위치를 선택하지 않은 record가 불완전하거나 오류처럼 보이지 않는가?
4. process recreation 뒤 app가 외부 작업 성공을 추측하거나 attachment를 중복 생성하지 않는가?
5. permission 설명, 실제 수집 trigger, data inventory와 generated native config가 일치하는가?
6. Android와 iOS에서 직접 확인하지 못한 상태를 다른 platform 결과로 채우지 않았는가?

## 자동 검증이 보장하지 않는 범위

- mock adapter는 실제 OS raw enum, dialog 문구, Settings와 hardware/session 수명을 보장하지 않는다.
- file fixture test는 provider URI, iCloud/remote asset와 실제 camera file metadata를 보장하지 않는다.
- development build는 preview/production signing, store privacy declaration과 모든 vendor device를 보장하지 않는다.
- 한 platform의 pending-result behavior는 다른 platform의 process restoration을 보장하지 않는다.
- selected photo의 client validation은 server content validation·moderation·malware 방어를 보장하지 않는다.
- foreground location success는 background tracking, 지속 정확도와 사용자 privacy policy 전체를 보장하지 않는다.

## 비범위

- background location·geofencing·지속 tracking
- 영상 녹화·편집과 전체 photo library 관리
- cloud media library와 remote attachment upload 성공
- microphone·contacts·Bluetooth 같은 추가 capability
- biometric login 전체
- server-side media validation·moderation
- store privacy form 승인과 production signing

## 완료 기준

- camera, system picker와 foreground location production/test adapter를 모두 구현한다.
- availability와 permission을 분리하고 startup이 아닌 기능 action에서 필요한 permission만 요청한다.
- denied·restricted·limited·revoked·unavailable에서도 text record와 기존 committed data를 보존한다.
- picker·camera cancel/success가 공통 owned-file pipeline으로 수렴하고 temporary URI를 영구 data로 쓰지 않는다.
- process recreation과 duplicate result 뒤 attachment·outbox effect가 한 번뿐이다.
- partial file·orphan·missing-file 상태가 Stage 02 reconciliation로 수렴한다.
- 위치 첨부는 사용자 선택이며 생략·timeout·낮은 accuracy가 record save를 막지 않는다.
- app config→generated Android/iOS config→설치 development build→실제 permission behavior를 evidence로 연결한다.
- Android와 iOS 실제 결과를 각각 기록하거나 검사하지 못한 platform/capability를 `미검사`로 남긴다.

Stage 03 완료는 background 실행, notification delivery, remote upload나 store privacy 승인을 자동 증명하지 않는다. 다음 Stage들은 같은 attachment/outbox identity를 실제 sync 실패와 lifecycle에 연결한다.
