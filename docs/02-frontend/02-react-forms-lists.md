# React 폼과 목록

폼과 목록은 작은 화면에서도 상태·식별자·접근성·server 오류가 동시에 만나는 경계입니다. 입력을 React state로 제어할지 browser에 맡길지, 제출과 검증을 어느 층에서 할지, 항목 identity를 어떻게 보존할지 결정해야 합니다.

## 목표

- 제어 입력과 비제어 입력을 목적에 맞게 선택합니다.
- form submit과 browser 기본 동작을 보존합니다.
- client 검증과 server 검증의 역할을 구분합니다.
- 목록의 key·빈 상태·오류와 optimistic item을 다룹니다.
- focus와 오류 연결을 사용자 계약으로 검증합니다.

## 제어 입력

```tsx
const [title, setTitle] = useState("");

<input
  id="title"
  value={title}
  onChange={(event) => setTitle(event.target.value)}
/>
```

React state가 현재 입력값의 정본입니다. 다른 UI와 즉시 연결하거나 글자 수·조건부 control을 보여 줄 때 유용합니다. 매 keystroke마다 render되므로 거대한 tree가 input state를 소유하지 않게 합니다.

## 비제어 입력

간단한 form은 submit 시 `FormData`로 읽을 수 있습니다.

```tsx
function submit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const title = String(data.get("title") ?? "").trim();
}
```

file input처럼 browser가 값 수명을 소유하는 control에도 적합합니다. 제어·비제어 중 하나가 항상 우월한 것이 아니라 상태가 필요한 시점을 기준으로 선택합니다.

## form submit

```tsx
<form onSubmit={handleSubmit}>
  <label htmlFor="title">보드 제목</label>
  <input id="title" name="title" />
  <button type="submit">만들기</button>
</form>
```

button `onClick`만 사용하지 않습니다. Enter 제출과 browser form 의미를 유지합니다. 제출 중에는 중복 제출을 막되 disabled control이 focus·설명을 잃지 않는지 확인합니다.

## client와 server 검증

client 검증은 빠른 피드백을 제공합니다.

```tsx
const normalized = title.trim();
if (!normalized) setError("제목을 입력해 주세요.");
```

server는 같은 규칙을 다시 검사해야 합니다. 사용자는 client를 우회할 수 있고 client·server version이 다를 수 있습니다. uniqueness, 권한, 현재 version처럼 server 상태가 필요한 규칙은 client만으로 판정할 수 없습니다.

## 오류를 field와 연결합니다

```tsx
<label htmlFor="title">보드 제목</label>
<input
  id="title"
  aria-invalid={Boolean(error)}
  aria-describedby={error ? "title-error" : undefined}
/>
{error ? <p id="title-error">{error}</p> : null}
```

제출 실패 뒤 첫 오류 field로 focus를 옮길 수 있지만, 사용자가 입력하는 매 순간 focus를 강제로 이동시키지 않습니다. server의 안정된 error code를 사용자 문장으로 번역합니다.

## 목록 상태

다음 상태를 분리합니다.

```tsx
if (state.status === "loading") return <p role="status">불러오는 중</p>;
if (state.status === "error") return <p role="alert">{state.message}</p>;
if (state.items.length === 0) return <p>아직 보드가 없습니다.</p>;
```

loading과 empty는 다릅니다. 이전 목록을 유지한 채 background refresh 중이라면 그 계약도 별도로 표현합니다.

## key와 항목 내부 state

stable id를 key로 사용합니다.

```tsx
{boards.map((board) => <BoardCard key={board.id} board={board} />)}
```

배열 index를 사용하면 정렬 뒤 잘못된 card에 menu open state나 input draft가 붙을 수 있습니다. 서버 id가 아직 없는 optimistic item에는 client에서 생성한 안정적인 임시 id를 둡니다.

## optimistic update

사용자 반응을 빠르게 하기 위해 server 응답 전에 목록을 갱신할 수 있습니다.

```text
현재 목록 보존
→ 임시 item 추가
→ 요청
→ 성공 시 server 결과로 교체
→ 실패 시 rollback 또는 failed 상태 표시
```

무조건 이전 배열 전체로 rollback하면 그 사이 성공한 다른 변경을 지울 수 있습니다. operation id나 item 단위 상태를 사용해 해당 변경만 복구합니다. server conflict는 단순 network failure와 다르게 최신 정본을 다시 받아야 할 수 있습니다.

## 삭제와 확인

삭제 button은 항목마다 접근 가능한 이름을 가집니다.

```tsx
<button aria-label={`${board.title} 삭제`}>삭제</button>
```

확인이 필요한 파괴적 작업은 modal의 focus·escape·return focus까지 설계합니다. 모든 삭제에 confirm을 강제하면 사용 흐름을 방해하므로 undo가 가능한 경우 다른 방식도 고려합니다.

## 실패 조건

- form submit 대신 click만 듣습니다.
- client 검증을 server 보안으로 간주합니다.
- 모든 오류를 form 위의 한 문장으로만 보여 줍니다.
- loading과 empty를 같은 UI로 표현합니다.
- index key를 사용합니다.
- optimistic 실패에서 관련 없는 최신 변경까지 rollback합니다.

## 연결 실습

[`React와 Next.js`](../../exercises/03-react-nextjs/README.md)에서 제어 input, 빈 결과, 안정적 key와 browser form 동작을 구현합니다.

## 완료 기준

- 제어·비제어 입력을 선택한 이유를 설명할 수 있습니다.
- Enter로 form을 제출하고 client·server 검증을 구분합니다.
- field 오류와 접근 가능한 설명을 연결합니다.
- loading·empty·ready·error를 구분합니다.
- optimistic 변경의 성공·실패·충돌 후 상태를 정의합니다.

## 다음 단계

network와 browser API 같은 외부 시스템을 component 수명에 연결하는 방법은 [`React effect와 비동기 요청`](03-react-effects-async.md)에서 다룹니다.
