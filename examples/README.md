# 운영체제 경계 관찰 예제

이 디렉터리의 C 프로그램은 운영체제 원리를 사용자 공간에서 관찰 가능한 작은 실행으로 분리합니다. 특정 kernel의 내부 자료구조를 재현하거나 증명하지 않으며, API 반환값·thread 결과·주소 공간 의미와 fault 통계가 본문의 상태 모델과 양립하는지 확인합니다.

## 학습 목표

- system call 성공·실패를 반환값과 `errno`로 함께 판정합니다.
- 경쟁, 조건 대기, lock order와 COW를 관찰 가능한 출력 field에 연결합니다.
- 고정 계약과 환경에 따라 달라지는 측정값을 구분합니다.
- 실행 결과가 증명하지 못하는 kernel 내부 상태를 명시합니다.

## 준비 환경

- C11 compiler가 필요합니다.
- POSIX thread, `fork`, `waitpid`와 `getrusage`를 제공하는 Unix 계열 환경이 필요합니다.
- Linux와 macOS를 지원합니다. Windows에서는 WSL 같은 POSIX 환경이 필요합니다.
- 주소 값, exact fault 수와 오류 문구는 환경에 따라 달라질 수 있습니다.

저장소 루트에서 모든 프로그램을 엄격한 warning 설정으로 빌드합니다.

```sh
make -C examples check
```

정상 경로와 의도한 차이를 실행합니다.

```sh
make -C examples verify
```

정의되지 않은 동작과 주소 오류도 함께 검사합니다.

```sh
make -C examples sanitizer-check
```

생성한 실행 파일만 지웁니다.

```sh
make -C examples clean
```

## 실행 전에 작성할 관찰 계약

각 프로그램을 실행하기 전에 다음을 한 줄씩 적습니다.

```text
예상되는 성공 조건:
의도한 실패 또는 상태 차이:
관찰할 출력 field:
이 결과만으로 증명할 수 없는 kernel 내부 상태:
환경에 따라 달라질 수 있는 값:
```

### `syscall-boundary`

```sh
./examples/build/syscall-boundary
```

`write` 성공과 존재하지 않는 path의 `open` 실패를 분리합니다. 반환값과 `errno`가 함께 실패 계약을 구성하는지 확인합니다. 실제 system-call instruction과 kernel entry code는 이 프로그램만으로 알 수 없습니다.

### `lost-update`

```sh
./examples/build/lost-update split 100
./examples/build/lost-update fetch-add 100
```

두 작업이 같은 값을 읽은 뒤 각각 저장하도록 barrier로 실행 교차를 고정합니다. `split`은 atomic load와 store가 각각 안전해도 복합 증가 하나가 사라지는 경우를 보이고, `fetch-add`는 읽기-수정-쓰기를 한 연산으로 묶습니다.

### `bounded-buffer`

```sh
./examples/build/bounded-buffer 100
```

고정 크기 ring buffer에서 `head`, `tail`, `count`, 종료 flag와 통계를 하나의 mutex로 보호합니다. producer와 consumer는 `not_empty`, `not_full`에서 깨어난 뒤 predicate를 `while`로 다시 검사합니다.

### `dining-cycle`

```sh
./examples/build/dining-cycle 100
```

모든 작업이 작은 번호의 lock을 먼저 획득해 circular wait를 제거합니다. 전체 완료는 확인하지만 공정한 대기 시간과 starvation 부재까지 증명하지 않습니다.

### `cow-observer`

```sh
./examples/build/cow-observer
```

`fork` 전후 같은 가상 주소와 부모·자식의 분리된 값을 관찰합니다. physical frame 번호와 정확한 COW fault 시점은 직접 증명하지 않습니다.

### `page-fault-observer`

```sh
./examples/build/page-fault-observer 128
```

anonymous allocation의 page마다 첫 byte를 쓰고 minor fault 통계 변화량을 출력합니다. 정확한 숫자는 allocator, huge-page 정책과 주변 실행에 따라 달라지므로 고정 정답으로 사용하지 않습니다.

## 결과가 예상과 다를 때

다음 순서로 확인합니다.

1. 프로그램의 종료 상태와 stderr를 보존합니다.
2. compiler와 C library, 운영체제와 architecture를 기록합니다.
3. 출력 숫자가 고정 계약인지 관찰값인지 구분합니다.
4. API 공식 문서에서 반환값과 오류 조건을 확인합니다.
5. 같은 현상을 결정론적 `kernel-model`로 재현할 수 있는지 검토합니다.

관찰 결과 하나를 특정 kernel 내부 구현의 증거로 과장하지 않습니다.

## 완료 기준

- 여섯 프로그램의 성공 조건과 관찰할 출력 field를 실행 전에 작성했습니다.
- `split`과 `fetch-add` 결과가 다른 이유를 복합 연산의 원자성으로 설명했습니다.
- 조건 대기와 lock order 예제에서 보호하는 predicate 또는 순서 불변식을 찾았습니다.
- COW와 minor fault 출력 중 고정 계약과 환경 의존 값을 분리했습니다.
- 일반 실행과 sanitizer 검사를 모두 통과했습니다.

## 자기 설명

- `open` 실패에서 종료 상태만 확인하면 어떤 정보가 사라집니까?
- atomic load/store 두 개가 왜 atomic increment 하나와 같지 않습니까?
- 전체 작업 완료가 starvation 부재를 증명하지 못하는 이유는 무엇입니까?
- 동일한 가상 주소가 동일한 물리 frame을 뜻하지 않는 이유는 무엇입니까?
- minor fault의 정확한 개수를 고정 정답으로 쓰면 왜 취약합니까?

## 검증

```sh
make -C examples verify
make -C examples sanitizer-check
```

검사기는 단순한 종료 상태뿐 아니라 `errno`, counter, 생산·소비 합계, 완료 수, 부모·자식 값과 page touch 수를 확인합니다.
