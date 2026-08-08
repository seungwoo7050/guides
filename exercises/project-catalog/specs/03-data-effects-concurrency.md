# Stage 03 — URL·요청 수명·낙관적 복구

## 사용자 결과

검색 조건은 URL, reload와 back/forward에 보존된다. 연속 검색의 오래된 응답은 최신 결과를 덮지 않는다. 제목 저장의 성공·일반 실패·409 conflict에서 server state와 local draft가 올바르게 수렴한다.

## 구현할 것

### URL과 history

- 검색 제출 시 query를 URL에 기록한다.
- `popstate`에서 URL을 다시 parse해 입력과 결과를 복원한다.
- navigation으로 시작한 검색은 history를 다시 쓰지 않는다.

### 요청 수명

- `createRequestCoordinator`를 완성한다.
- 새 검색이 이전 request signal을 abort한다.
- response 적용 전에 최신 generation인지 확인한다.
- unmount에서 현재 request를 취소한다.
- malformed body는 이전 result를 유지한 error state로 바꾼다.

### Optimistic rename

- 요청 전에 이전 server project와 local draft를 보존한다.
- 예상 title을 목록에 먼저 반영한다.
- 성공 응답을 검증해 server 값으로 확정한다.
- 일반 실패는 이전 server project로 rollback하고 draft를 유지한다.
- 409는 응답의 최신 server project를 반영하고 draft를 유지한다.
- 저장 중 중복 제출을 막는다.

`TODO(stage-03)` 표시를 모두 제거한다.

## 완료 조건

```sh
pnpm exercise:verify:03
```

unit test와 production build 뒤 `@stage-03` browser test가 통과해야 한다. browser test는 응답을 명시적으로 보류·해제하며 고정 sleep에 의존하지 않는다.
