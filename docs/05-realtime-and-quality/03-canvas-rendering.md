# Canvas 렌더링

`<canvas>`는 DOM 요소처럼 항목마다 노드를 유지하지 않습니다. 한 번 그린 픽셀은 application state가 아니므로, 화면을 다시 그릴 수 있는 별도 정본이 필요합니다. React와 Canvas를 함께 사용할 때는 React가 상태와 수명을, Canvas renderer가 픽셀 그리기를 담당하게 분리합니다.

## 목표

- logical board 좌표와 CSS·device pixel 좌표를 구분합니다.
- application state에서 매 frame 화면을 재생성합니다.
- React 수명과 imperative renderer를 연결합니다.
- pointer 입력을 좌표 변환하고 server 범위 검증과 결합합니다.
- 성능 최적화 전에 측정하고 접근 가능한 대안을 제공합니다.

## Canvas는 상태 저장소가 아닙니다

```ts
interface BoardViewState {
  items: BoardItem[];
  cursors: RemoteCursor[];
  selection: string | null;
  viewport: Viewport;
}
```

renderer는 이 값을 받아 그립니다.

```ts
function renderBoard(ctx: CanvasRenderingContext2D, state: BoardViewState): void {
  ctx.clearRect(0, 0, state.viewport.width, state.viewport.height);
  for (const item of state.items) drawItem(ctx, item);
  for (const cursor of state.cursors) drawCursor(ctx, cursor);
  if (state.selection) drawSelection(ctx, state.selection, state.items);
}
```

pixel을 읽어 업무 상태를 복원하지 않습니다. reconnect snapshot이나 React state 변경 후 언제든 전체를 다시 그릴 수 있어야 합니다.

## 세 좌표계를 구분합니다

1. **board 좌표**: 업무 상태가 저장되는 논리 좌표
2. **CSS pixel**: 화면에서 보이는 element 크기
3. **device pixel**: 실제 backing buffer 해상도

고밀도 화면에서 선명하게 그립니다.

```ts
function resizeCanvas(canvas: HTMLCanvasElement, width: number, height: number): CanvasRenderingContext2D {
  const ratio = window.devicePixelRatio || 1;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("2D canvas를 사용할 수 없습니다.");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return ctx;
}
```

`scale()`을 resize마다 누적 호출하면 좌표가 계속 커질 수 있습니다. `setTransform`으로 기준을 다시 설정합니다.

## pointer 좌표 변환

```ts
function pointerToBoard(event: PointerEvent, canvas: HTMLCanvasElement, view: Viewport) {
  const rect = canvas.getBoundingClientRect();
  const cssX = event.clientX - rect.left;
  const cssY = event.clientY - rect.top;
  return {
    x: (cssX - view.offsetX) / view.zoom,
    y: (cssY - view.offsetY) / view.zoom
  };
}
```

CSS transform, zoom, scroll과 board pan을 모두 고려합니다. client가 계산한 좌표는 신뢰 경계 밖 값이므로 server도 finite number, board bounds와 item policy를 다시 검사합니다.

## React와 renderer 연결

Canvas element reference와 drawing effect를 사용합니다.

```tsx
function BoardCanvas({ state }: { state: BoardViewState }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useLayoutEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = resizeCanvas(canvas, state.viewport.width, state.viewport.height);
    renderBoard(ctx, state);
  }, [state]);

  return <canvas ref={ref} aria-label="협업 보드" />;
}
```

상태 크기가 크면 매 변경마다 모든 객체를 그리는 비용을 측정합니다. 우선 정답이 명확한 전체 redraw로 시작하고, 실제 frame budget 문제가 확인된 뒤 dirty region, offscreen layer나 spatial index를 도입합니다.

## animation loop

cursor interpolation이나 drag preview처럼 frame마다 갱신할 때 `requestAnimationFrame`을 사용합니다.

```ts
let frame = 0;
function tick(time: number) {
  renderInterpolated(time);
  frame = requestAnimationFrame(tick);
}
frame = requestAnimationFrame(tick);
```

component cleanup에서 `cancelAnimationFrame(frame)`을 호출합니다. 여러 effect가 loop를 중복 시작하지 않게 합니다. background tab에서는 animation이 느려질 수 있으므로 업무 timeout과 frame time을 같은 것으로 보지 않습니다.

## hit testing

pointer가 어떤 항목을 가리키는지 application geometry로 판정합니다.

```text
화면 좌표 → board 좌표
→ candidate 검색
→ shape별 hit test
→ topmost item 선택
```

항목이 많으면 역순 전체 순회에서 spatial index로 발전할 수 있습니다. Canvas 색상 픽셀을 읽는 hidden hit map도 가능하지만 확대, anti-aliasing과 유지보수 비용을 고려합니다.

## 텍스트와 편집

Canvas 텍스트 입력은 접근성, selection, IME와 clipboard를 직접 구현해야 합니다. 실제 메모 편집은 위치를 맞춘 HTML input·textarea overlay를 사용하는 편이 적절할 수 있습니다.

```text
Canvas → 배경·도형·선택 표시
DOM     → toolbar·form·dialog·텍스트 편집·상태 알림
```

모든 UI를 Canvas로 옮기지 않습니다.

## 접근성

Canvas 픽셀만으로는 screen reader가 항목 구조를 알기 어렵습니다.

- canvas에 전체 목적의 접근 가능한 이름
- 별도 DOM 목록으로 항목·선택 상태 제공
- keyboard로 항목 선택·이동·삭제 가능
- 색만으로 역할·충돌·선택 표현하지 않음
- 실시간 저장·충돌 상태를 `role=status`·`alert`로 알림
- reduced motion 선호 시 불필요한 보간 감소

제품 요구에 따라 Canvas와 동등한 편집 경로를 제공해야 할 수 있습니다.

## 이미지와 보안

외부 이미지를 그리면 CORS 설정에 따라 Canvas가 tainted되어 pixel export가 막힐 수 있습니다. 사용자 업로드 이미지는 크기·형식·decode 실패와 메모리 사용을 제한합니다. SVG나 HTML을 그대로 실행 가능한 형태로 삽입하지 않습니다.

## 성능 측정

측정할 항목:

- frame 시간과 dropped frame
- item 수별 render 시간
- pointer event 처리 빈도
- React commit과 Canvas draw 구간
- backing buffer 메모리
- remote cursor·drag event 빈도

`requestAnimationFrame` callback 안에서 layout 측정과 DOM 쓰기를 반복해 layout thrashing을 만들지 않습니다. `getBoundingClientRect()` 결과는 resize·scroll·transform 변화 시 갱신합니다.

## 실패 조건

- Canvas pixel을 application state로 사용합니다.
- CSS 크기와 backing buffer 크기를 같다고 가정합니다.
- resize마다 transform을 누적합니다.
- pointer 좌표를 server가 그대로 저장합니다.
- animation frame과 event listener를 cleanup하지 않습니다.
- 모든 텍스트 입력과 UI를 Canvas에 직접 구현합니다.
- 측정 없이 복잡한 부분 redraw 구조부터 만듭니다.

## 연결 실습

완성 협업 보드의 Canvas는 snapshot·patch로 만든 상태만 그립니다. [`실시간 협업 보드`](../06-capstones/04-collaboration-board.md)의 단계 7에서 좌표 변환, drag preview와 확정 patch를 함께 검증합니다.

## 완료 기준

- board·CSS·device pixel 좌표를 구분하고 변환합니다.
- application state만으로 Canvas를 완전히 다시 그릴 수 있습니다.
- React effect·animation·event 수명을 cleanup합니다.
- hit testing과 server 좌표 검증의 역할을 구분합니다.
- Canvas 밖의 접근 가능한 DOM UI를 설계합니다.

## 다음 단계

각 위험을 가장 짧은 검사에서 증명하고 전체 애플리케이션 품질을 조립하는 방법은 [`테스트와 품질`](04-testing-quality.md)에서 다룹니다.
