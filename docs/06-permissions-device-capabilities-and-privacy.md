# permission·기기 기능·privacy

permission은 설치 시 한 번 통과하는 설정이 아니다. 사용자는 기능을 처음 사용할 때 허용하거나 거절하고, 제한된 범위만 주거나, 나중에 Settings에서 철회할 수 있다. device에 해당 기능이 없을 수도 있다.

이 장은 `cybersecurity`의 위협 모델이나 플랫폼 privacy 심사 전체를 소유하지 않는다. 이 브랜치가 소유하는 범위는 camera·foreground location 같은 기기 기능을 **최소 권한, lifecycle과 실패 상태를 가진 mobile adapter**로 연결하는 데까지다.

## 목표

- capability 존재와 permission 상태를 구분한다.
- permission을 사용자 의도가 있는 순간에 요청한다.
- 미결정·허용·거절·제한·다시 묻기 불가·unavailable을 제품 상태로 처리한다.
- system picker·camera·location 결과를 process 재생성과 함께 복구한다.
- file ownership, metadata, retention과 upload privacy를 설계한다.
- config plugin과 native permission 설명이 binary에 들어가는 과정을 추적한다.
- biometric 확인과 server authentication을 혼동하지 않는다.
- data inventory와 store privacy declaration의 근거를 만든다.

연결 실습은 [Stage 03](../exercises/field-notes/specs/03-media-permissions.md)이다.

## capability와 permission은 다릅니다

```text
capability
- device에 camera가 있는가?
- 현재 OS/version에서 API를 사용할 수 있는가?
- build에 필요한 native module이 들어 있는가?

permission
- 사용자가 이 app에 현재 허용했는가?
- 전체/제한 access인가?
- 다시 요청할 수 있는가?
```

camera permission이 granted여도 hardware 오류나 다른 app 사용 때문에 실패할 수 있다. permission이 denied여도 photo picker처럼 별도 system UI를 통해 제한된 파일 선택은 가능할 수 있다.

availability와 permission을 한 union으로 섞으면 `available-but-denied`, `unavailable-with-no-permission-concept`를 표현하지 못한다. 두 축을 분리한다.

```ts
type CapabilityAvailability =
  | { kind: "checking" }
  | { kind: "available"; constraints?: string[] }
  | { kind: "unavailable"; reason: "hardware" | "os" | "build" | "policy" };

type PermissionAccess =
  | { kind: "not-required" }
  | { kind: "undetermined"; canAskAgain: true }
  | { kind: "granted" }
  | { kind: "limited"; scope: string }
  | { kind: "denied"; canAskAgain: boolean }
  | { kind: "restricted"; reason: string };

type CapabilityAccess = {
  availability: CapabilityAvailability;
  permission: PermissionAccess;
};
```

platform raw value를 adapter에서 이 상태로 바꾼다.

## app 시작과 동시에 모든 permission을 요청하지 않습니다

startup에서 camera·photo·location·notification을 연속 요청하면 사용자는 이유를 알기 어렵고 거절 가능성이 높다.

권장 흐름:

```text
사용자가 "사진 추가" 선택
→ 기능이 왜 필요한지 현재 화면 문맥에서 설명
→ 기존 상태 확인
→ 필요하면 OS permission 요청
→ 허용이면 기능 실행
→ 거절·제한이면 대체 경로 제공
```

permission 전 안내 화면이 OS dialog를 흉내 내거나 사용자를 압박하면 안 된다. 실제 기능, 수집 범위와 거절 시 가능한 작업을 설명한다.

## permission state를 다시 읽습니다

사용자는 app 밖 Settings에서 권한을 바꿀 수 있다. app 복귀 시 관련 capability를 재조회한다.

- 이전 `granted` 값을 영구 cache하지 않는다.
- 권한이 철회되면 열린 camera view와 background location을 정리한다.
- `canAskAgain === false`이면 같은 dialog를 반복하지 않고 Settings 이동 안내를 제공한다.
- Settings에서 돌아와도 자동으로 민감 기능을 실행하지 않고 사용자의 원래 action을 다시 확인한다.

## camera와 photo picker의 책임을 구분합니다

### camera

- 실제 camera hardware와 preview 수명
- camera permission
- 촬영 중 app background·전화·screen lock
- 임시 cache file
- orientation·metadata·size

### system photo picker

- 사용자가 선택한 media에 대한 제한된 access
- 지원 OS에서는 보관함 전체 permission 없이 선택한 항목만 전달하는 경로
- provider가 반환한 URI와 file metadata의 불완전성
- Android Activity/process 재생성
- iCloud/remote provider처럼 즉시 local bytes가 없을 가능성

Field Notes는 가능한 경우 system picker를 기본으로 사용하고, 직접 촬영은 명시적 action으로 분리한다.

## picker 결과를 durable file로 전환합니다

system API가 반환한 URI가 영구 접근 가능하다고 가정하지 않는다.

```text
result 수신
→ canceled/error/success 구분
→ size·mime·dimension의 신뢰 수준 확인
→ app-owned staging file로 copy
→ checksum 계산
→ DB attachment transaction
→ UI에 local attachment 표시
```

원본 filename, MIME과 extension은 서로 모순될 수 있다. upload server에서도 content를 다시 검증해야 한다.

Android에서 picker를 다녀오는 동안 activity가 파괴될 수 있다. platform이 pending result 복구 API를 제공하면 startup reconciliation에 포함하고 같은 결과를 두 번 연결하지 않도록 identity를 둔다.

## 위치는 정확도와 시점을 계약으로 만듭니다

`위치 권한 있음`만으로 record coordinate의 품질을 설명할 수 없다.

필요한 값:

- 측정 timestamp
- latitude/longitude
- accuracy 또는 uncertainty
- foreground/background source
- last-known인지 새 측정인지
- 사용자가 선택했는지 자동 수집인지

Field Notes 기본 범위는 **사용자가 record 편집 화면에서 선택적으로 한 번 요청하는 foreground location**이다. background tracking은 제외한다.

권한이 없거나 정확도가 낮아도 text record 저장은 가능해야 한다. 위치는 핵심 record 생성의 필수 조건으로 두지 않는다.

## background permission은 별도 제품입니다

background location, microphone 지속 사용 같은 capability는 단순히 permission 하나를 추가하는 작업이 아니다.

- OS 제한과 foreground service
- battery 영향
- 명확한 사용자 가치
- store review와 privacy 설명
- 종료·pause control
- notification/indicator
- data retention과 access

이 브랜치의 capstone은 background location을 구현하지 않는다. 필요하면 별도 프로젝트에서 위 계약을 먼저 문서화한다.

## system picker와 library access의 제한 상태를 구분합니다

system photo picker는 보통 app에 보관함 전체 access를 주지 않고 사용자가 고른 항목만 전달한다. 이는 photo-library API의 `limited` permission과 같은 상태가 아니다. 전체 library를 조회하는 별도 기능을 선택한 경우에만 platform의 `limited` 상태를 처리한다.

- library API의 `limited`를 `denied`로 처리하지 않는다.
- 선택한 asset의 identifier나 filename이 항상 존재한다고 가정하지 않는다.
- system picker를 다시 열어 추가 선택할 수 있는 UI를 제공한다.
- app가 전체 library 목록을 볼 수 있다고 가정하지 않는다.

기능은 “전체 보관함 접근”이 아니라 “사용자가 선택한 사진을 record에 연결”이라는 최소 권한으로 설계한다.

## metadata와 privacy를 함께 처리합니다

사진에는 다음이 포함될 수 있다.

- EXIF 촬영 시각
- 기기·camera 정보
- 방향
- 위치 metadata
- thumbnail과 편집 정보

server upload 전에 어떤 metadata를 보존·제거할지 결정한다. Field Notes에서 사용자가 별도로 위치를 선택했다면 이미지 EXIF 위치를 자동 수집하지 않는 정책을 고려한다.

로그와 crash report에 local file URI, signed URL, record text와 정확한 위치를 넣지 않는다.

## biometric은 인접한 local gate입니다

biometric 인증 자체는 이 브랜치의 필수 결과물이 아니다. 이미 존재하는 credential adapter를 읽을 때 camera/location permission이나 server authorization과 섞지 않기 위한 경계 예시로만 다룬다.

Face ID·Touch ID·Android biometric prompt로 local data 접근을 잠글 수 있다. 하지만 다음을 보장하지 않는다.

- server account가 아직 유효하다.
- 다른 device session이 폐기되지 않았다.
- token 자체가 안전하게 회전됐다.
- 사용자가 server authorization을 가진다.

권장 흐름:

```text
platform biometric로 local credential 사용 승인
→ secure storage에서 credential 읽기
→ 필요하면 server refresh·authorization
→ private data 표시
```

biometric unavailable·not enrolled·cancel·lockout에 PIN/재로그인 같은 fallback을 명시한다.

## native configuration은 build 입력입니다

permission message와 Android manifest/iOS plist 설정은 runtime JavaScript가 아니라 native binary에 들어간다.

CNG를 사용한다면:

```text
app config의 plugin·permission 설명
→ prebuild/config plugin
→ AndroidManifest·Info.plist 등 생성
→ development/release binary build
```

문자열을 바꿨는데 Expo Go에서 화면만 다시 load해 확인하는 것은 검증이 아니다. 새 development build를 만들고 설치된 app의 실제 dialog를 확인한다.

불필요 permission이 dependency 때문에 추가되는지도 generated manifest와 store declaration에서 검토한다.

## 데이터 inventory를 만듭니다

capstone release 전에 다음 표를 실제 값으로 채운다.

| 데이터 | 목적 | 수집 trigger | local 위치 | remote 전송 | 보존·삭제 | 사용자 control |
|---|---|---|---|---|---|---|
| record text | 현장 기록 | Save | SQLite | sync 시 | 정책 | 편집·삭제 |
| photo | 증거 첨부 | 사진 추가 | app file | upload 시 | 정책 | 제거·삭제 |
| foreground location | 선택적 위치 | 위치 추가 | SQLite | sync 시 | record와 동일 | 거절·제거 |
| session credential | 인증 | login/refresh | secure storage | auth request | logout/revoke | logout |
| telemetry | 안정성 | 오류·성능 | 제한적 buffer | 조건부 | 단기 | privacy policy |

실제 코드, backend, store privacy form과 표가 일치해야 한다.

## permission 실패 UX

### 거절했지만 다시 물을 수 있음

- 기능 없이 가능한 대체 작업 제공
- 다음 사용 action 때 다시 설명
- 즉시 반복 dialog 금지

### 다시 물을 수 없음

- Settings에서 바꾸는 방법
- 돌아온 뒤 상태 재조회
- 기능 없이 가능한 범위

### 제한됨

- 현재 가능한 범위 표시
- 전체 access가 정말 필요한 경우에만 이유 설명

### capability 없음

- 숨기기보다 필요한 경우 이유와 대체 입력 제공
- unsupported device를 crash로 만들지 않음

## Stage 03 실패 주입

- 첫 요청 거절
- `canAskAgain=false`
- limited photo access
- system picker cancel
- picker 중 activity/process 종료
- zero-byte 또는 너무 큰 file
- unsupported MIME
- storage full
- file copy 뒤 DB transaction 실패
- location timeout·낮은 정확도
- app background 중 camera 중단
- Settings에서 permission 철회 뒤 복귀

## Stage 03 완료 기준

- permission을 기능 action에서 요청하고 startup에서는 요청하지 않는다.
- denied·limited·unavailable 상태에서도 text record를 저장한다.
- picker/camera 결과를 app-owned file로 copy한 뒤 DB에 연결한다.
- process recreation 뒤 pending picker result를 중복 없이 조정한다.
- location에는 timestamp와 accuracy가 있고 선택 기능이다.
- permission message와 native config를 development build에서 확인한다.
- data inventory에 local·remote·retention·사용자 control이 기록돼 있다.
- 로그와 오류 보고에 사진·위치·credential이 노출되지 않는다.

mock adapter 검사는 normalized 상태와 대체 행동을 보장할 뿐, 실제 OS dialog 문구·Settings 전환·camera hardware·provider URI 수명·store privacy declaration을 보장하지 않는다. Android와 iOS development build의 화면·로그·generated configuration을 사람이 검토한다.

다음은 앱이 보이지 않는 동안 작업과 알림을 어떻게 다루는지, 그리고 왜 background를 정확성 보장으로 사용하면 안 되는지 설명한다. [background·notification·lifecycle](07-background-work-notifications-and-lifecycle.md)으로 이어간다.
