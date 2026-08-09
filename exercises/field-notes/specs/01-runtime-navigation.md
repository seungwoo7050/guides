# Stage 01 — runtime·layout·navigation

## 학습 결과

모바일 app shell을 만들고 list/detail/new/edit route가 internal navigation, external link, back action과 process restart에서 같은 업무 의미를 유지하게 한다.

이 Stage를 마치면 다음을 수행할 수 있어야 한다.

- OS process, router, application coordinator와 in-memory repository의 상태 소유권을 구분한다.
- raw URL과 restoration 후보를 신뢰하지 않고 공통 `NavigationIntent`로 정규화한다.
- cold start, warm delivery와 restoration에서 readiness 뒤 같은 route decision을 만든다.
- malformed·stale·duplicate intent가 record나 draft를 반쯤 바꾸지 않게 한다.
- Android system back과 iOS gesture에서 unsaved draft를 같은 업무 정책으로 보호한다.
- 작은 화면·큰 글자·keyboard·TalkBack/VoiceOver에서도 기록 흐름을 완료한다.
- 자동 contract, simulator와 실제 development build가 각각 보장하지 않는 범위를 설명한다.

## 시작 상태와 의도적 미완성

저장소에는 세 역할이 있다.

| 경로 | 시작 상태 | 의도적으로 남아 있는 것 |
|---|---|---|
| [`../shared`](../shared/) | public type, fixture와 Stage 01 contract runner | router·device integration 자체는 없음 |
| [`../skeleton`](../skeleton/) | compile·launch 가능한 learner 앱 | ID/URL parsing, duplicate key, dirty-back decision과 관련 UI behavior가 TODO라 최초 contract 검사는 실패함 |
| [`../reference`](../reference/) | Stage 01 public behavior를 포함해 이후 결과가 누적될 수 있는 실행 비교 기준 | 후속 기능의 존재가 Stage 01 실제 기기 evidence나 전체 과정 완료를 대신하지 않음 |

권장 시작점은 `skeleton`이다. `reference/app/`과 `reference/src/`는 public behavior가 실제 Expo Router 앱에 연결되는 경로를 보여 주는 누적 비교 기준이다. Stage 01을 연습할 때는 Stage 01 contract만 판정하고, 누적 reference의 후속 repository·adapter를 Stage 01 요구사항으로 소급하지 않는다. reference의 component 이름, 색상, 문구나 파일 배치를 복사할 필요는 없다.

Stage 01 learner 시작 구현의 record 세 개와 새로 저장한 record는 **현재 process의 memory에만** 있다. 편집 결과가 process restart 뒤 사라지는 것은 이 Stage 기준선의 의도적 미완성이고, Stage 02에서 SQLite와 outbox를 추가한다. 누적 reference에 후속 durable adapter가 있더라도 이 학습 순서는 바뀌지 않는다. 반면 link target 검증, fallback, duplicate 방지와 dirty-back 정책은 Stage 01에서 완성해야 한다.

## 기준 실행과 development build

저장소 root에서 다음을 실행한다.

```sh
npm ci
npm run typecheck
npm run test:stage01
npm run test:stage01:skeleton
```

기준 결과:

- `typecheck`: shared·reference·skeleton이 compile된다.
- `test:stage01`: reference contract와 UI behavior가 통과한다.
- `test:stage01:skeleton`: 최초 skeleton에서는 의도적 TODO를 찾아 실패한다. 학습자 구현 뒤에는 통과해야 한다.

reference 앱의 첫 Android/iOS development build를 생성·설치하고 실제 기기라면 `--device`를 전달한다.

```sh
npm run run:android --workspace=@field-notes/reference -- --device
npm run run:ios --workspace=@field-notes/reference -- --device
```

설치 뒤 Metro만 다시 연결할 때 사용한다.

```sh
npm run start:dev-client --workspace=@field-notes/reference
```

learner 구현은 workspace 이름을 `@field-notes/skeleton`으로 바꾼다. 한 host에서 지원되지 않는 platform 명령을 억지로 성공 처리하지 말고 실제 실패 또는 `미검사`를 기록한다.

Expo Go나 browser preview는 빠른 UI 관찰에만 쓸 수 있다. custom scheme cold/warm entry, 설치된 native configuration, process 종료와 platform back evidence는 development build에서 다시 검사한다.

## 상태 소유권과 불변식

| 상태·자원 | 소유자 | 바꾸는 사건 | Stage 01 불변식 |
|---|---|---|---|
| process·foreground 기회 | OS | launch, background, termination | callback 없이 종료될 수 있다고 가정한다. |
| raw URL·restoration 후보 | OS/router | cold/warm delivery, route restore | schema와 freshness를 확인하기 전 route로 확정하지 않는다. |
| normalized intent·recent identity | startup coordinator | parse, accept/ignore, readiness | 같은 업무 intent를 중복 적용하지 않고 history를 bounded하게 유지한다. |
| current route·back stack | router | navigation, back, modal dismiss | route와 별도 selected-record 정본을 만들지 않는다. |
| fixture record | in-memory repository | save, process restart | 같은 process 안에서만 유지되며 restart 뒤 fixture로 초기화된다. |
| edit draft | current form | input, validation, discard/save | validation·back 실패 뒤 사용자의 선택 전까지 보존한다. |

정상 경로는 준비된 앱에서 목록의 record를 눌러 detail로 가는 흐름이다. 대표 경계는 valid link cold start이고, 대표 실패는 malformed·stale intent가 repository readiness보다 먼저 도착하거나 같은 intent가 두 번 전달되는 경우다.

## public contract

정본은 [`../shared/src/contracts.ts`](../shared/src/contracts.ts)와 [`../shared/src/testkit.ts`](../shared/src/testkit.ts)다.

```ts
interface Stage01NavigationImplementation {
  normalizeRecordId(input: string): RecordIdResult;
  parseNavigationIntent(
    input: string,
    source?: NavigationIntentSource,
  ): NavigationIntent;
  intentKey(intent: NavigationIntent): string;
  decideDraftBack(dirty: boolean): "leave" | "confirm-discard";
}
```

public contract가 요구하는 행동은 다음과 같다.

- record id는 trim·canonical case·최대 64 code point·허용 문자 규칙으로 검증한다.
- malformed percent encoding은 throw하지 않고 `invalid` intent가 된다.
- `/records`, detail, edit, `/sync`, `/settings`만 명시적으로 해석한다.
- detail과 edit intent identity는 다르지만 delivery source만 다른 같은 destination은 중복으로 본다.
- clean draft는 leave, dirty draft는 사용자 확인 전 navigation을 막는다.
- parser와 decision policy는 Expo Router 없이 검사할 수 있다.

정답 문자열이나 특정 함수 본문은 contract가 아니다. 같은 외부 입력에서 같은 normalized meaning과 최종 route/fallback을 만들면 다른 구조를 사용할 수 있다.

## route와 화면 계약

최소 route:

```text
/records
/records/new
/records/[recordId]
/records/[recordId]/edit
/sync
/settings
```

| 화면 | 최소 관측 정보·행동 |
|---|---|
| 목록 | title, status, observed time, sync state, 새 기록·sync·settings 진입 |
| 상세 | record text, attachment placeholder, edit action |
| 새 기록·편집 | title, notes, status, observed time, save/cancel, validation 오류 focus |
| sync | 아직 SQLite outbox/network가 없음을 명시 |
| settings | app/runtime와 Stage 01 in-memory 저장소임을 명시 |

detail은 record object 전체를 navigation parameter로 요구하지 않는다. route는 stable id와 destination을 소유하고 repository가 entity를 조회한다. invalid id와 형식은 valid하지만 존재하지 않는 stale id를 서로 다른 application state로 처리한다.

## startup·link·restoration 계약

모든 진입 source가 직접 router를 조작하지 않고 다음 pipeline을 거친다.

```text
raw URL 또는 restoration path
→ NavigationIntent parsing
→ repository.ready()
→ target 존재 여부 확인
→ recent intent identity 확인
→ navigate 또는 안전한 /records fallback
```

### cold start

process와 JavaScript memory가 없는 상태에서 link가 app를 시작한다. repository fixture가 준비되기 전에 target을 missing으로 확정하지 않는다. valid fixture id는 detail/edit로 가고, memory에서 새로 만든 record의 오래된 link는 restart 뒤 stale target이므로 목록 fallback과 설명 가능한 notice를 남긴다.

### warm delivery

process와 현재 route·draft가 있는 상태에서 link가 도착한다. 새 intent가 unsaved edit를 덮을 수 있다면 현재 작업을 버릴지 보류할지 제품 정책을 적용한다. callback 완료 순서만으로 의도를 선택하지 않는다.

### restoration

initial external link가 없을 때 이전 route 후보를 restoration source로 다시 해석할 수 있다. route 형식과 현재 fixture target을 재검증하고, invalid·missing route를 그대로 복원하지 않는다. loading, toast, modal boolean과 in-flight promise는 복원 대상이 아니다.

### duplicate

같은 record·destination intent가 link와 notification 같은 다른 source에서 반복돼도 route effect를 두 번 적용하지 않는다. recent identity 저장소에는 용량 또는 만료 정책이 있어야 한다. process를 넘어 무한히 intent를 억제하거나 memory가 무제한 증가하는 구현은 허용하지 않는다.

## layout·입력·접근성 계약

- screen root가 safe area를 처리한다.
- keyboard가 현재 field, validation message와 save/cancel을 가리지 않는다.
- 작은 width와 큰 font scale에서 핵심 action이 잘리거나 겹치지 않는다.
- icon-only action에는 작업 의미의 label과 role이 있다.
- validation 실패 뒤 draft와 오류 field focus가 유지된다.
- modal이나 discard dialog를 닫으면 합리적인 control로 focus가 돌아온다.
- Android system back, predictive back와 iOS interactive gesture가 같은 dirty-draft decision을 사용한다.

특정 pixel·component tree보다 사용자가 같은 기록 작업을 끝낼 수 있는지를 검토한다.

## 정상·경계·대표 실패 시나리오

| ID | 초기 상태 | 사건 | 기대 application 결과 | 기대 관측 결과 |
|---|---|---|---|---|
| NAV-01 | warm `/records` | `forest-edge` 선택 | record 변화 없음, detail route | 해당 fixture detail 표시 |
| NAV-02 | process 없음 | valid fixture link | readiness 뒤 한 번 navigate | cold start로 target detail 표시 |
| NAV-03 | app background | 다른 valid link | warm intent 한 번 적용 | 새 target 또는 명시적 draft 보호 UI |
| NAV-04 | 어떤 route든 | malformed encoding/unknown route | `invalid`, record 변화 없음 | crash 없이 `/records`와 실패 이유 |
| NAV-05 | process restart | 이전에 memory에서 만든 id link/restoration | `missing-record`, record 추측 없음 | stale target 설명 후 `/records` |
| NAV-06 | 같은 target 처리 완료 | 같은 link를 연속 두 번 전달 | 두 번째 effect 없음 | stack 중복·form 재초기화 없음 |
| NAV-07 | dirty edit | system/header/gesture back | `confirm-discard` | 계속 편집 또는 명시적 discard 선택 |
| NAV-08 | invalid title·keyboard open | save | repository 변화 없음 | draft 유지, 오류 표시·focus 이동 |
| NAV-09 | modal/dialog open | background→active | 업무 save 추측 없음 | 현재 선택 가능한 상태로 복귀 |
| NAV-10 | 큰 font·작은 화면 | 목록→편집→오류 수정 | 같은 fixture/save 의미 | action·오류에 touch/보조기술로 도달 |

`stale`은 URL 문법은 맞지만 현재 repository·session·version에서 더는 적용할 수 없는 target을 뜻한다. `malformed`와 같은 parser 실패로 뭉치지 않는다.

## 자동 검사와 실패 거부

최소 자동 검사는 구현 모양이 아니라 다음 behavior를 관찰한다.

- canonical/empty/too-long/unsupported record id
- 정상 route, custom scheme, Expo development URL과 restoration source parsing
- malformed encoding과 unknown route가 `invalid`로 정규화됨
- detail/edit intent identity 차이와 delivery source 중복
- dirty/clean draft back decision
- valid/missing target route decision
- form validation 실패 시 repository save가 호출되지 않고 draft·오류가 남음
- icon/button의 accessible label·role·state

실행:

```sh
npm run test:stage01
npm run test:stage01:skeleton
npm run bundle:android
npm run bundle:ios
```

reference와 완료한 skeleton은 contract가 통과해야 한다. 최초 skeleton이나 의도적으로 parser·dedupe·back behavior를 깨뜨린 구현은 관련 검사가 거부해야 한다. bundle 성공은 JavaScript가 두 platform target으로 묶인다는 자동 근거이며 native development build 설치나 OS entry point를 보장하지 않는다.

## development build 실기기 관찰

Android와 iOS 각각에서 다음을 기록한다.

1. 설치된 development build를 종료한 뒤 development profile의 resolved scheme인 `fieldnotes-development://records/forest-edge`로 cold start한다.
2. app가 열린 상태에서 `fieldnotes-development://records/ridge-marker/edit`를 전달해 warm 경로를 확인한다.
3. malformed URL과 `fieldnotes-development://records/no-longer-present`를 열어 invalid/stale 결과를 구분한다. preview는 `fieldnotes-preview`, production은 `fieldnotes`를 사용하며, 설치한 profile과 다른 scheme은 `unexpected-scheme`으로 거부되어야 한다.
4. 같은 link를 두 번 전달해 stack·draft·screen effect가 반복되지 않는지 본다.
5. dirty edit에서 Android system back과 iOS back gesture를 수행한다.
6. process를 실제로 종료하고 launcher/restoration 후보로 다시 시작해 memory-only edit가 fixture로 초기화되는지 확인한다.
7. 작은 화면·큰 글자·software keyboard에서 저장 오류를 수정한다.
8. TalkBack/VoiceOver로 목록→상세→편집→오류 수정→뒤로 가기를 완료한다.

Metro reload나 Fast Refresh를 process 종료 evidence로 사용하지 않는다. simulator URL open 결과는 보조 evidence가 될 수 있지만 실제 기기·OS version을 대신했다면 그 범위를 `미검사`로 남긴다.

## 제출 evidence

```text
stage-01/
├── route-map.md
├── state-lifetime-table.md
├── intent-cases.md
├── android-navigation-recording-or-steps.md
├── ios-navigation-recording-or-steps.md
├── accessibility-notes.md
├── automatic-test-output.txt
└── known-limits.md
```

`intent-cases.md`에는 cold/warm/restoration, malformed/stale/duplicate 각각의 초기 route·repository 상태, 사건, normalized intent, route before/after와 final record/draft 상태를 적는다. recording에는 private URL parameter나 실제 사용자 data를 넣지 않는다.

사람 검토 질문:

1. link 실패 뒤 사용자가 왜 목록으로 왔고 무엇을 할 수 있는지 이해할 수 있는가?
2. dirty draft를 discard하지 않은 상태에서 외부 intent나 back이 내용을 잃게 하지 않는가?
3. Android와 iOS의 back·keyboard·screen reader 차이가 같은 업무 결과로 수렴하는가?
4. reference와 다른 구조를 택했다면 같은 owner와 불변식을 어디서 보존하는가?

## 자동 검증이 보장하지 않는 범위

- parser unit test는 OS가 custom scheme/universal link를 실제 binary에 전달하는지 보장하지 않는다.
- reference의 fixture success는 session·tenant authorization이나 durable state 복원을 보장하지 않는다.
- component accessibility assertion은 TalkBack/VoiceOver 발화 순서와 작업 완료를 보장하지 않는다.
- simulator는 physical device의 process pressure, gesture, keyboard와 vendor 차이를 모두 재현하지 않는다.
- development build 성공은 preview/production signing, update compatibility와 store 전달을 보장하지 않는다.

## 비범위

- 실제 authentication·authorization
- SQLite persistent record와 outbox
- photo picker·camera·location
- remote sync와 conflict
- notification delivery
- universal/app link 도메인 association 운영
- preview/production signing과 store build

## 완료 기준

- public navigation contract와 reference 기준 검사가 통과한다.
- cold·warm·restoration의 상태 owner와 intent 적용 순서가 문서화돼 있다.
- malformed·stale·duplicate intent가 crash·중복 navigation·업무 data 변경을 만들지 않는다.
- dirty draft의 system/header/gesture back 결과가 동일하다.
- 작은 화면·큰 글자·keyboard에서 record form을 완료한다.
- Android와 iOS development build에서 link와 back 결과를 각각 기록하거나 실행하지 못한 platform을 `미검사`로 남긴다.
- TalkBack·VoiceOver 실제 작업 결과와 자동 accessibility 검사의 한계를 기록한다.
- process restart 뒤 유지할 상태와 Stage 01에서 의도적으로 잃는 memory-only 상태를 구분한다.

이 Stage의 완료는 mobile runtime 전체나 stable을 자동 증명하지 않는다. 다음 Stage에서 같은 route와 public behavior를 유지한 채 in-memory repository를 SQLite·file·outbox 경계로 교체한다.
