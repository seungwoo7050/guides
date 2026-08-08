# 학습자 구현 골격

이 디렉터리는 문법적으로 유효하지만 핵심 정책과 불변식이 `NotImplementedError`로 비어 있습니다. `scripts/new-workspace.sh`로 복사한 `workspace/`에서만 구현합니다.

## 권장 순서

1. `KernelState.assert_invariants()`를 먼저 구현합니다.
2. `admit`, `dispatch`, `block`, `wake_one`, `preempt`, `exit_running`을 한 전이씩 연결합니다.
3. 조건 채널의 사건 세대를 구현해 깨우기 손실을 막습니다.
4. 스케줄러의 한 tick 처리 순서를 종이에 적은 뒤 구현합니다.
5. deadlock, COW, 저널과 DMA 모델마다 snapshot validator를 먼저 만듭니다.
6. `filesystem.py`와 `journal.py`의 durable/replay 계약을 함께 확인합니다.
7. device request의 queue·pin·completion 위치를 연결합니다.
8. 마지막에 CLI dispatch와 fixture `expected` 결과를 확인합니다.

## 지켜야 할 인터페이스

함수와 클래스 이름, 인자와 반환형은 검사기가 사용합니다. 내부 자료구조는 바꿀 수 있지만 다음 관찰 계약은 유지해야 합니다.

- 같은 작업은 동시에 `ready`, `running`, `wait queue`, `completed` 두 곳에 존재할 수 없습니다.
- 조건 사건이 대기 등록 전에 발생했다면 작업은 그 뒤 잠들면 안 됩니다.
- COW로 공유하는 프레임은 어느 PTE에서도 직접 쓰기 가능이어서는 안 됩니다.
- commit되지 않은 저널 트랜잭션은 복구 때 적용하면 안 됩니다.
- in-flight DMA 요청만 pinned buffer를 소유할 수 있습니다.

`../check.py skeleton`은 skeleton이 정상적으로 import되고 의도한 미구현 지점을 유지하는지만 확인합니다. 구현 중에는 `kernel-model` 디렉터리에서 다음 명령으로 자신의 `workspace/`를 reference와 같은 공개 계약에 대입합니다.

```sh
python3 check.py implementation workspace 01-lifecycle
python3 check.py implementation workspace 02-synchronization
python3 check.py implementation workspace all
```

또는 저장소 루트에서 다음 명령을 사용합니다.

```sh
make -C exercises/kernel-model workspace-test
```

검사 통과만으로 설명이 끝나지는 않습니다. 각 모듈의 상태표, 정책 선택과 failure fixture를 왜 거부하는지 함께 기록합니다.
