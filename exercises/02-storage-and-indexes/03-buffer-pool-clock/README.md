# Clock buffer pool 구현

제한된 frame 안에서 페이지를 pin하고, dirty page를 안전하게 내보내며, Clock 정책으로 교체 대상을 선택한다.

## 구현할 계약

- 같은 page를 다시 fetch하면 디스크를 다시 읽지 않는다.
- pin된 frame은 교체하지 않는다.
- referenced bit가 켜진 frame에는 두 번째 기회를 준다.
- dirty victim은 mapping을 제거하기 전에 디스크에 기록한다.
- 마지막 unpin 뒤에만 교체 후보가 된다.
- 모든 frame이 pin 상태면 명시적으로 실패한다.

## 실행

```bash
./scripts/new-workspace.sh exercises/02-storage-and-indexes/03-buffer-pool-clock
PYTHONPATH=exercises/02-storage-and-indexes/03-buffer-pool-clock/workspace \
  python3 -m unittest discover -s exercises/02-storage-and-indexes/03-buffer-pool-clock/tests -v
```

문서: [`docs/02-storage-and-indexes/03-buffer-pool-and-replacement.md`](../../../docs/02-storage-and-indexes/03-buffer-pool-and-replacement.md)

## 목표

page table, pin count, dirty bit와 Clock hand를 하나의 frame 수명 계약으로 연결한다.

## 완료 기준

- 같은 page 재조회가 buffer hit로 관찰되고 disk read count를 늘리지 않는다.
- pin된 모든 frame만 남은 경우 victim을 고르지 않고 정해진 오류를 반환한다.
- dirty victim은 disk write를 먼저 완료한 뒤 page table과 frame mapping에서 제거된다.

## 자기 설명

1. referenced bit를 지우는 첫 순회와 실제 축출 순회를 분리해야 하는 이유는 무엇인가?
2. page table entry를 disk write보다 먼저 지우면 실패 시 어떤 상태를 잃는가?

## 검증

workspace 단위 테스트를 반복하고 `make python-check`에서 reference와 의도적으로 불완전한 skeleton을 대조한다.
