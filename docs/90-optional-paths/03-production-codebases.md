# 선택 경로: 실제 분산 시스템 코드베이스 진입

## 목적

가이드와 capstone 뒤 실제 coordination·storage system의 작은 변경에 진입합니다. 저장소 전체를 한 번에 이해하지 않고 protocol state, persistence, test harness와 observability 경계부터 조사합니다.

## 조사 순서

```text
문서화된 보장과 failure model
→ message·state type
→ storage interface
→ election·replication handler
→ apply와 client response
→ snapshot·membership
→ deterministic·integration test harness
→ 최근 protocol bug와 regression test
```

## 후보 유형

- Raft library
- coordination service
- distributed key-value store
- database replication module
- cluster metadata service
- model checker·history checker
- deterministic test framework

특정 제품의 인기도보다 다음 조건을 우선합니다.

- protocol 문서와 test가 공개되어 있습니다.
- 작은 module 또는 bug fixture로 기여할 수 있습니다.
- maintainer가 correctness change를 review할 기준을 갖고 있습니다.
- compatibility와 release process가 문서화되어 있습니다.

## 첫 기여 유형

1. invariant가 드러나는 test 이름·오류 메시지 개선
2. 누락된 crash·restart regression fixture
3. trace·metric에 term·index·epoch 추가
4. 작은 persistence ordering bug 재현
5. snapshot·membership edge case 수정
6. model counterexample을 integration test로 이전

## PR에 포함할 근거

- system·failure model
- 최소 재현 schedule
- 첫 위반 invariant
- 변경한 durable·message·state contract
- 기존·신규 test의 보장 범위
- upgrade·snapshot·compatibility 영향
- 성능 또는 storage 비용

protocol change는 정상 경로 예제만으로 승인하지 않습니다.
