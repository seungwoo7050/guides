# 자동 벡터화 보고서 읽기

`saxpy`는 각 원소가 독립적이므로 여러 레인에서 같은 연산을 수행하기 쉽습니다. `recurrence`는 다음 반복이 이전 결과를 사용하므로 같은 방식으로 묶기 어렵습니다.

```sh
make check
make report
make assembly
```

이 예제는 [SIMD와 데이터 배치](../../docs/04-parallel-execution/09-simd-vectorization-and-data-layout.md)의 Stage 09 관찰 checkpoint입니다. checksum, compiler·version·option, 벡터화된 loop, 벡터화되지 않은 loop와 이유를 기록한 뒤 Stage 10으로 진행합니다.

## 권장 구현 순서

다음 번호는 Git history가 아니라 이 독립 예제를 다시 만들 때의 권장 구성 순서입니다. C compiler는 선행 환경이고 별도 project bootstrap이 없으므로 0 단계는 없습니다.

| 번호 | 파일·symbol | 먼저 고정하는 책임 |
|---|---|---|
| 1 | `vector_sum.c::saxpy` | 원소 독립성과 `restrict` non-alias 계약 |
| 2 | `vector_sum.c::recurrence` | loop-carried dependency를 가진 비교 kernel |
| 3 | `vector_sum.c::main` | 결정적 입력, checksum과 finite·reference gate |
| 4 | `report.sh::macros` | GCC·Clang 판별, 보고서 option과 실행 증거 수집 |
| 5 | `Makefile::$(TARGET)` | check·report·assembly public build interface |

`restrict`는 세 포인터가 서로 겹치지 않는다는 계약을 컴파일러에 제공합니다. 실제 호출이 이 계약을 어기면 결과는 정의되지 않으므로 단순한 성능 힌트로 붙여서는 안 됩니다.

보고서에서 “vectorized”라는 문장만 확인하지 마세요. 다음도 함께 봐야 합니다.

- 어느 반복문이 벡터화되었습니까?
- 남은 원소를 위한 반복문이나 마스크 처리가 추가됐습니까?
- 사용한 벡터 폭은 무엇입니까?
- 정렬되지 않은 load를 허용했습니까?
- 부동소수점 연산 순서가 바뀌어도 되는 옵션을 요구합니까?

ISA마다 벡터 명령과 폭이 다르고, 같은 소스도 대상 CPU와 컴파일러 옵션에 따라 스칼라 코드가 될 수 있습니다.
