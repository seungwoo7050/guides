# Local Job Runner

## 개요

bounded queue와 단일 worker를 사용하는 C++20 local job runner입니다. 제출, 상태 전이, 협력적 취소, terminal wait, snapshot 조회와 TSV journal을 하나의 process-local runtime으로 제공합니다.

## 기능

- 강한 `JobId`와 명시적인 `JobStatus`
- `Result<JobId, SubmitError>` 기반 제출 결과
- 제한된 queue capacity와 rollback 가능한 제출
- `std::jthread`, `std::stop_token` 기반 협력적 취소
- callback 예외의 `failed` 상태 격리
- thread-safe snapshot 및 terminal wait
- 상태 전이 TSV journal과 sticky health 상태
- idempotent하고 concurrent-safe한 `stop()`

## 구조

- `include/result.hpp`: success/failure value contract
- `include/job_runner.hpp`: domain model, ownership, public API
- `src/job_runner.cpp`: queue, worker, cancellation, journal, shutdown
- `app/main.cpp`: 실행 가능한 API composition
- `tests/job_runner_tests.cpp`: 상태, capacity, 취소, 오류, journal 검증

## 빌드, 실행 및 테스트

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
./build/local_job_runner_app /tmp/local-jobs.tsv
```

## 상태 모델

```text
submit
  ├─ rejected: empty_name | empty_work | queue_full | stopped
  └─ accepted: queued → running → succeeded | failed | cancelled
```

terminal 상태는 다시 변경되지 않습니다. queued job은 즉시 취소할 수 있고, running job은 callback이 `stop_token`을 관찰해야 종료됩니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Result value contract | `include/result.hpp` |
| 2 | Job domain model | `include/job_runner.hpp` |
| 3 | Runtime state ownership | `include/job_runner.hpp` |
| 4 | Validated runtime bootstrap | `src/job_runner.cpp` |
| 5 | Transactional submission | `src/job_runner.cpp` |
| 6 | Cancellation and observation | `src/job_runner.cpp` |
| 7 | Worker state machine | `src/job_runner.cpp` |
| 8 | Journal health boundary | `src/job_runner.cpp` |
| 9 | Coordinated shutdown | `src/job_runner.cpp` |
| 10 | Process composition | `app/main.cpp` |

## 범위와 한계

journal은 감사 기록이며 durable queue가 아닙니다. restart recovery, multi-worker scheduling, priority, `JobId` overflow policy, record retention, process 간 locking과 crash-safe `fsync`는 제공하지 않습니다. callback이 stop 요청을 무시하고 영구적으로 block되면 `stop()`도 join을 기다립니다.
