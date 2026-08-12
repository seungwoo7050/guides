# 서로 다른 변수인데도 같은 캐시 라인이 경쟁하는 경우

두 스레드는 논리적으로 서로 다른 계수기만 수정합니다. `compact`에서는 계수기가 한 캐시 라인에 함께 놓일 수 있고, `padded`에서는 값 사이를 64바이트로 벌립니다.

```sh
make check
make benchmark
```

이 예제는 [멀티코어, 캐시 일관성과 거짓 공유](../../docs/04-parallel-execution/10-multicore-coherence-and-false-sharing.md)의 실제 pthread 관찰 자료입니다. 관찰을 마치면 `processor-model` Stage 10에서 같은 cache-line 경쟁을 안정 MESI state 전이로 설명합니다.

## 권장 구현 순서

다음 번호는 Git history가 아니라 이 독립 예제를 다시 만들 때의 권장 구성 순서입니다. C compiler와 pthread는 선행 환경이고 별도 project bootstrap이 없으므로 0 단계는 없습니다.

| 번호 | 파일·symbol | 먼저 고정하는 책임 |
|---|---|---|
| 1 | `false_sharing.c::compact_counter` | 같은 논리 값의 compact·padded 배치와 64-byte 가정 |
| 2 | `false_sharing.c::start_gate` | mutex·condition이 소유하는 start predicate |
| 3 | `false_sharing.c::run_worker` | thread별 scalar ownership과 동일 increment loop |
| 4 | `false_sharing.c::run_case` | aligned allocation, thread lifecycle와 join 뒤 정확성 gate |
| 4-1 | `false_sharing.c::main` | 같은 조건의 두 case 실행과 timing 관찰 |
| 5 | `Makefile::$(TARGET)` | `-pthread`를 포함한 check·benchmark build interface |

이 예제는 결과의 정확성을 검사하지만 여백을 둔 쪽이 반드시 더 빠르다고 단정하지 않습니다. 다음 조건에서는 차이가 작거나 반대로 보일 수 있습니다.

- 실행 가능한 CPU가 하나뿐입니다.
- 스레드가 같은 코어에 배치됩니다.
- 반복 횟수가 너무 작습니다.
- 측정 중 주파수와 다른 작업량이 변합니다.
- 실제 CPU의 캐시 라인이나 일관성 제어 구현이 가정과 다릅니다.

`compact`의 각 스레드는 같은 C 객체를 동시에 쓰지 않으므로 프로그램 수준의 공유 변수 경쟁과는 다릅니다. 문제는 일관성 제어의 소유권 단위가 스칼라 값이 아니라 캐시 라인이라는 점입니다. [MESI 추적 실습](../../exercises/processor-model/README.md)의 주소 `0`과 `8`도 같은 현상을 상태 전이로 보여 줍니다.

실제 서비스의 구조체에 여백을 무조건 넣지 마세요. 메모리 사용량과 캐시 점유 범위가 늘어나므로 실제 경합과 배치 근거가 있을 때 적용해야 합니다.
