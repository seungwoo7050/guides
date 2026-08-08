# Stage 02 — 런타임 계약과 화면 상태

## 사용자 결과

서버가 잘못된 JSON을 보내도 화면은 그 값을 신뢰하지 않는다. 진행·빈 결과·실패 상태는 모순 없이 표현되고, 재조회 실패에서는 마지막으로 확인된 결과를 유지한다.

## 구현할 것

### `lib/catalog-contract.ts`

- 외부 값을 `unknown`에서 검사한다.
- project의 id, title, summary, status, version을 검증한다.
- search result의 projects, total, page, pageSize를 검증한다.
- 중복 project id를 거절한다.
- update envelope의 project를 검증한다.
- 계약 위반은 `ContractError`로 바꾼다.

### `lib/catalog-model.ts`

- `ready`, `empty`, `pending`, `error`의 discriminated union을 만든다.
- 첫 result로 state를 만든다.
- pending·success·failure 전이를 구현한다.
- pending·error에서는 이전 result를 선택할 수 있게 한다.
- project 하나를 모든 유효 상태에서 교체한다.

`TODO(stage-02)` 표시를 모두 제거한다.

## 완료 조건

```sh
pnpm exercise:verify:02
```

Stage 01과 Stage 02의 unit test, production route type을 포함한 typecheck가 통과해야 한다.
