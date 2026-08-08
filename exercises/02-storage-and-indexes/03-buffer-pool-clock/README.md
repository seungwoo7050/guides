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
