# Canvas 렌더링

`<canvas>`는 DOM 요소처럼 항목마다 노드를 유지하지 않습니다. 한 번 그린 픽셀은 애플리케이션 상태가 아니므로 언제든 화면을 다시 그릴 수 있는 별도의 상태가 필요합니다. React와 Canvas를 함께 사용할 때는 React가 상태와 생명주기를 관리하고, Canvas 렌더러는 픽셀 그리기만 담당하도록 책임을 분리합니다.

## 목표

- 보드의 논리 좌표, CSS 픽셀, 장치 픽셀을 구분합니다.
- 애플리케이션 상태만으로 매 프레임 화면을 다시 그립니다.
- React의 생명주기와 명령형 렌더러를 연결합니다.
- 포인터 입력 좌표를 변환하고 서버의 범위 검증과 결합합니다.
- 성능을 측정한 뒤 필요한 최적화만 적용하고 접근 가능한 대체 UI를 제공합니다.

## Canvas는 상태 저장소가 아닙니다

```ts
interface BoardViewState {
  items: BoardItem[];
  cursors: RemoteCursor[];
  selection: string | null;
  viewport: Viewport;
}
```

렌더러는 이 상태를 입력으로 받아 화면을 그립니다.

```ts
function renderBoard(ctx: CanvasRenderingContext2D, state: BoardViewState): void {
  ctx.clearRect(0, 0, state.viewport.width, state.viewport.height);
  for (const item of state.items) drawItem(ctx, item);
  for (const cursor of state.cursors) drawCursor(ctx, cursor);
  if (state.selection) drawSelection(ctx, state.selection, state.items);
}
```

픽셀을 다시 읽어 도메인 상태를 복원하지 않습니다. 재연결 후 스냅샷을 받거나 React 상태가 변경되어도 전체 화면을 다시 그릴 수 있어야 합니다.

## 세 가지 좌표계를 구분합니다

1. **보드 좌표**: 도메인 상태에 저장하는 논리 좌표
2. **CSS 픽셀**: 화면에 표시되는 요소의 크기
3. **장치 픽셀**: Canvas 백킹 버퍼의 실제 해상도

고밀도 디스플레이에서도 선명하게 그리려면 CSS 크기와 백킹 버퍼 크기를 따로 설정합니다.

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

크기를 조정할 때마다 `scale()`을 누적 호출하면 좌표 배율이 계속 커질 수 있습니다. `setTransform()`으로 변환 행렬을 기준 상태로 다시 설정합니다.

## 포인터 좌표 변환

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

CSS 변환, 확대·축소, 스크롤, 보드 이동을 모두 고려해야 합니다. 클라이언트가 계산한 좌표는 신뢰할 수 없는 외부 입력이므로 서버도 유한한 숫자인지, 보드 범위 안인지, 항목별 정책을 만족하는지 다시 검사합니다.

## React와 렌더러 연결

Canvas 요소의 참조와 그리기 Effect를 사용합니다.

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

상태가 커지면 변경할 때마다 모든 항목을 다시 그리는 비용을 측정합니다. 먼저 동작이 명확한 전체 다시 그리기로 구현하고, 실제 프레임 예산을 초과하는 문제가 확인된 뒤 변경 영역만 다시 그리기, 오프스크린 레이어, 공간 인덱스 같은 최적화를 도입합니다.

## 애니메이션 루프

커서 보간이나 드래그 미리보기처럼 프레임마다 화면을 갱신해야 할 때는 `requestAnimationFrame`을 사용합니다.

```ts
let frame = 0;
function tick(time: number) {
  renderInterpolated(time);
  frame = requestAnimationFrame(tick);
}
frame = requestAnimationFrame(tick);
```

컴포넌트를 정리할 때 `cancelAnimationFrame(frame)`을 호출합니다. 여러 Effect가 애니메이션 루프를 중복으로 시작하지 않게 합니다. 백그라운드 탭에서는 애니메이션 실행 빈도가 낮아질 수 있으므로 도메인 타임아웃을 프레임 시간으로 측정해서는 안 됩니다.

## 적중 판정

포인터가 어떤 항목을 가리키는지는 애플리케이션이 관리하는 기하 정보로 판정합니다.

```text
화면 좌표 → 보드 좌표
→ 후보 항목 검색
→ 도형별 적중 판정
→ 가장 위에 있는 항목 선택
```

항목 수가 많아지면 모든 항목을 역순으로 순회하는 방식에서 공간 인덱스를 사용하는 방식으로 발전시킬 수 있습니다. 숨겨진 색상 버퍼의 픽셀을 읽어 항목을 찾는 방법도 있지만 확대·축소, 안티앨리어싱, 유지보수 비용을 함께 고려해야 합니다.

## 텍스트 입력과 편집

Canvas 안에서 텍스트 입력을 직접 구현하면 접근성, 텍스트 선택, IME, 클립보드 동작까지 모두 처리해야 합니다. 실제 메모 편집에는 Canvas 위에 위치를 맞춘 HTML `input`이나 `textarea`를 겹쳐 사용하는 편이 적합할 수 있습니다.

```text
Canvas → 배경·도형·선택 표시
DOM    → 도구 모음·폼·대화 상자·텍스트 편집·상태 알림
```

모든 사용자 인터페이스를 Canvas로 옮기지 않습니다.

## 접근성

Canvas에 그린 픽셀만으로는 스크린 리더가 항목 구조를 파악하기 어렵습니다.

- Canvas 전체 목적을 설명하는 접근 가능한 이름
- 항목과 선택 상태를 제공하는 별도의 DOM 목록
- 키보드로 항목 선택·이동·삭제 가능
- 역할·충돌·선택 상태를 색만으로 표현하지 않음
- 실시간 저장·충돌 상태를 `role="status"` 또는 `role="alert"`로 알림
- 동작 줄이기 설정을 사용하면 불필요한 보간 감소

제품 요구사항에 따라 Canvas와 동등한 편집 경로를 제공해야 할 수 있습니다.

## 이미지와 보안

외부 이미지를 그리면 CORS 설정에 따라 Canvas가 오염된 상태가 되어 픽셀 읽기나 이미지 내보내기가 차단될 수 있습니다. 사용자 업로드 이미지는 크기, 형식, 디코딩 실패, 메모리 사용량을 제한합니다. SVG나 HTML을 실행 가능한 형태로 그대로 삽입해서는 안 됩니다.

## 성능 측정

다음 항목을 측정합니다.

- 프레임 처리 시간과 누락된 프레임 수
- 항목 수에 따른 렌더링 시간
- 포인터 이벤트 처리 빈도
- React 커밋과 Canvas 그리기 구간
- 백킹 버퍼 메모리 사용량
- 원격 커서와 드래그 이벤트 빈도

`requestAnimationFrame` 콜백 안에서 레이아웃 측정과 DOM 쓰기를 반복해 강제 레이아웃 계산을 유발하지 않습니다. `getBoundingClientRect()` 결과는 크기, 스크롤, 변환이 변경될 때 갱신합니다.

## 흔한 오류

- Canvas 픽셀을 애플리케이션 상태로 사용합니다.
- CSS 크기와 백킹 버퍼 크기가 같다고 가정합니다.
- 크기를 조정할 때마다 변환을 누적합니다.
- 클라이언트가 계산한 포인터 좌표를 서버가 그대로 저장합니다.
- 애니메이션 프레임과 이벤트 리스너를 정리하지 않습니다.
- 모든 텍스트 입력과 UI를 Canvas에 직접 구현합니다.
- 측정하기 전에 복잡한 부분 다시 그리기 구조부터 만듭니다.

## 연결 실습

완성된 협업 보드의 Canvas는 스냅샷과 패치로 만든 상태만 그립니다. [`실시간 협업 보드`](../06-capstones/04-collaboration-board.md)의 7단계에서 좌표 변환, 드래그 미리보기, 확정 패치를 함께 검증합니다.

## 완료 기준

- 보드 좌표, CSS 픽셀, 장치 픽셀을 구분하고 상호 변환합니다.
- 애플리케이션 상태만으로 Canvas 전체를 다시 그릴 수 있습니다.
- React Effect, 애니메이션, 이벤트 리스너의 생명주기를 정리합니다.
- 클라이언트의 적중 판정과 서버의 좌표 검증 역할을 구분합니다.
- Canvas 밖에 접근 가능한 DOM 인터페이스를 설계합니다.

## 다음 단계

먼저 [`WebSocket 스냅샷과 패치`](../../exercises/07-websocket/README.md)의 `work/`에서 파트 05의 연결, 스냅샷, 패치, 재연결 동작을 검증하고 완료 후 `reference/`와 비교합니다. 그다음 각 위험을 가장 짧은 경계에서 검증하는 방법을 [`테스트와 품질`](04-testing-quality.md)에서 다룹니다. Canvas 통합은 최종 협업 보드의 7단계에서 수행합니다.
