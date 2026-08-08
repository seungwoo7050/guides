# 테스트·접근성·성능

검증의 목적은 테스트 수를 늘리는 것이 아니라 **변경이 깨뜨릴 수 있는 계약을 가장 낮고 결정적인 계층에서 잡는 것**이다. 형 검사, 순수 unit test, production build와 실제 browser는 서로 다른 증거를 제공한다.

## 목표

이 장을 마치면 다음을 수행할 수 있어야 한다.

- 기능의 가장 큰 위험을 먼저 적고 검사 계층을 선택한다.
- 고정된 sleep 없이 응답 순서와 실패를 결정적으로 재현한다.
- accessible name, keyboard와 focus transition을 실제 browser로 검사한다.
- 320px, 200% 확대, 긴 문자열과 reduced motion을 검증한다.
- JavaScript response body와 DOM node 수에 budget을 둔다.
- production build와 실제 production server를 검사 대상으로 사용한다.

연결 실습은 [Stage 04](../exercises/project-catalog/specs/04-testing-accessibility-performance.md)다.

## 위험에서 시작합니다

구현 파일보다 먼저 실패 결과를 적는다.

| 위험 | 사용자 영향 | 첫 검사 계층 |
| --- | --- | --- |
| URL과 입력이 어긋남 | 공유·reload·back이 깨짐 | query unit + browser navigation |
| malformed response를 신뢰함 | 잘못된 화면 또는 runtime crash | contract unit + routed response |
| 오래된 응답이 최신 결과를 덮음 | 사용자가 다른 조건의 데이터를 봄 | controlled browser network |
| conflict에서 draft를 잃음 | 사용자의 작업 손실 | browser mutation failure |
| cancel 후 focus를 잃음 | keyboard 사용자가 다음 위치를 찾지 못함 | production browser |
| client bundle 급증 | 초기 표시와 입력이 느려짐 | production body budget |

각 테스트에는 “어떤 결함을 막는가?”를 한 문장으로 설명할 수 있어야 한다. 내부 함수 호출 횟수만 확인하고 사용자 계약을 놓치지 않는다.

## 검사 계층을 나눕니다

| 계층 | 잘 잡는 문제 | 잡지 못하는 문제 |
| --- | --- | --- |
| 정적 검사 | syntax, interface, 누락 branch | runtime 외부 데이터 |
| route type + typecheck | Next route signature, module 경계 | 실제 browser behavior |
| 순수 unit | parser, state transition, coordinator | DOM, layout, history engine |
| HTTP handler test | status, body contract, validation | 실제 bundle과 focus |
| production build | server/client graph, route generation | 실제 사용자 상호작용 |
| browser E2E | history, network, focus, viewport | 내부 알고리즘의 모든 경계 |
| standalone smoke | 실제 start, health, release, secret boundary | 복잡한 전체 사용자 흐름 |

가장 낮은 계층에서 충분히 잡히는 경계를 E2E로만 검사하지 않는다. 반대로 focus, overflow와 history는 DOM 모방 환경만으로 단정하지 않는다.

## Typecheck 전에 route type을 생성합니다

Next.js route와 navigation type은 build output에 의존할 수 있다. 깨끗한 checkout에서도 형 검사가 재현되도록 type generation을 script에 포함한다.

```json
{
  "scripts": {
    "typecheck": "next typegen && tsc --noEmit"
  }
}
```

생성 디렉터리를 commit하지 않고도 동일 명령으로 개발자와 CI가 준비할 수 있어야 한다.

## Network test는 시간을 제어합니다

다음 검사는 불안정하다.

```ts
await new Promise((resolve) => setTimeout(resolve, 500));
```

실행 환경이 느리면 실패하고 빠르면 시간을 낭비한다. 응답을 명시적으로 보류하고 테스트가 원하는 순서에 해제한다.

```ts
let releaseSlow: (() => void) | undefined;
const slowRequest = new Promise<void>((resolve) => {
  releaseSlow = resolve;
});

await page.route("**/api/projects?*", async (route) => {
  const query = new URL(route.request().url()).searchParams.get("q");
  if (query === "old") await slowRequest;
  await route.continue();
});
```

검사 흐름:

```text
old 요청을 보류
→ new 요청을 시작하고 결과 확인
→ old 응답을 해제
→ 화면이 new 결과를 유지하는지 확인
```

취소 자체를 확인하더라도 stale result guard의 효과도 별도로 확인한다.

## 예상하지 않은 요청을 실패시킵니다

network mock은 등록한 요청에만 응답하고 나머지는 통과시키는 대신, 해당 test 범위에서 예상하지 않은 application request를 실패로 만들 수 있다. 잘못된 URL, 중복 fetch와 숨은 analytics 호출을 빠르게 발견한다.

다만 framework asset, HMR와 browser 자체 요청까지 무차별적으로 막지 않는다. production server에서 application API pattern을 구체적으로 지정한다.

## 접근성은 구조와 시간 흐름입니다

자동 accessibility scanner는 이름 없는 control과 잘못된 ARIA를 잘 찾지만 focus transition의 의미를 모두 판단하지 못한다.

### 의미 구조

- 하나의 주요 `<main>`과 논리적인 heading 순서
- search form과 연결된 label
- navigation에는 link, action에는 button
- project 반복 항목은 list와 article
- 상태 메시지는 적절한 live region

### Keyboard와 focus

편집 흐름을 실제 keyboard로 검사한다.

```text
Tab으로 “제목 수정” 도달
→ Enter로 editor 열기
→ input에 focus
→ draft 입력
→ Escape 또는 취소
→ 처음 edit button으로 focus 복귀
```

저장 성공 뒤에도 edit button으로 돌아갈 수 있어야 한다. 반면 일반 실패와 conflict에서는 editor를 유지하므로 input focus와 draft를 보존한다.

`autoFocus`만으로 전체 계약을 해결했다고 보지 않는다. dialog, conditional editor와 navigation 뒤 focus가 어디에 있어야 하는지 사용자 흐름으로 결정한다.

### Focus indication

focus가 존재해도 눈으로 구분되지 않으면 keyboard 사용자가 현재 위치를 알 수 없다. 실제 computed style에서 outline width, style과 색 대비가 사라지지 않았는지 확인한다.

## 작은 화면과 확대를 함께 봅니다

반응형은 device width만의 문제가 아니다. 200% 확대는 유효한 CSS viewport를 줄이고 글자와 control을 키운다.

검사 조건:

- 320px × 720px
- 640px viewport에 200% zoom
- 80자의 공백 없는 title
- browser 기본 font 확대
- input과 select의 긴 값

다음을 단언한다.

```ts
await page.evaluate(() =>
  document.documentElement.scrollWidth <= document.documentElement.clientWidth
);
```

페이지 전체 overflow가 없다는 사실뿐 아니라 article, heading와 form control의 bounding box가 viewport 안에 있는지도 확인한다.

CSS의 기본 안전장치:

```css
*,
*::before,
*::after {
  box-sizing: border-box;
}

input,
select,
textarea {
  min-width: 0;
  max-width: 100%;
}

article {
  overflow-wrap: anywhere;
}
```

## Reduced motion을 실제 style로 검사합니다

media query 문자열 존재만 검사하지 않는다. browser context에서 reduced motion을 활성화하고 transition과 animation의 computed duration이 사실상 0인지 확인한다.

```ts
await page.emulateMedia({ reducedMotion: "reduce" });
```

기능 이해에 필요한 상태 변화까지 제거할 필요는 없지만 장식적인 motion은 줄여야 한다.

## 성능 예산은 변경 전에 둡니다

실습은 환경 차이에 덜 민감한 두 budget을 사용한다.

```json
{
  "maximumInitialJavaScriptBytes": 800000,
  "maximumDomNodes": 180
}
```

- JavaScript budget은 첫 route가 요청한 script response **body byte 합계**를 측정한다.
- DOM budget은 첫 화면의 element 수를 측정한다.

전송 압축 byte, parse·execute cost와 실제 사용자 지표를 대신하는 완전한 성능 모델은 아니다. 그러나 작은 feature 때문에 client boundary가 넓어지거나 DOM이 폭증하는 회귀를 빠르게 막는다.

예산은 한 번 정한 숫자를 영구적인 진리로 취급하지 않는다. 대표 device, network와 실제 사용자 지표를 바탕으로 근거 있게 갱신한다.

## Production server를 검사합니다

개발 서버는 error overlay, HMR와 development-only behavior를 사용한다. E2E는 build한 결과를 `next start`로 실행한다.

```text
고정 설치
→ typecheck와 unit test
→ next build
→ next start
→ browser E2E
```

Playwright의 `webServer`는 기존 development server를 재사용하지 않고 매 실행 고유 port에서 production server를 시작한다. 실패 시 trace를 남기고 test data reset endpoint는 명시적인 test token이 있을 때만 열린다.

## 불안정한 검사 원인을 제거합니다

- 고정 sleep 대신 URL, response, live region과 DOM 상태를 기다린다.
- test마다 server data를 초기화한다.
- cookie, local/session storage와 route handler를 격리한다.
- browser console error와 page error를 수집한다.
- retry로 결정적인 버그를 숨기지 않는다.
- 실패 trace, screenshot과 server output을 보존한다.

## Stage 04 완료 기준

```sh
pnpm exercise:verify:04
```

다음을 확인한다.

- search와 edit를 keyboard만으로 완료할 수 있다.
- cancel과 성공 뒤 focus가 edit button으로 복구된다.
- conflict와 일반 실패에서 draft와 input focus가 유지된다.
- focus-visible indicator가 실제 computed style에 존재한다.
- 320px, 200% 확대와 긴 title에서 horizontal overflow가 없다.
- reduced motion preference가 computed duration에 반영된다.
- initial JavaScript body와 DOM node가 budget을 넘지 않는다.
- 모든 검사는 production build와 production server를 사용한다.

## 다음 단계

브라우저 기능이 검증되면 배포 인프라가 사용할 산출물과 상태 계약을 만들어야 한다. [운영 런타임 계약](05-production-runtime-contract.md)으로 이어간다.
