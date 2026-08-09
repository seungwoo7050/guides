# layout·입력·접근성

같은 React 문법을 사용해도 모바일 화면은 웹 페이지의 작은 버전이 아니다. 손가락, 가상 keyboard, safe area, 화면 회전, 큰 글자, screen reader와 platform navigation이 같은 UI를 동시에 제약한다.

## 목표

이 장을 마치면 다음을 수행할 수 있어야 한다.

- CSS pixel과 물리 pixel을 혼동하지 않고 density-independent layout을 만든다.
- 고정 기기 이름이 아니라 현재 window와 content constraint로 화면을 바꾼다.
- safe area와 keyboard가 content와 action을 가리지 않게 한다.
- touch target, gesture, hardware keyboard와 screen reader action을 같은 기능 계약에 포함한다.
- font scale·언어 길이·오른쪽에서 왼쪽으로 쓰는 언어를 견디는 layout을 만든다.
- accessibility label·role·state·focus를 시각적 표현과 함께 갱신한다.
- Android와 iOS 실제 보조기술에서 주요 흐름을 검증한다.

연결 실습은 [Stage 01](../exercises/field-notes/specs/01-runtime-navigation.md)이다.

## 이 장의 책임 경계

HTML·CSS·React accessibility의 일반 원리는 [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), 상태·비동기 경쟁·접근성·성능 심화는 [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs)가 정본이다. 이 장은 그 원리를 safe area, software keyboard, touch·gesture, native accessibility tree와 Android/iOS 실제 보조기술에 적용하는 모바일 고유 차이를 다룬다.

| 상태·자원 | 소유자 | 바꾸는 사건 | 불변식 |
|---|---|---|---|
| window 크기·safe-area inset·font scale | OS/window | 회전, split view, display·text 설정 | layout 변화가 record·draft·선택 상태를 잃게 하지 않는다. |
| keyboard·focus·screen-reader focus | OS와 현재 screen | focus, submit, route/modal 전환 | 핵심 action과 오류에 도달할 수 있고 실패 뒤 draft를 보존한다. |
| visual·accessible state | component/view model | save, sync, permission과 validation 결과 | 색·아이콘·접근성 state가 같은 업무 상태에서 계산된다. |
| record·draft·sync 상태 | repository/application | edit, save, sync result | 화면 크기나 입력 수단이 업무 commit을 바꾸지 않는다. |

정상 경로는 기본 글자 크기의 touch 입력이다. 대표 경계는 큰 글자·작은 화면·hardware keyboard이고, 대표 실패는 keyboard나 modal 때문에 저장 action과 오류 focus를 잃는 경우다.

## 화면 크기보다 제약을 읽습니다

다음 분기는 오래 유지되지 않는다.

```ts
if (deviceName === "some-phone") {
  // special layout
}
```

기기 모델이 아니라 현재 사용 가능한 width, height, orientation, font scale과 input mode를 기준으로 한다. split screen, foldable, tablet, display zoom과 큰 글자 때문에 같은 기기에서도 제약은 달라진다.

```text
좁은 width
→ list와 detail을 별도 route로 표시

넓은 width
→ list-detail을 동시에 표시할 수 있음

큰 font scale
→ 한 줄 action을 여러 줄 또는 menu로 재배치
```

layout 선택이 업무 상태를 바꾸면 안 된다. width가 변했다고 편집 draft나 선택한 record를 잃지 않는다.

## Flexbox의 차이를 명시합니다

React Native의 layout은 Yoga를 통해 계산되며 웹 CSS와 이름이 같아도 기본값과 지원 범위가 다를 수 있다. 기억으로 옮기지 말고 현재 runtime의 문서를 확인한다. React Native style 숫자는 물리 pixel 고정값이 아니라 logical layout 단위이며, 실제 pixel density와 글자 scale은 별도 입력이다.

주요 원칙:

- 부모가 자식에게 제공하는 공간과 자식의 content size를 구분한다.
- `flex: 1`이 모든 overflow를 해결한다고 가정하지 않는다.
- scroll container 안의 child size와 바깥 layout을 별도로 검사한다.
- absolute positioning으로 keyboard·safe area 문제를 덮지 않는다.
- text가 길어지거나 font scale이 커질 때 잘림·겹침을 검사한다.

Field Notes 목록 행은 다음 정보의 우선순위를 가져야 한다.

```text
record title                 가장 먼저 읽힘
sync state와 status          시각·보조기술 모두 제공
observed time                보조 정보
attachment indicator         아이콘만 두지 않고 의미 제공
```

## safe area를 장식 여백으로 보지 않습니다

status bar, camera cutout, home indicator와 system gesture 영역은 플랫폼과 기기 상태에 따라 달라진다. 화면 root에서 safe area를 처리하고 nested component마다 임의 padding을 반복하지 않는다.

주의할 경우:

- edge-to-edge 화면에서 상단 header와 하단 action
- modal·sheet·full-screen camera
- keyboard가 열린 상태의 bottom action
- landscape와 tablet
- Android system navigation mode 차이

safe area inset을 업무 좌표로 저장하지 않는다. runtime layout 입력으로만 사용한다.

## keyboard는 화면 일부를 점유하는 외부 시스템입니다

편집 화면에서 keyboard가 열리면 다음 실패가 생긴다.

- 현재 input과 validation message가 가려진다.
- save/cancel action에 접근할 수 없다.
- 화면이 resize 또는 pan되면서 scroll 위치가 튄다.
- Android와 iOS의 keyboard avoidance 행동이 다르다.
- hardware keyboard에서는 on-screen keyboard 가정이 맞지 않는다.

권장 계약:

1. focus된 field가 보이는 영역으로 이동할 수 있다.
2. error summary에서 field로 이동할 수 있다.
3. save action은 keyboard를 닫지 않아도 접근 가능하다.
4. keyboard dismissal이 draft를 잃지 않는다.
5. submit 뒤 실패하면 focus와 draft를 보존한다.
6. 성공하면 route 이동과 focus 목적지를 명시한다.

`KeyboardAvoidingView` 하나로 해결됐다고 간주하지 않는다. 실제 form, scroll container, modal과 platform 조합에서 검사한다.

## touch interaction에 상태를 부여합니다

손가락은 mouse보다 정확하지 않고 hover가 없다. 작은 icon만 배치하고 설명을 hover에 숨길 수 없다.

각 action에 다음을 정의한다.

- 최소 touch area와 주변 action 사이 간격
- press feedback
- disabled와 busy의 차이
- double tap 또는 빠른 연속 tap 처리
- long press가 필수인지 선택 기능인지
- gesture가 screen reader·switch control·hardware keyboard에서도 대체 가능한지

예를 들어 sync button은 다음 상태를 구분한다.

```ts
type SyncActionState =
  | { kind: "ready" }
  | { kind: "running"; pendingCount: number }
  | { kind: "offline"; pendingCount: number }
  | { kind: "blocked"; reason: string };
```

`running` 동안 단순히 opacity만 낮추지 않는다. 접근성 state의 busy/disabled, 진행 설명과 취소 가능 여부를 함께 제공한다.

## visual component와 접근성 tree를 함께 설계합니다

screen reader는 화면 픽셀을 그대로 읽지 않는다. component의 role, label, value, state와 focus order를 사용한다.

### label

아이콘 버튼에 눈으로 보이는 이름이 없다면 작업 결과를 설명하는 label을 제공한다.

```tsx
<Pressable
  accessibilityRole="button"
  accessibilityLabel="사진 추가"
  accessibilityHint="카메라 또는 사진 선택 화면을 엽니다"
  onPress={openAttachmentPicker}
>
  <CameraIcon />
</Pressable>
```

label은 구현 수단이 아니라 사용자 작업을 말한다. `camera icon`보다 `사진 추가`가 낫다.

### role과 state

- action은 button 역할을 가진다.
- 선택된 filter는 selected 상태를 제공한다.
- sync 중에는 busy 상태와 진행 문구를 제공한다.
- validation error는 field 관계와 함께 읽힌다.
- decorative image는 focus 대상이 되지 않는다.

시각적 색상 변화와 접근성 state가 서로 다른 source에서 계산되지 않게 한다.

### focus

route 이동, modal open/close, 오류 발생과 optimistic 결과가 focus에 영향을 준다.

```text
새 화면 진입
→ 화면 제목 또는 첫 의미 있는 영역

modal 닫힘
→ modal을 연 control로 복귀

저장 실패
→ error summary 또는 첫 오류 field

record 삭제
→ 목록의 합리적인 다음 항목 또는 목록 제목
```

보조기술 focus를 강제로 자주 이동시키면 맥락을 잃는다. 사용자의 현재 위치와 작업 결과를 기준으로 한다.

## 동적 변경을 조용히 숨기지 않습니다

offline 저장, sync 성공, conflict 발생처럼 화면 일부가 바뀌어도 screen reader 사용자가 알아야 한다.

- 짧은 상태 변화는 platform에 맞는 live region 또는 announcement를 사용한다.
- 오류를 toast에만 두지 않고 화면에 지속 가능한 메시지와 다음 action을 남긴다.
- 여러 record가 동시에 sync돼도 모든 항목을 연속 announcement하지 않는다.
- background에서 바뀐 상태는 app 복귀 시 요약한다.

React Native의 live-region·announcement API 지원 범위는 Android와 iOS가 같지 않다. 공통 prop 이름만 확인하지 말고 TalkBack과 VoiceOver의 실제 발화·중복 여부를 각각 검사한다.

예:

```text
오프라인으로 저장했습니다. 연결되면 동기화합니다.
동기화 충돌이 있습니다. 서버 기록과 내 변경을 검토하십시오.
```

## 큰 글자와 긴 번역을 정상 입력으로 둡니다

`numberOfLines={1}`로 모든 문제를 숨기지 않는다. 정보 우선순위에 따라 줄바꿈, 축약, detail 이동을 결정한다.

검사 항목:

- 최대 font scale에서 핵심 action과 title이 보이는가?
- button text가 길어져도 다른 action을 덮지 않는가?
- 날짜·숫자·단위가 locale에 맞는가?
- right-to-left에서 icon 방향과 navigation 의미가 맞는가?
- uppercase 변환이나 letter spacing이 특정 언어를 깨지 않는가?
- color contrast와 색상 이외의 상태 표현이 있는가?

문자열 길이를 영어 기준으로 고정하지 않는다.

## form은 mobile interruption을 견뎌야 합니다

Field Notes 편집 draft는 사용자가 전화를 받거나 다른 앱으로 이동해도 쉽게 사라지지 않아야 한다.

가능한 정책:

```text
field 입력
→ memory draft 즉시 갱신
→ 짧은 debounce 또는 명시적 checkpoint로 local draft 저장
→ 명시적 Save에서 업무 record와 outbox transaction
```

자동 draft와 명시적 save의 의미를 구분한다.

- draft checkpoint는 unfinished input 복구를 위한 것
- save는 record version과 sync 대상이 되는 업무 사건

validation은 입력 중 안내와 저장 차단을 구분한다. keyboard type이나 UI control이 올바른 값만 만든다고 믿지 않고 domain parsing을 별도로 수행한다.

## list는 데이터 양과 상호작용을 함께 검토합니다

긴 목록에서 모든 item을 한 번에 render하거나 각 row가 무거운 image와 effect를 소유하면 scroll frame을 잃는다.

설계 기준:

- 안정적인 key는 record identity를 사용한다.
- row render가 global sync tick마다 모두 바뀌지 않게 selector를 제한한다.
- image thumbnail은 화면 크기에 맞는 decode·cache 정책을 가진다.
- pagination과 local query가 같은 sort contract를 사용한다.
- item의 accessibility order가 visual order와 일치한다.
- list empty, loading, stale, error와 offline state를 구분한다.

성능 수치는 [테스트·성능·관측성](09-testing-performance-and-observability.md)에서 release build로 측정한다.

## Android와 iOS에서 같은 모양을 강제하지 않습니다

공통 design language는 유지하되 platform convention을 무시하지 않는다.

- Android system back과 iOS back gesture의 기대가 다르다.
- modal, picker, permission dialog와 navigation animation이 다르다.
- font rendering과 control behavior가 다르다.
- accessibility traversal과 announcement가 다를 수 있다.

동일한 pixel보다 동일한 작업 결과와 상태 의미를 우선한다. platform-specific file이나 component가 필요하면 이유와 공통 contract를 문서화한다.

## 검사 matrix

Stage 01에서 최소 다음 조합을 확인한다.

| 축 | 사례 |
|---|---|
| 화면 | 좁은 phone, 넓은 phone 또는 tablet/split view |
| 방향 | portrait, landscape가 지원 범위라면 landscape |
| 글자 | 기본, 큰 font scale |
| 입력 | touch, software keyboard, 가능한 경우 hardware keyboard |
| 보조기술 | TalkBack, VoiceOver |
| 상태 | empty, 긴 title, validation error, sync busy, offline |
| platform | Android와 iOS |

screenshot만으로 screen reader focus와 keyboard 접근을 증명할 수 없다. 실제 interaction 기록을 남긴다.

## 검증 범위와 한계

component 검사는 label·role·state와 visible result를 빠르게 확인할 수 있다. screenshot은 clipping·safe area·큰 글자 배치를 비교하는 근거가 되고, 실제 interaction 기록은 keyboard·gesture·focus 이동을 검증한다.

다음은 자동 검사나 한 종류의 evidence로 보장할 수 없다.

- accessibility tree snapshot은 실제 발화 순서와 사용자의 작업 완료를 보장하지 않는다.
- screenshot은 focus, announcement, switch control과 hardware keyboard 조작을 보장하지 않는다.
- simulator 결과는 실제 기기의 font 설정, keyboard, system gesture와 보조기술 차이를 모두 재현하지 않는다.
- 한 화면 크기의 성공은 split view·rotation·최대 글자 크기를 보장하지 않는다.

Android TalkBack과 iOS VoiceOver에서 같은 업무 결과를 직접 수행하고, 검사하지 못한 device·입력·언어 범위를 acceptance matrix에 남긴다.

## Stage 01 완료 기준

- list/detail/edit가 작은 화면과 큰 font scale에서 핵심 작업을 보존한다.
- safe area와 keyboard가 action·오류를 가리지 않는다.
- icon-only action에 label과 role이 있다.
- 저장 성공·실패·offline 상태가 시각·보조기술 모두에 전달된다.
- modal 또는 picker 뒤 focus 목적지가 정의돼 있다.
- TalkBack과 VoiceOver에서 record 생성·편집·뒤로 가기를 완료했다.
- Android와 iOS 차이, 미검사 조합과 evidence 한계를 acceptance matrix에 기록했다.

다음은 화면이 어떤 경로로 열리고, 외부 link·알림·재시작 뒤 어느 상태를 복원할지 정한다. [navigation·link·상태 복원](03-navigation-links-and-state-restoration.md)으로 이어간다.
