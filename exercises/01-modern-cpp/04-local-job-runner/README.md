# Modern C++ 누적 과제: 로컬 작업 실행기

## 목표

이 과제는 Modern C++ 트랙의 값을 하나의 실행 가능한 프로그램 경계로 통합합니다. 강한 식별자, `variant` 기반 결과, RAII, `jthread`, `stop_token`, bounded queue, 예외 경계, 파일 시스템과 결정적인 동시성 테스트를 함께 사용합니다.

## 시작하기 전에

다음 문서와 앞선 세 실습을 완료합니다.

- [오류·optional·variant·expected](../../../docs/01-modern-cpp/05-errors-optional-variant-and-expected.md)
- [동시성·시간·filesystem](../../../docs/01-modern-cpp/07-concurrency-time-and-filesystem.md)
- [테스트·디버깅·도구](../../../docs/01-modern-cpp/08-testing-debugging-and-tooling.md)

## 상태 계약

```text
submit
  ├─ 거부: empty_name | empty_work | queue_full | stopped
  └─ 수락: queued → running → succeeded | failed | cancelled
```

terminal 상태에서 다른 상태로 되돌아가면 안 됩니다. `cancel`은 queued 상태를 바꾸거나 첫 stop 요청을 발행한 호출에만 true를 반환합니다. 존재하지 않는 ID의 wait는 timeout을 소비하지 않고 즉시 실패합니다. 실행 중 취소는 `stop_token`을 작업에 전달하는 협력적 계약이며, 임의의 thread를 강제로 종료하지 않습니다.

## 단계

1. [값 모델과 Result 접근 계약](specs/01-model-and-result.md)
2. [bounded queue와 상태](specs/02-bounded-queue-and-state.md)
3. [jthread와 취소](specs/03-jthread-and-cancellation.md)
4. [예외·journal·종료](specs/04-errors-journal-and-shutdown.md)

한 단계를 구현할 때마다 자신의 commit을 남긴 뒤 다음 단계로 넘어갑니다. `reference/`는 모든 테스트를 통과한 뒤 설계 차이를 비교하는 용도입니다.

## 검증

```sh
make modern-exercise-test MODERN_EXERCISE=04-local-job-runner
make modern-exercise-sanitize MODERN_EXERCISE=04-local-job-runner
make modern-exercise-thread-sanitize MODERN_EXERCISE=04-local-job-runner
```

reference 공개 API를 실제 실행 파일에서 확인할 수도 있습니다.

```sh
cmake --build exercises/01-modern-cpp/build/debug \
  --target local_job_runner_reference_app
./exercises/01-modern-cpp/build/debug/04-local-job-runner/local_job_runner_reference_app \
  "${TMPDIR:-/tmp}/guide-cpp-jobs-$$.tsv"
```

skeleton을 완성한 뒤에는 `local_job_runner_skeleton_app`도 같은 입력으로 실행되어야 합니다.

테스트는 `sleep`으로 실행 순서를 추측하지 않습니다. `promise`, `future`, stop-aware wait를 사용해 다음 사건을 직접 동기화합니다.

- worker가 실제로 실행을 시작함
- 하나의 작업이 실행 중이고 하나가 queue에 대기함
- 취소 요청이 작업에 전달됨
- terminal 상태가 관찰됨

## 명시적인 한계

생성 시 journal을 만들 수 없으면 runner 생성이 실패합니다. 생성 뒤 append가 실패하면 작업은 계속 실행하되 `journal_healthy()`가 false가 되고, 이 health 저하는 자동 복구하지 않는 sticky 상태입니다. 이 과제의 journal은 상태 전이 감사 기록이며 프로세스 재시작 뒤 실행 중 작업을 자동 복구하는 durable queue는 아닙니다.

외부 `stop()`과 소멸자는 worker join을 기다립니다. Work가 stop token을 관찰하지 않고 영원히 막히면 종료도 기다리게 됩니다. terminal record는 snapshot 조회를 위해 계속 보존하며 자동 정리·보존 기간·`JobId` overflow 정책은 기본 범위에 포함하지 않습니다. 다중 worker, 우선순위, 프로세스 간 잠금, crash-safe fsync는 후속 시스템 설계 주제입니다.

## 완료 기준

- 모든 reference 테스트와 sanitizer를 통과합니다.
- skeleton 구현도 같은 테스트를 통과합니다.
- queue capacity와 실행 중 작업 수의 차이를 설명할 수 있습니다.
- `stop_token` 취소가 협력적이라는 한계를 설명할 수 있습니다.
- 외부 `stop()`은 worker 종료를 기다리며, callback 내부 호출은 self-join을 피하는 이유를 설명할 수 있습니다.
- runtime journal 실패와 작업 상태 전이의 우선순위를 설명할 수 있습니다.
- 상태 전이, 소유권, 잠금 범위와 journal 기록 순서를 그림으로 설명할 수 있습니다.

## 권장 구현 순서

<!-- implementation-scope: modern-local-job-runner -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/include/result.hpp` | 예상 가능한 성공과 실패를 하나의 값 계약으로 두었습니다. |
| `2` | `reference/include/job_runner.hpp` | Job ID·상태·snapshot·callback 모델을 정의합니다. |
| `3` | `reference/include/job_runner.hpp` | queue·record·cancellation·worker join 상태의 owner를 고정합니다. |
| `4` | `reference/src/job_runner.cpp` | 유효한 capacity와 journal을 확인한 뒤 worker를 시작합니다. |
| `5` | `reference/src/job_runner.cpp` | 제출 거부를 값으로 돌리고 삽입 실패를 rollback합니다. |
| `6` | `reference/src/job_runner.cpp` | queued/running 취소와 wait·snapshot 관찰 계약을 연결합니다. |
| `7` | `reference/src/job_runner.cpp` | worker만 실행 상태를 전이시키고 callback 예외를 격리합니다. |
| `8` | `reference/src/job_runner.cpp` | journal 기록 실패를 sticky health 저하로 보존합니다. |
| `9` | `reference/src/job_runner.cpp` | 제출을 닫고 취소를 전파한 뒤 self-join 없이 worker를 합류합니다. |
| `10` | `app/main.cpp` | 공개 API를 process 입력·출력·종료 경계로 조립합니다. |
<!-- /implementation-scope -->
