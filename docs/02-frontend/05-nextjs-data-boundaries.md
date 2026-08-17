# Next.js 데이터 경계와 어댑터

모든 프런트엔드 컴포넌트에서 `fetch` URL, 헤더, JSON 파싱, 오류 문장을 직접 다루면 API 변경의 영향과 테스트 비용이 화면 전체로 퍼집니다. 데이터 경계는 전송 계층의 세부 구현을 한곳에 모으고, 화면에는 검증된 값과 일관된 오류만 제공합니다.

## 목표

- 전송 계층, 어댑터, 애플리케이션 상태, 컴포넌트를 분리합니다.
- 서버 요청과 클라이언트 요청의 선택 기준을 설명합니다.
- 응답을 런타임 스키마로 검증합니다.
- 캐시, 재검증, 변경 후 최신성 유지 방식을 명시합니다.
- 테스트용 어댑터로 대기·오류·충돌 상태를 결정적으로 재현합니다.

## 어댑터 계약

```ts
export interface BoardApi {
  listBoards(signal?: AbortSignal): Promise<BoardSummary[]>;
  createBoard(input: CreateBoardInput): Promise<BoardSummary>;
  renameBoard(id: string, input: RenameBoardInput): Promise<BoardSummary>;
}
```

컴포넌트는 `fetch` 경로와 상태 코드 파싱 방법을 알 필요가 없습니다.

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

어댑터는 HTTP 오류와 응답 검증 실패를 애플리케이션이 이해하는 오류로 변환합니다.

## 서버에서 가져올 데이터

초기 페이지에 필요하고 브라우저 상호작용 없이 가져올 수 있는 공개 데이터나 사용자 데이터는 Server Component에서 읽을 수 있습니다. 클라이언트 번들 크기를 줄이고 첫 HTML에 데이터를 포함할 수 있다는 장점이 있습니다.

다만 Server Component에서 API를 호출할 때는 브라우저의 세션 쿠키를 전달하는 방식, 배포 환경의 네트워크 경로, 캐시 정책을 명확히 해야 합니다. 같은 애플리케이션 내부라면 서비스를 직접 호출할지 HTTP 경계를 유지할지도 결정해야 합니다. 서버 렌더링을 사용한다고 모든 보안 문제가 자동으로 해결되는 것은 아닙니다.

## 클라이언트에서 가져올 데이터

사용자 입력에 따라 자주 달라지거나 브라우저 API·폴링·WebSocket과 결합되는 데이터는 클라이언트 경계에서 가져오는 편이 적합할 수 있습니다. 이 경우 요청 취소, 오래된 응답, 화면 상태를 직접 관리해야 합니다.

서버와 클라이언트가 같은 데이터를 각각 가져와 독립적인 기준값으로 사용해서는 안 됩니다. 서버가 초기 데이터를 전달하고 이후에는 클라이언트 캐시가 이어받도록 계약을 명확하게 정할 수 있습니다.

## 응답 파싱

TypeScript 제네릭만으로 외부 응답이 안전해지지는 않습니다.

```ts
async function parseResponse<T>(response: Response, schema: ZodType<T>): Promise<T> {
  if (!response.ok) throw await toApplicationError(response);
  return schema.parse(await response.json());
}
```

204 응답처럼 본문이 없는 계약은 별도로 처리합니다. 프록시가 HTML을 반환해 JSON 파싱에 실패하는 경우도 일관된 애플리케이션 오류로 변환합니다.

## 캐시는 데이터 최신성 계약입니다

캐시 사용 여부만 정해서는 부족합니다. 다음 질문에 답할 수 있어야 합니다.

- 어떤 키로 같은 데이터를 식별하는가?
- 데이터가 얼마 동안 오래된 상태여도 되는가?
- 변경 요청이 성공하면 어떤 키를 갱신하거나 무효화하는가?
- 새 데이터를 가져오는 동안 이전 데이터를 유지할 것인가?
- 권한별로 다른 응답이 같은 캐시에 섞이지 않는가?

사용자별 데이터를 공개 공유 캐시에 저장해서는 안 됩니다. 캐시 키에 사용자·로케일·필터처럼 응답을 달라지게 하는 조건이 포함되는지 확인합니다.

## 변경 요청과 충돌

```text
입력 검증
→ 낙관적 UI 또는 대기 UI 표시
→ 변경 요청 전송
→ 성공 결과를 기준값으로 반영
→ 409이면 최신 값 재조회 후 사용자 선택 요청
→ 네트워크 오류이면 재시도 가능 여부 판단
```

409 충돌은 단순한 실패 메시지로 끝낼 문제가 아닙니다. 현재 서버 버전과 사용자의 초안을 어떻게 조정할지 정해야 합니다. 모든 오류에서 이전 UI로 조용히 되돌리면 사용자가 입력한 내용을 잃을 수 있습니다.

## 테스트용 어댑터

```ts
export function createDeferredBoardApi() {
  // 검사에서 resolve/reject 시점을 직접 제어
}
```

실제 타이머와 네트워크에 의존하지 않고 다음 상태를 재현합니다.

- 요청이 계속 대기 중인 상태
- 빈 목록
- 검증 실패
- 이전 요청이 더 늦게 완료되는 상황
- 409 충돌
- 변경 성공 후 데이터 갱신

이렇게 하면 화면 테스트를 실행할 때마다 전체 HTTP 서버를 시작할 필요가 없습니다. 반대로 어댑터 자체의 실제 HTTP 계약은 별도의 통합 검사로 확인합니다.

## Server Action과 Route Handler

프레임워크 기능을 사용하더라도 입력 검증·권한 검사·도메인 서비스 경계는 유지합니다. UI 컴포넌트 안에 데이터베이스 쓰기와 권한 판정을 섞어서는 안 됩니다. 전송 방식이 Server Action인지 HTTP Route Handler인지보다 애플리케이션 명령이 어떤 계약을 가지는지가 중요합니다.

## 흔한 오류

- 모든 컴포넌트에서 `fetch`, 상태 코드 처리, JSON 파싱을 반복합니다.
- TypeScript 제네릭으로 외부 응답 검증을 대신합니다.
- 서버와 클라이언트가 같은 데이터의 독립적인 기준값을 가집니다.
- 캐시 키에서 사용자·필터·버전을 빠뜨립니다.
- 변경 요청이 성공한 뒤에도 관련 캐시에 오래된 값이 남습니다.
- 409 충돌을 일반 알림으로만 처리하고 초안 복구 방식을 정하지 않습니다.

## 연결 실습

[`React와 Next.js`](../../exercises/03-react-nextjs/README.md)의 가짜 어댑터로 요청 생명주기를 검사한 뒤, [`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)의 실제 전송 계약과 연결합니다.

## 완료 기준

- 컴포넌트와 HTTP 어댑터의 책임을 분리합니다.
- 서버와 클라이언트 중 어느 쪽에서 데이터를 가져올지 선택한 이유를 설명합니다.
- 응답을 런타임 스키마로 파싱합니다.
- 캐시 키·허용 가능한 오래된 시간·변경 후 무효화 방식을 정의합니다.
- 테스트용 어댑터로 응답 순서 역전·오류·충돌을 재현합니다.

## 다음 단계

먼저 [`React와 Next.js`](../../exercises/03-react-nextjs/README.md)의 `work/`에서 파트 02의 상태·요청 생명주기·동적 경로 계약을 검증하고, 완료한 뒤 `reference/`와 비교합니다. 그다음 실제 전송 계약을 설계하려면 [`HTTP API 모델`](../03-backend/01-http-api-model.md)로 이동합니다.
