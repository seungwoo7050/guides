# 파일 검색, symbol과 의존 근거

## 목표

처음 보는 저장소에서 관련 코드를 찾는 과정을 단계화합니다. 검색 결과가 많다는 이유로 모델 context를 채우지 않고, 각 후보가 task와 연결되는 근거를 보존합니다.

## 조사 계층

### 1. 저장소 지도

- 최상위 directory와 주요 manifest
- 언어·build system
- application·library·test·generated·vendor 구분
- monorepo package와 workspace
- 변경 금지 또는 generated path

### 2. lexical search

- issue의 error message
- type·function·config key
- endpoint·command·environment variable
- test name
- log field

filename, exact text, regular expression을 구분합니다.

### 3. symbol search

- definition
- references
- implementations
- call hierarchy
- type hierarchy
- imports·exports

LSP나 parser가 없어도 language-aware index를 선택적으로 사용할 수 있도록 adapter로 분리합니다.

### 4. dependency evidence

- import와 package dependency
- build target
- generated source 관계
- config에서 runtime component로 이어지는 경로
- test fixture와 production code의 연결

### 5. history

- 관련 line의 blame
- 최근 변경
- 이전 bug fix
- revert와 migration

history는 의도를 추측하는 보조 근거입니다. 현재 코드와 test를 대신하지 않습니다.

## SearchResult 계약

```text
query_id
search_kind
canonical_path
line_range_or_symbol
excerpt
content_digest
repository_snapshot_id
match_reason
rank_features
truncated
```

모델이 결과를 인용할 때 path와 line만 아니라 snapshot identity를 유지합니다.

## 검색 전략

```text
넓은 지도
→ task의 직접 식별자 검색
→ definition·reference 추적
→ 관련 test·config·history 확인
→ 가설을 구분할 추가 evidence 선택
```

검색 결과가 없을 때 즉시 새 코드를 만들지 않습니다.

- 다른 이름과 alias를 찾습니다.
- generated file과 source file을 구분합니다.
- case·language·encoding 차이를 확인합니다.
- runtime에서 동적으로 등록되는 경로를 조사합니다.
- task description이 잘못됐을 가능성을 남깁니다.

## 대규모 저장소

다음 budget을 둡니다.

- search result count
- path별 excerpt 수
- 읽기 byte
- index build 시간
- generated/vendor 포함 여부
- binary·large file 처리

검색 index의 revision이 현재 worktree와 다르면 stale 결과로 표시합니다. agent가 수정한 파일은 index 갱신 전 직접 읽기 결과를 우선합니다.

## 관련성 판정

모델의 직관만으로 후보를 고르지 않고 근거를 기록합니다.

```text
직접 identifier match
call/reference 연결
같은 failing test가 실행
같은 config path 사용
최근 관련 change
동일한 invariant 소유
```

관련성을 설명할 수 없는 파일은 context에서 제거할 수 있습니다.

## 실패 조건

- 저장소 전체를 recursive read해 context를 소모합니다.
- `grep` 결과의 path·line·digest를 잃고 excerpt만 보냅니다.
- generated file을 수정할 source처럼 취급합니다.
- search index가 어느 commit에서 생성됐는지 모릅니다.
- history의 commit message를 현재 계약보다 우선합니다.
- 검색 결과가 없다는 사실을 대상 코드가 없다는 증명으로 사용합니다.

## 완료 조건

- 처음 보는 fixture에서 관련 production code, test, config와 build target을 찾는 조사 순서를 설명합니다.
- 각 context item이 task와 연결되는 evidence를 남깁니다.
- lexical search와 symbol/dependency search의 실패를 구분합니다.
- 변경 뒤 영향받은 reference와 test를 다시 탐색합니다.
