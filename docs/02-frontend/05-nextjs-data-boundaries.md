# Next.js 데이터 경계와 adapter

프런트엔드가 모든 component에서 `fetch` URL, header, JSON parsing과 오류 문장을 직접 다루면 API 변경과 테스트 비용이 화면 전체로 퍼집니다. 데이터 경계는 전송 세부 사항을 한곳에 모으고, 화면에는 parse된 값과 안정된 오류만 제공합니다.

## 목표

- transport, adapter, application state와 component를 분리합니다.
- server fetch와 client fetch의 선택 기준을 설명합니다.
- response를 runtime schema로 검증합니다.
- cache, revalidation과 mutation 후 최신성 계약을 명시합니다.
- 테스트용 adapter로 loading·오류·충돌을 결정적으로 재현합니다.

## adapter 계약

```ts
export interface BoardApi {
  listBoards(signal?: AbortSignal): Promise<BoardSummary[]>;
  createBoard(input: CreateBoardInput): Promise<BoardSummary>;
  renameBoard(id: string, input: RenameBoardInput): Promise<BoardSummary>;
}
```

component는 fetch path와 status parsing을 알지 않습니다.

```ts
export function createHttpBoardApi(baseUrl: string): BoardApi {
  return {
    async listBoards(signal) {
      const response = await fetch(`${baseUrl}/boards`, { signal, credentials: "include" });
      return parseResponse(response, BoardListSchema);
    },
    // ...
  };
}
```

adapter는 HTTP 오류와 response validation을 application 오류로 번역합니다.

## server에서 가져올 데이터

초기 page에 필요하고 browser interaction 없이 가져올 수 있는 공개·사용자 data는 Server Component에서 읽을 수 있습니다. 장점은 client bundle 감소와 첫 HTML에 data 포함입니다.

그러나 server component fetch가 browser의 session cookie를 API로 전달하는 경로, deployment network와 cache 정책을 명확히 해야 합니다. 같은 application 내부라면 service를 직접 호출할지 HTTP 경계를 유지할지도 선택입니다. server rendering이 자동으로 모든 보안 문제를 해결하지 않습니다.

## client에서 가져올 데이터

사용자 입력에 따라 자주 바뀌거나 browser API·polling·WebSocket과 결합되는 data는 client 경계가 적합할 수 있습니다. 이 경우 요청 취소, stale response와 화면 상태를 관리합니다.

server와 client에서 같은 data를 각각 가져와 독립 정본을 만들지 않습니다. 초기 server data를 전달하고 이후 client cache가 이어받는 계약을 명시할 수 있습니다.

## response parsing

TypeScript generic만으로 응답이 안전해지지 않습니다.

```ts
async function parseResponse<T>(response: Response, schema: ZodType<T>): Promise<T> {
  if (!response.ok) throw await toApplicationError(response);
  return schema.parse(await response.json());
}
```

204 response처럼 body가 없는 계약은 별도로 처리합니다. proxy가 HTML을 반환하는 경우의 JSON parsing 실패도 안정된 오류로 바꿉니다.

## cache는 최신성 계약입니다

“cache를 쓴다”는 설정이 아니라 다음 질문의 답입니다.

- 어떤 key로 같은 data를 식별하는가?
- 얼마 동안 오래되어도 되는가?
- mutation 성공 뒤 어떤 key를 갱신·무효화하는가?
- 화면에는 이전 data를 유지할 것인가?
- 권한에 따라 다른 응답이 같은 cache에 섞이지 않는가?

사용자별 data를 public shared cache에 넣지 않습니다. cache key가 user·locale·filter 같은 변형 조건을 포함하는지 확인합니다.

## mutation과 conflict

```text
입력 검증
→ optimistic 또는 pending UI
→ mutation 요청
→ 성공 결과를 정본으로 반영
→ 409면 최신 값 재조회와 사용자 선택
→ network 오류면 retry 가능성 판정
```

409 conflict는 단순 실패 message가 아니라 현재 server version과 사용자의 draft를 조정해야 하는 상태입니다. 모든 오류에서 이전 UI로 조용히 rollback하면 사용자가 입력을 잃을 수 있습니다.

## 테스트용 adapter

```ts
export function createDeferredBoardApi() {
  // 검사에서 resolve/reject 시점을 직접 제어
}
```

실제 timer와 network에 의존하지 않고 다음을 재현합니다.

- loading 지속
- 빈 목록
- validation 실패
- 이전 요청이 늦게 완료
- 409 conflict
- mutation 성공 뒤 갱신

화면 테스트가 HTTP server 전체를 항상 필요로 하지 않게 합니다. 반대로 adapter 자체의 실제 HTTP 계약은 별도 통합 검사로 확인합니다.

## server action과 route handler

framework 기능을 사용하더라도 입력 검증·권한·업무 service 경계는 유지합니다. UI component 안에 DB 쓰기와 권한 판정을 섞지 않습니다. 전송 방식이 server action인지 HTTP route인지보다 application command가 어떤 계약을 갖는지가 중요합니다.

## 실패 조건

- 모든 component가 fetch·status·JSON parsing을 반복합니다.
- TypeScript generic으로 외부 응답 검증을 대신합니다.
- server와 client가 같은 data의 독립 정본을 가집니다.
- cache key에서 사용자·filter·version을 빠뜨립니다.
- mutation 성공 뒤 관련 cache가 오래된 채 남습니다.
- 409를 일반 toast로만 처리하고 draft 복구 계약이 없습니다.

## 연결 실습

[`React와 Next.js`](../../exercises/03-react-nextjs/README.md)의 fake adapter로 요청 수명을 검사한 뒤, [`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)의 실제 전송 계약과 연결합니다.

## 완료 기준

- component와 HTTP adapter의 책임을 분리합니다.
- server·client data loading을 선택한 이유를 설명합니다.
- response를 runtime schema로 parse합니다.
- cache key·staleness·mutation 무효화 계약을 정의합니다.
- 테스트 adapter로 순서 역전·오류·conflict를 재현합니다.

## 다음 단계

프런트엔드가 의존할 실제 전송 계약을 설계하려면 [`HTTP API 모델`](../03-backend/01-http-api-model.md)로 이동합니다.
