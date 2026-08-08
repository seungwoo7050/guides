# 기준 구현 안내

기준 구현은 운영체제의 실제 커널 자료구조를 재현하지 않습니다. 한 CPU, 정수 tick, 페이지당 정수 값 하나, 단일 디렉터리와 단일 장치 큐라는 제한된 모델에서 상태 전이와 불변식을 명확히 보여 줍니다.

## 구현 선택

- 실행 상태는 작업 객체의 `state`와 각 큐의 위치를 함께 검사합니다.
- 조건 대기는 세대 번호를 사용해 조건 검사와 대기 등록 사이의 사건 유실을 드러냅니다.
- 스케줄러는 도착·깨우기·선택·한 tick 실행·완료 순서로 처리합니다.
- COW는 PTE를 쓰기 금지로 바꾸고 frame refcount를 증가시킵니다.
- 파일 내용의 cache 상태와 이름 매핑의 durable 상태를 분리합니다.
- 장치 완료는 인터럽트 단계에서 buffer pin을 풀고, 사용자 소유자가 결과를 회수할 때 요청 수명을 끝냅니다.
- journal 복구는 commit된 operation의 선택과 중복 적용 방지를 모델링하며, replay 도중 임의 operation이 실패했을 때의 transaction rollback은 모델링하지 않습니다.
- CLI 검사는 fixture의 전체 내부 표현이 아니라 각 `expected` mapping이 선언한 관찰 결과를 비교합니다.

8개 checkpoint는 독립 실행할 수 있습니다.

```sh
python3 ../check.py reference 01-lifecycle
python3 ../check.py reference 06-storage
python3 ../check.py reference 08-cli
```

## 의도적으로 보장하지 않는 것

- 실제 CPU의 명령어, TLB, cache coherence를 모델링하지 않습니다.
- 실제 커널 스케줄러의 시간 단위와 다중 CPU 부하 분산을 재현하지 않습니다.
- 파일시스템 block allocator, B-tree와 실제 on-disk format을 구현하지 않습니다.
- 장치 드라이버 register와 IOMMU page table을 구현하지 않습니다.

기준 구현을 평가할 때는 코드 모양보다 `check.py`가 확인하는 외부 상태와 실패 거부 능력을 기준으로 삼습니다.
