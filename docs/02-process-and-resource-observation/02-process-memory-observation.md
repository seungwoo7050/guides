# 프로세스 메모리 관찰

프로세스의 가상 주소 공간 크기, 실제 RAM에 상주한 페이지, 공유된 페이지와 최근 최대 RSS는 서로 다른 값입니다. 숫자 하나가 크다는 이유만으로 메모리 누수, 과도한 사용 또는 시스템 압박을 판정하면 안 됩니다.

## 학습 목표

- 가상 주소 공간과 물리 메모리 상주량을 구분합니다.
- mapping, page, RSS, shared/private, dirty와 fault를 관찰 수준에서 설명합니다.
- 예약된 큰 주소 공간이 즉시 같은 양의 RAM을 소비하지 않을 수 있음을 설명합니다.
- COW와 file-backed mapping이 관찰값에 미치는 영향을 설명합니다.
- 메모리 누수, cache 성장, working set 증가와 일시적 peak를 구분하는 증거를 수집합니다.
- Linux와 macOS의 관찰 도구 차이를 알고 같은 질문으로 결과를 읽습니다.

## 선행 개념

- process·virtual resource와 단일 수치보다 시간축/독립 근거의 중요성

## 관찰 모델

```text
프로세스 가상 주소 공간
├─ executable와 shared library mapping
├─ anonymous mapping
├─ heap-like allocator 영역
├─ thread stack
├─ file-backed mapping
└─ guard / reserved 영역
        │ page fault와 정책
        ▼
물리 페이지
├─ resident
├─ shared 또는 private
├─ clean 또는 dirty
└─ 회수·swap·compression 가능
```

가상 주소는 프로세스가 사용할 수 있는 주소 범위입니다. 모든 가상 페이지가 물리 RAM에 상주하는 것은 아닙니다.

## 주요 측정값

### Virtual size

프로세스가 가진 mapping과 예약 주소 범위의 총합에 가까운 값입니다. 큰 파일 mapping, 예약된 arena, sparse mapping이나 shared library 때문에 클 수 있습니다.

### RSS

현재 물리 메모리에 상주한 페이지의 근사 합입니다. 공유 페이지가 프로세스별 RSS에 중복 계산될 수 있으므로 여러 프로세스 RSS를 단순 합하면 실제 시스템 사용량보다 커질 수 있습니다.

### Private와 shared

도구에 따라 private dirty, shared clean, proportional set size 같은 분해를 제공합니다. 이름과 계산 방식은 플랫폼마다 다르므로 도구 문서를 확인합니다.

### Peak RSS

프로세스 수명 중 최대 상주량일 수 있습니다. 현재값과 다릅니다.

### Page fault

프로세스가 접근한 가상 페이지를 즉시 사용할 수 없어 커널이 처리한 사건입니다. page fault가 모두 오류나 디스크 I/O를 뜻하지는 않습니다.

```text
minor-like fault
→ 이미 메모리에 있는 페이지 연결, COW 처리 등

major-like fault
→ backing storage I/O가 필요할 수 있음
```

분류와 이름은 운영체제에 따라 다릅니다.

## 예약과 실제 상주

다음 과정은 가능합니다.

```text
128 MiB 주소 공간 예약
→ 첫 페이지 하나만 접근
→ virtual size는 크게 증가
→ RSS는 작은 폭만 증가
```

따라서 “VIRT가 128 MiB 늘었으니 128 MiB 누수”라고 결론 내리면 안 됩니다. 시간에 따른 RSS, private dirty, allocation count, 요청량과 memory pressure를 함께 봅니다.

## File-backed mapping과 공유

실행 파일, shared library와 memory-mapped file은 파일을 backing으로 가질 수 있습니다. clean page는 필요하면 버리고 파일에서 다시 가져올 수 있습니다. 여러 프로세스가 같은 physical page를 공유할 수도 있습니다.

관찰 질문:

- mapping의 backing file이 있습니까?
- writable private mapping입니까, shared mapping입니까?
- dirty page가 계속 증가합니까?
- 파일 크기와 mapping 길이는 얼마입니까?
- 같은 library를 여러 프로세스가 공유합니까?

## Copy-on-write

프로세스 생성이나 private file mapping에서 페이지를 논리적으로 공유하다가 한쪽이 쓸 때 복사할 수 있습니다.

```text
초기: parent와 child가 같은 physical page 참조
write 발생
→ fault
→ 새 private page 생성
→ writer가 새 page 사용
```

따라서 자식 생성 직후와 쓰기 작업 뒤의 RSS·private page 구성이 달라질 수 있습니다. COW의 정책과 page replacement는 `guide-operating-systems`, 주소 변환 하드웨어는 `guide-computer-architecture`가 더 깊게 다룹니다.

## 플랫폼별 관찰

### 공통 시작점

```sh
ps -p PID -o pid=,ppid=,etime=,vsz=,rss=,command=
```

열 이름과 단위는 플랫폼 매뉴얼을 확인합니다.

### Linux

```sh
cat /proc/PID/status
cat /proc/PID/smaps_rollup 2>/dev/null || true
cat /proc/PID/maps
```

`/proc/PID/smaps`는 정보량과 접근 비용이 크므로 증상에 필요한 범위에서 사용합니다. 컨테이너나 권한 정책에 따라 보이지 않을 수 있습니다.

시스템 수준:

```sh
free -h 2>/dev/null || true
vmstat 1 5 2>/dev/null || true
```

### macOS

```sh
vmmap PID
footprint PID
```

명령 지원과 권한은 OS 버전에 따라 다릅니다. Activity Monitor의 한 숫자만 캡처하기보다 mapping과 시간축을 함께 봅니다.

## 메모리 문제 분류

### 누수 가능성

다음 패턴을 찾습니다.

```text
같은 workload 반복
→ 요청 완료 후에도 private resident memory가 계속 증가
→ 안정 구간이 없음
→ object/resource count도 함께 증가
```

한 번의 peak만으로 판정하지 않습니다.

### 의도된 cache 성장

cache hit와 성능을 위해 메모리를 유지할 수 있습니다. 최대 크기, eviction, memory pressure 반응과 재시작 외 회수 경로가 계약되어야 합니다.

### Working set 증가

실제로 더 큰 데이터나 동시 요청을 처리해 필요한 상주량이 늘 수 있습니다. workload와 연결해 봅니다.

### Fragmentation

애플리케이션이 객체를 해제해도 allocator가 페이지를 OS에 즉시 반환하지 않을 수 있습니다. 객체 수명과 프로세스 RSS가 항상 동시에 줄지는 않습니다.

### 파일·FD 문제

삭제됐지만 열린 파일은 디스크 문제이며 RSS와 직접 같은 것은 아닙니다. 반대로 memory-mapped file은 파일과 메모리 관찰이 연결됩니다. 자원 종류를 먼저 분류합니다.

## 측정 절차

```text
1. 정확한 PID와 workload 구간을 고정합니다.
2. 기준 시각과 virtual/RSS 값을 기록합니다.
3. 같은 조건으로 작업을 반복합니다.
4. 현재값·peak·private/shared를 구분합니다.
5. mapping과 backing file을 확인합니다.
6. page fault·swap·memory pressure를 확인합니다.
7. 요청량·cache·object count와 상관관계를 비교합니다.
8. 변경 후 같은 workload와 시간 구간으로 재측정합니다.
```

관찰 자체가 비용을 만들 수 있습니다. 매우 상세한 mapping 수집이나 profiler는 짧은 대표 구간에서 사용합니다.

## 실습 연결

- `09-reserved-not-resident`: 큰 익명 mapping을 예약하고 일부만 접근한 프로세스에서 virtual size와 RSS를 비교합니다.
- `04-deleted-open-file`: disk space 문제와 memory 문제를 구분하는 연습으로 함께 사용합니다.

[시스템 조사 실습](../../exercises/system-investigation/README.md)

## 연결 실습

- [사례 09](../../exercises/system-investigation/README.md)에서 virtual reservation과 RSS를 측정해 누수 오판을 반증합니다.

## 완료 기준

- VIRT와 RSS를 구분할 수 있습니다.
- shared page 때문에 프로세스 RSS 합이 실제 물리 사용량과 다를 수 있음을 설명할 수 있습니다.
- page fault가 항상 치명적 오류를 뜻하지 않는 이유를 설명할 수 있습니다.
- 큰 예약 주소 공간만으로 누수를 판정하면 안 되는 이유를 설명할 수 있습니다.
- 누수, cache, working set과 allocator retention을 구분하기 위한 시간축 실험을 설계할 수 있습니다.

다음 문서: [네트워크 엔드포인트와 연결 진단](03-network-endpoints-and-diagnosis.md)
