# Stage 01 — URL에서 첫 화면 복원

## 사용자 결과

방문자가 `/?q=저장소&status=active&page=1`을 직접 열면 검색 입력, 상태 선택과 첫 목록이 같은 조건을 나타낸다. 잘못된 query는 안전한 기본값으로 정규화된다.

## 구현할 것

- `app/page.tsx`에서 `searchParams`를 기다린다.
- string 값만 `URLSearchParams`로 옮긴다.
- `parseProjectQuery`로 query를 정규화한다.
- 같은 query로 `searchProjects`를 실행한다.
- `ProjectCatalog`에 직렬화 가능한 `initialQuery`, `initialResult`를 전달한다.
- `TODO(stage-01)` 표시를 제거한다.

## 경계값

- 앞뒤 공백이 있는 `q`
- 80자를 넘는 `q`
- 알 수 없는 `status`
- 0, 음수, 실수, 매우 큰 `page`
- 배열로 전달된 query 값

## 완료 조건

```sh
pnpm exercise:verify:01
```

형 검사와 query/첫 화면 행동 검사가 모두 통과해야 한다. 표시만 제거하고 `searchParams`를 무시하면 실패해야 한다.
