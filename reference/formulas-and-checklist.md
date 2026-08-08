# 성능식과 설계 검토 빠른 참조

이 문서는 자주 쓰는 계산식을 한곳에 모았습니다. 식에 숫자를 넣기 전에 각 값의 단위와 측정 범위를 먼저 적으세요. 평균 하나만으로 전체 작업량을 설명하거나 서로 다른 장비의 계수기를 직접 비교하면 잘못된 결론을 낼 수 있습니다.

## CPU 실행 시간

```text
CPU time
= instruction count × CPI × clock cycle time
= instruction count × CPI / clock rate
```

단위 예시는 다음과 같습니다.

```text
instructions × cycles/instruction × seconds/cycle = seconds
```

CPI가 여러 instruction class의 가중 평균이면 다음과 같습니다.

```text
average CPI = Σ(class fraction_i × CPI_i)
```

두 판본을 비교할 때는 어느 항이 바뀌었는지 구분하세요.

- 소스 또는 컴파일러가 명령 수를 바꿨습니까?
- 캐시 실패나 분기 예측 실패가 CPI를 바꿨습니까?
- 파이프라인을 깊게 만들어 클록 주파수가 바뀌었습니까?
- CPU 실행 시간이 아닌 실제 경과 시간에 I/O와 스케줄러 대기가 포함됐습니까?

## 속도 향상률

```text
speedup = old execution time / new execution time
```

`2×` 성능 향상은 새 시간이 절반이라는 뜻입니다. “200% 빨라졌다” 같은 표현은 기준이 불명확하므로 시간과 비율을 함께 적는 편이 낫습니다.

## Amdahl의 법칙

전체 시간 중 개선 가능한 비율을 `f`, 그 부분의 성능 향상률을 `s`라고 하면 다음과 같습니다.

```text
overall speedup = 1 / ((1 - f) + f / s)
```

개선 가능한 부분을 무한히 빠르게 해도 한계는 다음과 같습니다.

```text
limit = 1 / (1 - f)
```

예를 들어 전체의 20%만 개선 가능하면 그 부분을 무한히 빠르게 해도 전체 성능은 1.25배보다 더 빨라지지 않습니다.

```sh
python3 exercises/processor-model/reference/processor-model.py perf amdahl \
  --fraction 0.2 --speedup 10
```

## 파이프라인의 이상적인 사이클 수

단계 수가 `k`, 명령 수가 `n`이고 정지·비우기가 없다면 대략 다음과 같습니다.

```text
cycles = k + n - 1
ideal CPI = (k + n - 1) / n
```

긴 실행에서는 파이프라인을 채우고 비우는 비용이 작아져 CPI가 1에 가까워집니다. 실제 CPI에는 다음 비용이 추가됩니다.

```text
actual cycles
= ideal cycles
+ data-hazard stalls
+ control-hazard penalties
+ structural stalls
+ cache/TLB miss stalls
+ 기타 replay와 serialization
```

깊은 파이프라인은 한 단계의 조합 지연을 줄일 수 있지만 분기 복구 비용, 래치 부가 비용과 복잡성이 늘어날 수 있습니다.

## 캐시 주소 분해

캐시 용량을 `C`, 블록 크기를 `B`, 연관도를 `A`라고 하면 세트 수는 다음과 같습니다.

```text
sets = C / (B × A)
```

`C`, `B`, `A`가 적절한 2의 거듭제곱이고 바이트 주소를 사용한다고 가정하면 다음과 같습니다.

```text
offset bits = log2(B)
index bits  = log2(sets)
tag bits    = address bits - index bits - offset bits
```

주소의 블록 번호와 세트는 다음과 같습니다.

```text
block = address // B
set   = block % sets
tag   = block // sets
```

## 캐시 실패율과 AMAT

```text
miss rate = misses / accesses
hit rate  = hits / accesses
```

단순한 한 단계 캐시의 평균 메모리 접근 시간은 다음과 같습니다.

```text
AMAT = hit time + miss rate × miss penalty
```

실패 비용에 하위 캐시 적중 시간이 포함되면 다단계 식을 재귀적으로 구성할 수 있습니다.

```text
AMAT_L1
= L1 hit time
+ L1 miss rate × (L2 hit time + L2 miss rate × memory penalty)
```

지역 실패율과 전역 실패율을 구분하세요.

```text
L2 local miss rate  = L2 misses / L2 accesses
L2 global miss rate = L2 misses / all memory accesses
```

## 캐시 3C 분류

- 최초 접근 실패는 해당 블록을 처음 읽어서 발생합니다.
- 충돌 실패는 같은 줄 수의 완전 연관 캐시라면 적중했지만 세트 대응 관계 때문에 발생합니다.
- 용량 실패는 완전 연관 캐시에서도 작업 집합이 캐시 줄 수를 넘어 발생합니다.

실제 미리 가져오기, 일관성과 비포함 계층이 있는 CPU에서는 이 단순 분류만으로 모든 캐시 실패를 설명할 수 없습니다.

## 대역폭과 지연 시간

```text
bandwidth = transferred bytes / elapsed time
latency   = operation 하나가 완료될 때까지의 시간
```

연속 처리 작업은 대역폭에, 의존성이 이어지는 작업은 지연 시간에 더 민감할 수 있습니다. 서로 독립적인 요청을 여러 개 유지하면 개별 지연 시간을 없애지 않고도 처리량을 높일 수 있습니다.

## 가상 주소 분해

페이지 크기를 `P`라고 하면 다음과 같습니다.

```text
VPN    = virtual address // P
offset = virtual address % P
physical address = PFN × P + offset
```

`P`가 2의 거듭제곱이면 오프셋 비트 수는 `log2(P)`입니다. 페이지 테이블 항목이 없거나 유효하지 않으면 페이지 폴트가 발생할 수 있고, 대응 관계가 있어도 필요한 권한이 없으면 보호 폴트가 발생합니다.

## TLB를 고려한 평균 접근 시간

단순 모델에서 TLB 조회 시간을 `t`, 메모리 접근 시간을 `m`, TLB 적중률을 `h`라고 가정하면 페이지 테이블 단계와 동시 처리 여부에 따라 식이 달라집니다. 예를 들어 단일 단계 페이지 테이블이고 TLB와 캐시의 관계를 단순화하면 다음과 같은 출발점을 사용할 수 있습니다.

```text
EAT = h × (t + m) + (1 - h) × (t + page-table access + m)
```

실제 프로세서의 페이지 워크 캐시, 다단계 테이블, 캐시 적중과 병렬 조회를 생략한 식입니다. 문제에서 어떤 접근을 포함하는지 확인해야 합니다.

## SIMD 처리량

벡터 폭이 `W`비트이고 원소 폭이 `E`비트라면 한 벡터 레지스터에 들어가는 레인 수는 다음과 같습니다.

```text
lanes = W / E
```

이 값이 곧 성능 향상률은 아닙니다. 다음 제한을 함께 봐야 합니다.

- 적재·저장 대역폭
- 의존성과 축약 연산
- 정렬과 나머지 처리
- 마스크와 gather/scatter 비용
- 클록 제한 또는 명령 처리량
- 컴파일러가 실제 벡터 명령을 생성했는지 여부

## 병렬 속도 향상률과 효율

프로세서 수를 `p`라고 하면 다음과 같습니다.

```text
parallel speedup = T1 / Tp
efficiency       = speedup / p
```

직렬 실행 구간, 부하 불균형, 동기화, 통신, 일관성 유지와 메모리 대역폭이 효율을 낮출 수 있습니다.

## 벤치마크 전에 고정할 조건

```text
질문:
입력과 크기:
정확성 기준과 체크섬:
컴파일러와 버전:
컴파일러 선택 사항과 대상:
장비와 CPU 구성:
실행 횟수와 준비 실행:
측정할 실제 경과 시간과 CPU 시간:
관찰할 계수기:
외부 부하와 주파수 상태:
```

한 번의 최솟값만 보고하지 마세요. 최소한 여러 번의 가공하지 않은 결과와 중앙값 또는 분포를 남기고 이상치 제거 규칙을 사전에 정해야 합니다.

## 어셈블리와 계수기를 함께 볼 때

1. 동일한 소스가 실제로 같은 일을 하는지 체크섬으로 확인합니다.
2. 컴파일러가 반복문을 제거하거나 닫힌 형태의 식으로 바꾸지 않았는지 어셈블리를 봅니다.
3. 명령 수 변화와 사이클 변화 중 어느 쪽이 큰지 확인합니다.
4. 분기·캐시 계수기는 사건 정의와 다중화 여부를 확인합니다.
5. 계수기가 없거나 권한이 거부되면 실행 시간만으로 내부 원인을 확정하지 않습니다.
6. 결과가 가설과 다르면 컴파일러, 메모리 배치와 스케줄링부터 다시 확인합니다.

## 캐시·TLB 문제 검토 질문

- 주소의 바이트 단위와 원소 단위를 구분했습니까?
- 블록 크기와 페이지 크기를 혼동하지 않았습니까?
- 세트 인덱스가 물리 주소인지 가상 주소인지 문제 조건에 적혀 있습니까?
- write-through·write-back과 write-allocate 정책을 확인했습니까?
- 교체 상태가 적중할 때도 갱신됩니까?
- 수정된 교체 대상을 내보낼 때 하위 계층 쓰기가 발생합니까?
- 페이지 테이블 갱신 뒤 오래된 TLB 항목을 무효화했습니까?
- 권한 폴트와 페이지 부재 폴트를 구분했습니까?

## 멀티코어 문제 검토 질문

- 공유 단위가 변수입니까, 캐시 줄입니까, 페이지입니까?
- 정확성을 위한 원자성과 성능을 위한 지역성을 구분했습니까?
- 캐시 일관성과 메모리 일관성을 같은 의미로 사용하지 않았습니까?
- 잠금이 보호하는 불변식과 잠금 획득 순서를 적었습니까?
- 거짓 공유를 주장하기 전에 주소와 캐시 줄 오프셋을 확인했습니까?
- 패딩으로 캐시 줄 경쟁을 줄인 대신 메모리 사용량이 얼마나 늘었습니까?
- NUMA 환경에서 메모리가 어느 노드에 배치됐습니까?
