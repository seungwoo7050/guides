# 파일시스템, page cache와 장애 일관성

## 학습 목표

- path, directory entry, inode, cached data와 durable data를 분리합니다.
- file `fsync`, directory `fsync`, atomic rename과 journal commit의 보장을 구분합니다.
- 장애 지점별 가능한 상태와 idempotent recovery 불변식을 검증합니다.

## 핵심 모델

파일에 값을 쓴 뒤 같은 process가 그 값을 읽을 수 있다는 사실은 전원 장애 뒤에도 값이 남는다는 뜻이 아닙니다. 파일시스템은 path name, directory entry, inode 같은 metadata, file data, page cache, storage write와 장치 cache를 서로 다른 시점에 바꿀 수 있습니다. 이 장에서는 **현재 실행 중 보이는 상태**와 **장애 뒤 복구되는 durable 상태**를 분리합니다.

## path는 data 자체가 아닙니다

단순화한 Unix 계열 파일시스템에서 path resolution은 다음 객체를 연결합니다.

```text
path component
→ directory entry
→ inode 또는 file object 식별자
→ file metadata
→ data block 또는 page cache 내용
```

파일 이름을 바꾸는 `rename`, inode의 link count를 바꾸는 `link`·`unlink`, file content를 바꾸는 `write`는 서로 다른 상태를 갱신합니다.

다음 불변식이 필요합니다.

```text
유효한 directory entry는 존재하는 file object를 가리킴
file object의 link count는 durable namespace의 참조 수와 일치
free block은 어떤 live file에도 속하지 않음
한 block이 동시에 충돌하는 두 소유자에게 할당되지 않음
file size와 data block 목록이 모순되지 않음
```

실제 파일시스템은 hard link, open-but-unlinked file, snapshot과 delayed allocation 때문에 더 복잡하지만 “이름, object와 data를 분리합니다”라는 모델이 출발점입니다.

## file descriptor와 directory entry의 수명은 다릅니다

process가 file을 열면 kernel은 path lookup 결과인 open file object를 참조합니다. 이후 이름을 삭제해도 열린 descriptor는 같은 object를 계속 사용할 수 있습니다.

```text
open("log")
→ descriptor가 file object 참조

unlink("log")
→ directory entry 제거, link count 감소

process가 descriptor 유지
→ data 접근 가능

마지막 link와 마지막 open reference 제거
→ object와 block을 회수할 수 있음
```

따라서 disk 공간이 줄지 않을 때 “파일 이름이 보이지 않습니다”만으로 object가 해제됐다고 결론 내릴 수 없습니다. 실제 관찰 방법은 Unix 시스템 가이드가 담당합니다.

## page cache는 현재 보이는 write를 흡수할 수 있습니다

일반적인 buffered write는 먼저 memory의 page cache를 바꿉니다.

```text
application write
→ kernel page cache 변경
→ dirty 표시
→ application에 성공 반환 가능
→ 나중에 writeback
→ storage controller·device cache
→ non-volatile media
```

이 경로의 어느 지점까지 도달해야 durability가 성립하는지는 API, mount option, filesystem과 hardware 계약에 따라 다릅니다.

`write` 성공만으로 다음을 모두 보장하지 않습니다.

- file data가 non-volatile media에 도달했습니다.
- file size metadata가 durable합니다.
- 새 file name이 directory에 durable합니다.
- `rename`의 source와 destination directory가 durable합니다.
- storage device가 volatile cache를 실제 media로 flush했습니다.

## file data와 directory durability를 분리합니다

새 파일을 만드는 과정을 단순화합니다.

```text
1. file object 생성
2. directory entry "report" 추가
3. data "v1" write
4. file data flush
5. directory metadata flush
```

4까지만 durable하고 5가 되지 않았다면 장애 뒤 file data object는 storage에 있어도 `report`라는 이름이 남지 않을 수 있습니다. 반대로 directory entry만 먼저 남고 data가 준비되지 않으면 이름은 있지만 내용이 오래되거나 불완전할 수 있습니다.

[`filesystem.py`](../../exercises/kernel-model/README.md)는 live state와 durable state를 별도로 둡니다.

```text
create("draft", "v1")
fsync_file("draft")
crash_recover()
→ directory가 durable하지 않아 이름이 사라짐

create("stable", "v2")
fsync_file("stable")
fsync_directory()
write("stable", "v3")
crash_recover()
→ durable content "v2" 복구
```

이 모델은 특정 filesystem의 정확한 block ordering을 재현하지 않습니다. file content와 namespace durability가 별도라는 계약을 검증합니다.

## 안전한 파일 교체는 여러 durability 경계를 가집니다

설정 파일을 통째로 교체하는 일반적인 패턴은 다음과 같습니다.

```text
1. 같은 filesystem의 임시 file 생성
2. 전체 새 내용 write
3. file flush
4. 임시 file을 목적 path로 atomic rename
5. parent directory flush
```

여기서 “rename이 atomic합니다”는 실행 중 관찰자가 old name 또는 new name 중 하나를 보도록 하는 namespace 원자성을 뜻할 수 있습니다. 장애 뒤 새 이름이 반드시 남는 durability와 같은 주장이 아닙니다.

다음도 확인해야 합니다.

- 임시 file이 다른 filesystem에 있으면 rename이 atomic하지 않을 수 있습니다.
- file permission과 ownership을 언제 설정합니까?
- old file의 metadata를 보존해야 합니까?
- directory flush API와 지원 수준은 무엇입니까?
- write error와 close error를 확인합니까?

shell과 application에서 이 패턴을 구현하는 방법은 해당 개발 가이드가 담당합니다.

## write ordering과 crash window

정상 실행에서는 여러 write가 완료됐지만 storage에는 다른 순서로 도달할 수 있습니다. filesystem은 다음 메커니즘을 조합합니다.

```text
write barrier와 flush
ordered writeback
journal
copy-on-write tree
log-structured update
checksum과 generation
```

핵심은 “어떤 순서가 반드시 durable해야 복구 불변식이 유지되는가”입니다.

예를 들어 block을 새 file에 할당할 때 다음 순서가 잘못되면 같은 block이 free list와 file 양쪽에 보일 수 있습니다.

```text
file metadata는 새 block을 가리킴
free-space metadata는 아직 block이 free라고 기록
장애
→ double allocation 위험
```

반대 순서는 block leak을 만들 수 있습니다. filesystem은 leak과 corruption 중 어떤 실패를 피할지, recovery가 무엇을 고칠 수 있는지 정합니다.

## journal은 transaction의 의도를 기록합니다

단순 write-ahead journal의 흐름은 다음과 같습니다.

```text
BEGIN tx
UPDATE 또는 operation record
COMMIT tx
journal flush
home location 반영
checkpoint 또는 journal 공간 회수
```

장애 뒤에는 commit record가 durable한 transaction만 replay합니다. commit되지 않은 operation은 적용하지 않습니다.

[`journal.py`](../../exercises/kernel-model/README.md)는 다음 불변식을 검사합니다.

```text
BEGIN 없는 operation 금지
BEGIN 없는 COMMIT 금지
COMMIT 뒤 새 operation 금지
같은 committed transaction을 recovery에서 두 번 적용하지 않음
```

```sh
make -C exercises/kernel-model reference-test
make -C exercises/kernel-model failure-test
```

`failure-fixtures/06-journal-commit-before-begin.json`은 transaction 시작 없이 commit된 log를 거부합니다.

## redo와 undo를 구분합니다

### redo logging

새 값을 기록하고 committed transaction의 변경을 다시 적용합니다. operation이 여러 번 적용돼도 같은 결과가 되거나, transaction id로 중복 적용을 막아야 합니다.

### undo logging

이전 값을 기록하고 commit되지 않은 변경을 되돌립니다. data가 journal보다 먼저 durable해질 수 있는지 같은 ordering 계약이 필요합니다.

### physical과 logical logging

physical log는 block·byte 수준 변경을 기록할 수 있고, logical log는 “directory entry 추가” 같은 연산을 기록할 수 있습니다. logical operation은 replay 시 현재 상태와 충돌하지 않도록 idempotency와 precondition이 필요합니다.

실제 filesystem은 두 방식을 혼합할 수 있습니다.

## journaling이 application transaction을 대신하지 않습니다

filesystem journal은 filesystem metadata나 data 구조의 내부 일관성을 보호합니다. 다음 application 불변식을 자동으로 보장하지 않습니다.

```text
두 파일이 같은 generation을 가져야 함
configuration file과 secret file이 함께 바뀌어야 함
DB row와 filesystem object가 한 transaction이어야 함
여러 service가 같은 release manifest를 사용해야 함
```

application은 자체 transaction, version, manifest와 recovery protocol을 설계해야 합니다.

## page cache와 memory mapping

file-backed mapping의 write는 page cache를 dirty하게 만들 수 있습니다. process가 mapping에서 새 값을 읽는다는 사실과 storage durability는 분리됩니다.

```text
mapped write
→ process와 다른 mapping에서 새 값 관찰 가능
→ page dirty
→ writeback 전 장애
→ storage에는 이전 값
```

`msync`, `fsync`, `fdatasync`와 mapping 해제의 정확한 보장은 운영체제 API 문서를 확인해야 합니다. file metadata와 parent directory까지 필요한지 별도로 판단합니다.

## short write와 delayed error

storage가 가득 찼거나 quota, device error가 있으면 write가 일부만 성공할 수 있습니다. buffered write는 초기 호출에 성공하고 나중 writeback 또는 close·fsync에서 오류를 보고할 수도 있습니다.

호출자는 다음을 확인해야 합니다.

```text
반환된 byte 수
반복 가능한 오류인지
부분 파일을 유지할지 제거할지
fsync와 close 오류
원본을 교체하기 전 새 파일 검증
장애 뒤 어떤 generation을 신뢰할지
```

“write가 예외 없이 끝났습니다”라는 high-level 언어 표현이 전체 durability를 의미하는지 runtime과 API 계약을 확인해야 합니다.

## direct I/O와 sync option도 단순한 우회가 아닙니다

page cache를 우회하거나 synchronous write option을 사용해도 alignment, metadata, device cache와 ordering 계약은 남습니다. 성능과 correctness를 함께 측정해야 합니다.

- direct I/O는 buffer alignment와 수명을 요구할 수 있습니다.
- synchronous mode는 각 operation latency를 크게 늘릴 수 있습니다.
- 여러 file 간 ordering은 자동으로 transaction이 되지 않습니다.
- device의 volatile write cache와 power-loss protection을 확인해야 합니다.

## 장애 모델을 먼저 정합니다

crash consistency를 논할 때 어떤 장애를 가정하는지 적습니다.

```text
process crash
- kernel과 page cache는 살아 있음

kernel panic 또는 system reset
- memory state 유실

power loss
- device cache와 controller 상태도 계약에 따라 유실 가능

partial sector 또는 torn write
- hardware와 filesystem이 지원하는 atomicity 단위 확인

media corruption
- checksum, redundancy와 repair 필요
```

process crash 테스트만 통과했다고 power-loss durability를 증명한 것은 아닙니다.

## recovery의 완료 조건

복구가 끝났다는 것은 mount가 성공했다는 사실 이상입니다.

```text
namespace가 참조하는 object가 존재
link count와 directory 참조 일치
allocated block과 free-space metadata 일치
committed transaction 효과가 한 번 반영됨
uncommitted operation이 노출되지 않음
필요한 application generation이 일치
```

`FileSystemModel.validate_snapshot`은 directory, inode, link count와 durable state의 최소 불변식을 검사합니다. `failure-fixtures/05-filesystem-link-count.json`은 directory 참조와 link count가 맞지 않는 snapshot을 거부합니다.

## 연결 실습

[`filesystem.json`](../../exercises/kernel-model/fixtures/filesystem.json)과 `06-storage` checkpoint에서 visible state, durable state와 recovery 결과를 따로 확인합니다.

다음 safe-replace 절차에서 각 단계 직후 장애가 발생했다고 가정하고 old file, temp file와 destination name 중 무엇이 남을 수 있는지 적습니다.

```text
write temp
fsync temp
rename temp → config
fsync parent directory
```

추가로 다음 질문에 답합니다.

1. destination file 내용이 durable하지만 이름이 사라질 수 있는 구간은 어디입니까?
2. rename은 성공했지만 parent directory가 durable하지 않은 상태를 어떻게 검증합니까?
3. journal replay가 같은 logical operation을 두 번 실행해도 안전하려면 무엇이 필요합니까?
4. file data와 DB row를 함께 갱신해야 한다면 filesystem journal만으로 충분합니까?
5. close에서 오류가 났을 때 이미 일부 data를 다른 process가 읽었을 가능성은 있습니까?

## 완료 기준

- safe-replace 네 단계 각각의 crash 뒤 namespace와 data 가능 상태를 표로 만듭니다.
- filesystem fixture가 `v2` 대신 durable `v1`로 복구되는 이유를 설명합니다.
- committed journal만 한 번 replay되고 link count fixture가 거부됨을 확인합니다.

## 실패 조건

- 현재 process가 읽은 값을 durable data로 간주합니다.
- atomic rename 성공을 parent directory durability와 같은 보장으로 취급합니다.
- journal replay를 중복 적용해도 안전한 operation 계약을 확인하지 않습니다.

## 자기 설명

- path, directory entry, file object, data와 page cache를 구분할 수 있습니까?
- 현재 읽을 수 있는 값과 장애 뒤 durable한 값을 별도로 설명할 수 있습니까?
- file `fsync`와 parent directory durability가 다른 이유를 설명할 수 있습니까?
- atomic rename과 crash durability를 같은 주장으로 취급하지 않을 수 있습니까?
- journal에서 committed transaction만 replay하고 중복 적용을 막는 불변식을 적을 수 있습니까?
- process crash, system reset과 power loss의 장애 모델을 구분할 수 있습니까?
