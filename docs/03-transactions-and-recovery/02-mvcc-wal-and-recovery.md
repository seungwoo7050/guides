# MVCC, WAL과 crash recovery

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 한다.

- lock만으로 읽기와 쓰기를 모두 직렬화하지 않고도 일관된 snapshot을 제공하는 이유
- tuple version의 생성·가시성·폐기 조건
- MVCC가 write-write conflict나 업무 불변식을 자동으로 해결하지 않는 이유
- WAL의 write-ahead 규칙과 `page_lsn`이 필요한 이유
- commit record와 데이터 page flush가 서로 다른 시점에 일어날 수 있는 이유
- crash 뒤 redo와 undo가 각각 어떤 상태를 복구하는지
- checkpoint가 복구의 시작점을 줄이지만 durability를 대신하지 않는 이유
- vacuum과 오래된 transaction이 저장 공간·가시성에 미치는 영향

## 선행지식

[`Transaction, 격리와 lock`](01-transactions-isolation-and-locks.md)의 transaction 경계, 이상 현상, retry 계약을 먼저 이해해야 한다. 저장 page와 buffer pool의 역할은 [`페이지와 레코드`](../02-storage-and-indexes/01-pages-records-and-files.md), [`Buffer pool`](../02-storage-and-indexes/03-buffer-pool-and-replacement.md)을 참고한다.

## MVCC는 값을 덮어쓰는 대신 version을 관리한다

단순한 in-place update만 있다고 가정하면 reader와 writer가 같은 위치를 두고 계속 충돌한다. reader가 row를 읽는 동안 writer가 그 bytes를 바꾸면 reader는 이전 값과 새 값이 섞인 상태를 볼 수 있다. 모든 read에 긴 shared lock을 잡으면 일관성은 얻을 수 있지만, 읽기가 쓰기를 막고 쓰기가 읽기를 막는 시간이 길어진다.

MVCC는 논리 row의 값을 한 번에 덮어쓰지 않고 여러 version으로 표현한다.

```text
account(id=7, balance=100, xmin=T10, xmax=T12)
account(id=7, balance=80,  xmin=T12, xmax=∞)
```

`T12`가 balance를 100에서 80으로 바꾸면 이전 version을 즉시 없애지 않는다. 이전 version에는 더 이상 최신이 아님을 표시하고, 새 version을 만든다. reader는 자신의 snapshot에서 보이는 version을 선택한다.

이 모델의 핵심 질문은 “가장 최근 bytes가 무엇인가?”가 아니다.

> 이 transaction의 snapshot에서 어느 version이 committed 상태로 보이는가?

## Snapshot은 보이는 transaction 집합을 고정한다

축소한 snapshot을 다음처럼 생각할 수 있다.

```text
snapshot 시작 시점에 완료된 transaction
snapshot 시작 시점에 진행 중인 transaction
snapshot 이후 시작한 transaction
```

어떤 version이 보이려면 보통 다음 조건을 만족해야 한다.

```text
생성 transaction이 이 snapshot에서 committed로 보임
그리고
삭제/대체 transaction이 이 snapshot에서 committed로 보이지 않음
```

실제 PostgreSQL의 transaction ID, subtransaction, hint bit, snapshot 자료구조는 더 복잡하지만, 학습 단계에서는 다음 세 가지를 분리하면 된다.

1. version을 만든 transaction
2. version을 더 이상 최신이 아니게 만든 transaction
3. reader가 사용하는 snapshot

같은 물리 page에 두 version이 있어도 reader마다 다른 결과를 볼 수 있다.

## Isolation level은 snapshot을 언제 새로 잡는지와 연결된다

`READ COMMITTED`에서는 statement마다 새로운 snapshot을 얻을 수 있다. 한 transaction 안에서도 첫 `SELECT`와 두 번째 `SELECT`가 서로 다른 committed version을 볼 수 있다.

`REPEATABLE READ` 계열에서는 transaction snapshot을 유지한다. 같은 row를 반복해 읽을 때 안정적이지만, 서로 다른 row를 고치는 write skew까지 자동으로 막는 것은 아니다.

`SERIALIZABLE`은 snapshot만 제공하는 수준을 넘어, 동시에 실행된 transaction 사이의 위험한 의존 관계를 감지하고 일부를 abort시킨다. MVCC를 쓴다는 사실과 serializable하다는 사실은 동일하지 않다.

## MVCC가 해결하지 않는 문제

### 같은 row에 대한 write-write conflict

두 writer가 같은 row를 바꾸면 하나가 대기하거나 실패해야 한다. 여러 version이 있다고 해서 두 최종 쓰기를 모두 아무 조건 없이 받아들일 수 있는 것은 아니다.

### 여러 row에 걸친 업무 불변식

다음 불변식은 version visibility만으로 보존되지 않는다.

```text
항상 최소 한 명의 당직 의사가 있어야 한다.
```

각 transaction이 서로 다른 row를 수정하면 둘 다 자신의 snapshot에서 다른 당직자를 보고 성공할 수 있다. guard row, serializable isolation, materialized conflict 또는 다른 명시적 직렬화 지점이 필요하다.

### 외부 시스템 효과

DB transaction이 rollback되어도 이미 보낸 email이나 외부 결제 호출은 자동으로 취소되지 않는다. 이는 분산 transaction과 Outbox 같은 별도 범위다.

## 오래된 version은 즉시 지울 수 없다

writer가 새 version을 만들었다고 이전 version을 바로 삭제하면, 오래된 snapshot을 가진 reader가 읽을 값이 사라진다. 따라서 version을 회수하려면 더 이상 어떤 유효 snapshot도 그 version을 필요로 하지 않는다는 증거가 필요하다.

이 때문에 오래 실행되는 transaction은 다음 문제를 만든다.

- dead tuple 회수가 지연된다.
- index entry와 heap page가 팽창한다.
- vacuum이 진행해도 재사용 가능한 범위가 줄어든다.
- transaction ID 정리 범위를 밀어낸다.

“읽기만 하는 transaction이므로 안전하다”는 말은 저장 공간과 유지보수 관점에서는 틀릴 수 있다. transaction 수명을 짧고 명시적으로 유지해야 한다.

## WAL은 데이터 page보다 먼저 기록된다

buffer pool은 수정된 page를 즉시 디스크에 쓰지 않을 수 있다. 반대로 메모리가 부족하면 transaction이 commit하기 전에도 dirty page가 디스크로 밀려날 수 있다. 이 두 상황을 모두 허용하면서 atomicity와 durability를 지키려면 변경의 재현 정보가 먼저 안정 저장소에 있어야 한다.

Write-Ahead Logging의 핵심 규칙은 다음이다.

```text
변경을 포함한 data page를 디스크에 쓰기 전에
그 변경을 설명하는 WAL record가 먼저 안정 저장소에 있어야 한다.
```

그리고 commit 성공을 반환하기 전에 최소한 commit을 증명할 WAL 범위가 안정 저장소에 있어야 한다.

```text
log append
→ WAL flush
→ commit 성공 응답
→ data page flush는 나중일 수 있음
```

따라서 commit 성공 시점에 모든 table page가 디스크 최신 상태일 필요는 없다. crash 뒤 WAL을 replay해 복구할 수 있으면 된다.

## LSN과 `page_lsn`

각 WAL record에는 순서를 나타내는 Log Sequence Number가 있다고 가정한다.

```text
LSN 100: T1, page 3, slot 2를 A에서 B로 변경
LSN 120: T1 COMMIT
```

page에도 마지막으로 반영된 WAL 위치를 기록한다.

```text
page_lsn = 100
```

복구 중 같은 WAL을 다시 만나도 `page_lsn >= record.lsn`이면 이미 반영된 변경으로 판단할 수 있다. 이 규칙은 redo를 반복 실행해도 결과가 달라지지 않는 멱등성의 근거가 된다.

`page_lsn` 없이 “값이 이미 B인지”만 비교하면 같은 최종 값으로 가는 서로 다른 변경을 구분하기 어렵다. 복구는 값의 우연한 동일성보다 변경 순서의 증거를 사용해야 한다.

## WAL record에 필요한 정보

축소 모델에서는 다음 정도를 기록할 수 있다.

```text
LSN
transaction ID
record 종류: UPDATE / COMMIT / ABORT
page ID와 slot ID
before image
after image
이전 transaction record LSN
```

DBMS 설계에 따라 physical log, logical log, physiological log를 선택할 수 있다.

- physical: 특정 bytes의 전·후를 기록한다.
- logical: “이 key를 insert” 같은 논리 연산을 기록한다.
- physiological: page 위치와 page 내부 논리 연산을 결합한다.

학습용 구현에서는 page와 slot을 식별하면서 before/after 값을 기록하면 WAL 순서, redo와 undo를 관찰하기 쉽다.

## Steal과 no-force가 복구 요구를 만든다

Buffer policy를 두 축으로 나눈다.

### Steal

commit하지 않은 transaction의 dirty page를 다른 page를 위해 내보낼 수 있다. 메모리 사용은 유연해지지만 crash 시 uncommitted 변경이 디스크에 남을 수 있으므로 undo가 필요하다.

### No-force

commit할 때 transaction이 바꾼 모든 data page를 즉시 디스크에 쓰지 않는다. commit latency를 줄일 수 있지만 committed 변경이 아직 data file에 없을 수 있으므로 redo가 필요하다.

```text
steal + no-force
→ undo와 redo 모두 필요
```

많은 실제 시스템이 성능을 위해 이 조합 또는 유사한 정책을 사용한다.

## Crash recovery를 세 단계로 생각한다

실제 ARIES는 더 정교하지만, 축소된 학습 모델에서는 다음 순서로 이해할 수 있다.

### 1. 분석

WAL을 읽어 다음을 찾는다.

- 어떤 transaction이 commit했는가
- crash 시점에 어떤 transaction이 끝나지 않았는가
- 어떤 page가 어느 LSN 이후 dirty했는가
- redo를 어디서 시작해야 하는가

### 2. Redo

committed 결과뿐 아니라 “crash 직전 시스템이 수행했던 역사”를 필요한 범위에서 다시 적용한다. page의 `page_lsn`을 보고 이미 반영된 record는 건너뛴다.

축소 exercise에서는 committed transaction만 redo하도록 단순화할 수 있다. 다만 실제 steal/no-force 복구에서는 반복 역사와 undo가 연결된다는 점을 구분한다.

### 3. Undo

crash 시 끝나지 않은 transaction의 변경을 역순으로 되돌린다. transaction별 이전 log record 연결이 있으면 마지막 변경부터 따라갈 수 있다.

undo 자체도 crash할 수 있으므로 실제 시스템은 보상 log record를 남겨 반복 복구가 안전하게 진행되도록 한다. 학습 구현에서는 “복구를 두 번 실행해도 같은 최종 상태”를 최소 계약으로 검사한다.

## Commit과 abort의 경계

다음 경우를 분리한다.

```text
UPDATE WAL은 flush됐지만 COMMIT WAL은 없음
→ transaction 결과를 committed로 인정하지 않음

COMMIT WAL까지 flush됐지만 data page는 이전 값
→ redo로 committed 결과를 복구

uncommitted dirty page가 이미 data file에 기록됨
→ undo로 이전 상태 복구
```

클라이언트가 commit 응답을 받기 직전에 연결이 끊어진 경우에는 애플리케이션 관점에서 결과가 불확실할 수 있다. DB 내부에는 commit record가 있을 수도, 없을 수도 있다. 외부 요청은 operation ID와 상태 조회를 통해 결과를 확인해야 하며, 같은 업무 효과를 무조건 재실행해서는 안 된다.

## Checkpoint는 복구 범위를 줄인다

WAL 전체를 처음부터 재생하면 시간이 계속 늘어난다. checkpoint는 특정 시점의 활성 transaction, dirty page와 log 위치를 기록해 분석 시작점을 줄인다.

checkpoint를 했다고 모든 page가 clean하거나 WAL 이전 부분을 즉시 삭제할 수 있다는 뜻은 아니다. 다음을 함께 확인해야 한다.

- checkpoint가 참조하는 WAL이 안정 저장소에 있는가
- 해당 WAL이 필요한 replica나 backup이 있는가
- dirty page가 어느 LSN까지 반영되었는가
- point-in-time recovery 요구가 있는가

Checkpoint는 복구 최적화다. WAL flush 규칙이나 backup을 대체하지 않는다.

## 복구 검증은 정상 종료만 확인해서는 부족하다

검증 시점을 의도적으로 나눈다.

```text
1. WAL append 전 crash
2. WAL append 후 flush 전 crash
3. update WAL flush 후 commit 전 crash
4. commit WAL flush 후 data page flush 전 crash
5. 일부 data page만 flush된 뒤 crash
6. 복구 중 다시 crash
```

각 시점에서 기대 상태를 먼저 적는다.

- committed transaction의 효과는 남는다.
- uncommitted transaction의 효과는 남지 않는다.
- page와 index가 서로 같은 논리 상태를 가리킨다.
- 복구를 다시 실행해도 결과가 바뀌지 않는다.
- WAL 순서 위반을 검사가 잡는다.

## 관찰 지표

운영 DB에서는 다음 현상이 복구·MVCC 문제의 신호가 될 수 있다.

- 오래 열린 transaction
- dead tuple 증가와 vacuum 지연
- WAL 생성량 급증
- checkpoint가 지나치게 잦거나 오래 걸림
- replication lag
- recovery 예상 시간 증가
- disk full에 가까운 WAL 보관량

수치만 보고 원인을 단정하지 않는다. workload, transaction 수명, page flush, replica와 backup 보존 요구를 함께 본다.

## 연결 연습

[`WAL recovery`](../../exercises/03-transactions-and-recovery/02-wal-recovery/README.md)에서 다음을 구현한다.

- update·commit WAL record
- WAL flush-before-page 검사
- committed transaction redo
- crash 시 미완료 transaction undo
- `page_lsn` 기반 중복 redo 방지
- 복구를 두 번 실행해도 같은 결과가 되는지

이 연습은 실제 PostgreSQL recovery 전체를 재현하지 않는다. WAL 순서와 atomicity·durability 계약을 코드로 관찰하는 축소 모델이다.

## 완료 기준

다음 질문에 코드와 상태 전이로 답할 수 있어야 한다.

- 같은 물리 row에 여러 version이 있을 때 snapshot이 하나를 선택하는 기준은 무엇인가?
- MVCC가 write skew를 자동으로 막지 못하는 이유는 무엇인가?
- commit 성공 전에 data page 전체를 flush하지 않아도 되는 근거는 무엇인가?
- dirty page를 쓰기 전에 어떤 WAL 범위가 반드시 flush되어야 하는가?
- crash 시 committed transaction과 미완료 transaction을 어떻게 구분하는가?
- redo를 두 번 실행해도 안전하게 만드는 증거는 무엇인가?
- 오래 열린 read transaction이 vacuum과 저장 공간에 어떤 영향을 주는가?

다음 문서에서는 저장된 row를 연산자로 처리하는 [`질의 실행, join과 sort`](../04-execution-and-optimization/01-query-execution-joins-and-sorting.md)를 다룬다.
