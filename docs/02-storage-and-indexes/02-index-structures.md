# 인덱스 구조: B+ tree, hash와 BRIN

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 한다.

- 인덱스가 table의 복사본이 아니라 search key에서 row 위치로 가는 별도 구조인 이유
- B+ tree가 equality와 range·order를 함께 지원하는 방법
- leaf와 internal node 분할 규칙이 다른 이유
- composite index에서 column 순서가 탐색 범위를 결정하는 방식
- hash index와 BRIN이 유리한 workload
- index가 읽기를 줄이는 대신 쓰기·공간·유지비를 추가하는 이유

## 선행지식

[`페이지와 레코드`](01-pages-records-and-files.md)에서 page와 RID를 이해해야 한다.

## 인덱스의 기본 계약

인덱스는 search key를 table record 또는 RID와 연결한다.

```text
search key → index entry → (page_id, slot_id) → record
```

index가 있다고 해서 항상 읽기가 빨라지는 것은 아니다. 탐색을 줄이는 대신 다음 비용이 생긴다.

- insert·update·delete 때 index도 변경
- index page의 buffer와 I/O
- split과 vacuum·rebuild 같은 유지 작업
- 잘못된 통계 때문에 비효율적인 index plan 선택
- 많은 heap page를 무작위로 읽는 비용

따라서 index는 “자주 조회하는 column에 추가”하는 장식이 아니라 workload에 대한 물리 설계다.

## B+ tree 구조

B+ tree는 높은 fan-out을 가진 균형 tree다.

```text
internal node: separator keys + child page pointers
leaf node: ordered keys + RID/value
leaf links: 다음 leaf로 이동
```

모든 실제 record pointer는 leaf에 있고, internal node는 탐색 범위를 나눈다. 모든 leaf가 같은 깊이에 있으므로 root-to-leaf 탐색 비용이 안정적이다.

page 하나에 많은 key와 pointer가 들어가므로 binary tree보다 높이가 낮다. 수백만 entry도 몇 번의 page 접근으로 leaf에 도달할 수 있다.

## Internal separator의 의미

예를 들어 internal node가 다음 key를 갖는다고 하자.

```text
[20 | 50]
child 0: key < 20
child 1: 20 <= key < 50
child 2: 50 <= key
```

separator가 “왼쪽의 최대 key”인지 “오른쪽의 최소 key”인지는 구현 계약에 따라 다를 수 있다. 한 방식을 선택하고 search·split·validation 전체에서 일관되게 유지해야 한다.

이 가이드의 B+ tree exercise는 separator를 **오른쪽 subtree의 최소 key**로 정의한다.

## Leaf split

leaf가 page capacity를 넘으면 key/value를 두 leaf로 나눈다.

```text
before: [10, 20, 30, 40]
after : [10, 20] → [30, 40]
parent separator: 30
```

중요한 점:

- 모든 key/value는 두 leaf 중 하나에 남는다.
- 오른쪽 leaf의 첫 key가 parent에 복사된다.
- leaf linked list를 연결한다.
- parent가 넘치면 internal split이 연쇄된다.
- root가 split되면 tree 높이가 하나 늘어난다.

## Internal split

internal node는 key와 child pointer 수가 다르다.

```text
children = keys + 1
```

internal split에서는 가운데 separator를 parent로 **올려 보내고**, 그 key 자체는 두 child node에 남기지 않는 구현이 일반적이다.

```text
before keys: [20, 50, 80]
promote: 50
left keys: [20]
right keys: [80]
```

leaf split과 internal split을 같은 코드로 처리하면 child 범위나 separator가 중복되는 오류가 생기기 쉽다.

## Range scan과 leaf link

B+ tree의 range scan은 시작 key가 있는 leaf까지 root 탐색을 한 뒤 leaf link를 따라간다.

```text
seek(100)
→ leaf에서 100 이상 첫 위치
→ 같은 leaf의 key 읽기
→ next leaf
→ upper bound를 넘으면 종료
```

매 key마다 root에서 다시 찾지 않는다. 이 구조가 `ORDER BY indexed_key`와 범위 조건에 유리하다.

## Duplicate key와 non-unique index

업무 key가 유일하지 않으면 index entry는 같은 search key에 여러 RID를 연결해야 한다.

가능한 표현:

- `(search_key, RID)`를 전체 정렬 key로 사용
- leaf entry 하나에 RID list 저장
- duplicate entry를 연속 배치

실제 DBMS는 concurrency와 page split을 고려한 더 복잡한 방식을 쓴다. 중요한 것은 index key의 유일성과 table row의 유일성을 혼동하지 않는 것이다.

## Composite index

다음 index를 보자.

```sql
CREATE INDEX ON events(tenant_id, created_at DESC, id DESC);
```

정렬 순서는 먼저 `tenant_id`, 그 안에서 `created_at`, 동률이면 `id`다.

잘 맞는 workload:

```sql
WHERE tenant_id = ?
  AND created_at < ?
ORDER BY created_at DESC, id DESC
LIMIT 20
```

`tenant_id` equality로 tree의 좁은 범위를 찾고, 그 범위 안에서 시간 순서로 scan할 수 있다.

반면 다음 질의는 첫 column을 제한하지 않는다.

```sql
WHERE created_at > now() - interval '1 day'
```

모든 tenant 범위를 탐색해야 하므로 같은 index의 효율이 떨어질 수 있다. 이를 흔히 leftmost prefix 규칙으로 설명하지만, 단순 문구보다 실제 정렬 순서를 그리는 편이 정확하다.

## Covering과 INCLUDE

질의가 index key와 추가 payload만으로 결과를 만들 수 있으면 heap 접근을 줄일 수 있다.

```sql
CREATE INDEX ... ON events(tenant_id, created_at DESC, id DESC)
INCLUDE (kind, payload);
```

그러나 index-only scan 가능 여부는 visibility 정보와 DBMS 구현에도 영향을 받는다. INCLUDE column을 많이 넣으면 index 크기와 write 비용이 커진다. “heap을 전혀 읽지 않는다”를 영구 보장으로 간주하지 않는다.

## Partial index

특정 predicate를 만족하는 row만 index에 포함한다.

```sql
CREATE INDEX jobs_pending_schedule_idx
ON jobs(scheduled_at, id)
WHERE status = 'PENDING';
```

완료된 job이 대부분이고 pending만 자주 읽는다면 index를 작게 유지할 수 있다. 질의 predicate가 partial index predicate를 함의해야 planner가 사용할 수 있다.

상태 분포가 변하면 index 가치도 변한다. pending이 대부분이 되면 partial index의 선택성이 사라진다.

## Hash index

hash index는 key hash를 bucket에 매핑한다.

장점:

- equality lookup에 직접적이다.
- key 순서를 유지할 필요가 없다.

제약:

- range와 ordered scan에 적합하지 않다.
- bucket overflow와 skew가 성능을 흔든다.
- hash function과 resize 계약이 필요하다.

다음과 같은 질문에는 잘 맞을 수 있다.

```sql
WHERE session_token = ?
```

하지만 `BETWEEN`, prefix order, `ORDER BY`를 지원하기 위한 구조는 아니다.

## BRIN

BRIN은 table의 연속 page range마다 최소·최대 같은 summary를 저장한다. index entry가 row마다 하나씩 존재하지 않는다.

잘 맞는 조건:

- table이 매우 크다.
- column 값이 물리 page 순서와 강하게 상관된다.
- 시간 append처럼 범위가 자연스럽게 모인다.
- 완벽한 pinpoint보다 많은 page range를 건너뛰는 것이 목적이다.

예를 들어 append-only event table이 시간 순으로 쌓이면 `created_at` BRIN이 작은 공간으로 오래된 page 범위를 제외할 수 있다. row가 무작위 시간 순서로 배치되면 summary 범위가 넓어져 효과가 줄어든다.

## Clustered order와 correlation

B+ tree로 RID를 빠르게 찾더라도 RID가 서로 먼 heap page에 흩어져 있으면 random I/O가 많다. index key와 physical order의 correlation이 높으면 range scan이 연속 page를 읽기 쉽다.

```text
index 탐색 비용
+ 방문할 leaf page
+ heap page 접근 수
```

선택도가 낮아 결과 row가 많을 때 sequential scan이 더 쌀 수 있는 이유다. index 사용 여부는 O(log N)이라는 표기 하나로 결정되지 않는다.

## Index 유지 비용

index 하나를 추가하면 다음 경로가 늘어난다.

```text
INSERT: table page + 각 index
UPDATE: 변경 column과 HOT 가능성
DELETE: table version + index cleanup
VACUUM: dead tuple과 index entry 정리
BACKUP/REPLICA: 더 많은 bytes
```

중복 index, prefix가 겹치는 index와 사용되지 않는 index는 write amplification을 만든다. 제거 전에는 실제 query와 constraint가 해당 index에 의존하는지 확인한다.

## 연결 연습

- [`B+ tree 구현`](../../exercises/02-storage-and-indexes/02-bplus-tree/README.md): leaf/internal split, separator와 range scan을 구현한다.
- [`실행 계획과 인덱스`](../../exercises/04-execution-and-optimization/02-query-plans-and-indexes/README.md): composite·partial index가 실제 PostgreSQL plan에 나타나는지 확인한다.
- [`Index 비용 예제`](../../examples/index_cost_simulator.py): 선택도에 따라 index scan과 sequential scan의 상대 비용이 바뀌는 축소 모델이다.

## 완료 기준

다음을 만족해야 한다.

1. B+ tree leaf와 internal node가 각각 무엇을 저장하는지 그린다.
2. leaf split과 internal split의 separator 처리 차이를 설명한다.
3. composite index column 순서를 대표 질의의 equality·range·order로 정당화한다.
4. equality-only workload와 range workload에서 hash와 B+ tree를 비교한다.
5. BRIN이 작지만 부정확한 summary index인 이유를 설명한다.
6. index 추가 제안에 read 이득뿐 아니라 write·공간·운영 비용을 함께 기록한다.
