# 알고리즘·ranges·concepts 기반 조회 파이프라인

## 목표

컨테이너를 직접 순회하며 조건문을 누적하는 대신 조회 계약을 값으로 만들고, `std::views`, `std::ranges` 알고리즘과 concept으로 처리 경계를 표현합니다. 원본 데이터는 변경하지 않고 결과에는 비소유 참조만 담습니다.

## 시작하기 전에

[알고리즘·ranges·templates·concepts](../../../docs/01-modern-cpp/06-algorithms-ranges-templates-and-concepts.md)를 먼저 읽습니다.

## 구현할 계약

- 상태, 최대 실행 시간, 필수 태그는 서로 독립적으로 조합됩니다.
- 정렬 키는 ID 또는 실행 시간입니다.
- 실행 시간이 같으면 ID로 결과 순서를 결정합니다.
- 결과는 원본 `Job`을 소유하지 않는 `reference_wrapper` 목록입니다.
- 조회 과정에서 원본 벡터의 순서와 값은 바뀌지 않습니다.
- `summarize`는 `JobReference`를 순회하는 range에만 참여합니다.

## 작업 순서

1. 하나의 predicate에서 선택 조건을 조합합니다.
2. `views::filter` 결과를 소유하지 않는 참조 목록으로 materialize합니다.
3. `ranges::sort`에 명시적인 tie-breaker를 둡니다.
4. concept이 잘못된 range의 호출을 컴파일 시점에 막는지 확인합니다.
5. 조회 뒤 원본 순서가 보존되는지 검사합니다.

## 실패 실험

- 실행 시간이 같은 항목의 tie-breaker를 제거합니다.
- `std::sort`로 원본 벡터를 직접 정렬합니다.
- 결과에 `Job`을 복사해 원본 변경이 반영되지 않게 만듭니다.
- concept을 제거하고 임의 문자열 range를 전달합니다.

## 검증

```sh
make modern-exercise-test MODERN_EXERCISE=03-query-pipeline
```

## 완료 기준

- 모든 필터 조합과 오름차순·내림차순이 결정적입니다.
- 원본 데이터는 수정되지 않습니다.
- 비소유 결과의 수명 전제를 설명할 수 있습니다.
- concept이 문법 장식이 아니라 공개 템플릿 계약을 좁힙니다.

## 권장 구현 순서

<!-- implementation-scope: modern-query-pipeline -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/include/query.hpp` | source-owned Job과 조회 조건·비소유 결과를 모델링합니다. |
| `2` | `reference/include/query.hpp` | `summarize`의 range 참여 조건을 concept으로 제한합니다. |
| `3` | `reference/src/query.cpp` | filter view를 원본 수명을 공유하는 참조 목록으로 만듭니다. |
| `4` | `reference/src/query.cpp` | key와 ID tie-breaker로 결과 순서를 결정적으로 만듭니다. |
<!-- /implementation-scope -->
