# 커널 경계와 사건

## 학습 목표

- system call, exception, fault와 interrupt를 발생 주체와 재개 위치로 구분합니다.
- kernel 진입, block, 선점과 context switch를 서로 다른 사건으로 설명합니다.
- 부분 실패 뒤 반환값·오류·소유권·재시도 계약을 기록합니다.

## 핵심 모델

애플리케이션은 CPU 배분, 임의의 물리 메모리와 장치 상태를 직접 바꾸지 못합니다. 운영체제는 사용자 코드와 커널 사이에 권한 경계를 두고, 허용된 진입점으로 요청이 들어왔을 때만 시스템 전체 상태를 변경합니다. 이 장의 목적은 system call, exception, fault와 interrupt를 이름으로 외우는 것이 아니라 **발생 원인, 현재 명령과의 관계, 처리 뒤 재개 위치**로 구분하는 것입니다.

## 사용자 모드와 커널 모드가 나누는 책임

현대 CPU의 특권 단계 수와 이름은 ISA마다 다릅니다. 운영체제 학습에서는 다음 두 영역으로 단순화할 수 있습니다.

```text
사용자 모드
- 애플리케이션의 일반 명령 실행
- 자기 주소 공간의 허용된 mapping 접근
- 특권 명령과 임의 장치 접근 제한

커널 모드
- CPU scheduling과 interrupt 제어
- 주소 공간과 접근 권한 관리
- 장치 request와 completion 관리
- 프로세스·스레드와 파일시스템 상태 변경
```

모드 전환은 일반 함수 호출과 같지 않습니다. CPU는 정해진 진입점으로 이동하고, 이전 권한 수준과 복귀 위치를 보존하며, 커널이 신뢰할 수 있는 stack과 문맥에서 처리하도록 돕습니다. 커널은 사용자 공간이 준 주소, 길이, 식별자와 권한을 다시 검증합니다.

이 경계가 필요한 이유는 단순한 보안만이 아닙니다. 서로 독립적인 프로그램이 같은 장치와 물리 메모리를 사용하므로, 한 요청의 부분 실패가 다른 실행 주체의 상태를 깨지 않도록 소유권과 수명을 중재해야 합니다.

## 사건을 발생 원인으로 구분하기

| 사건 | 누가 발생시킵니까? | 현재 명령과의 관계 | 처리 뒤 가능한 결과 |
|---|---|---|---|
| system call | 사용자 프로그램이 의도적으로 요청합니다. | 동기적입니다. | 같은 스레드로 반환하거나, 대기 뒤 나중에 반환하거나, 실패를 반환합니다. |
| exception | 현재 명령 실행에서 CPU가 감지합니다. | 동기적입니다. | handler가 복구하거나 실행을 종료합니다. |
| fault | 명령을 끝내려면 커널 처리가 필요합니다. | 동기적입니다. | 상태를 준비한 뒤 같은 명령을 다시 시도할 수 있습니다. |
| interrupt | timer나 장치가 외부 사건을 알립니다. | 현재 명령과 비동기적입니다. | 중단된 문맥으로 돌아가거나 scheduler가 다른 작업을 선택합니다. |

교재마다 trap을 동기 exception 전체 또는 의도적인 system call 진입에 사용합니다. 용어가 충돌할 때는 다음 세 질문을 먼저 적습니다.

1. 사건의 원인이 현재 명령입니까, 외부 장치입니까?
2. 처리 뒤 같은 명령을 다시 실행합니까, 다음 명령으로 갑니까?
3. 현재 실행 주체가 계속 실행 가능합니까, 어떤 조건을 기다려야 합니까?

페이지 fault가 항상 프로그램 오류는 아닙니다. demand-zero page의 첫 접근, file mapping의 첫 접근과 COW write는 정상적인 정책 경로일 수 있습니다. 반대로 mapping이 없거나 권한을 위반했다면 커널이 복구할 근거가 없습니다.

## system call의 일반 경로

구체적인 register와 instruction은 ISA와 ABI에 따라 달라지지만 상태 흐름은 비슷합니다.

```text
1. 사용자 코드가 요청 번호와 인자를 준비합니다.
2. 전용 진입 명령으로 커널 경계를 넘습니다.
3. 진입 코드가 복귀에 필요한 사용자 문맥을 보존합니다.
4. 커널이 요청 번호, pointer, length와 권한을 검증합니다.
5. 요청 대상 kernel object를 찾고 참조 수명이나 lock을 확보합니다.
6. 즉시 처리하거나 현재 작업을 BLOCKED 상태로 옮깁니다.
7. 결과, 부분 진행량 또는 오류를 준비합니다.
8. 같은 작업으로 복귀하거나 scheduler를 거쳐 나중에 복귀합니다.
```

사용자 pointer는 커널 내부 pointer가 아닙니다. 주소 범위가 사용자 공간에 속하는지, 필요한 page가 mapping되어 있는지, 읽기·쓰기 권한이 있는지와 길이 계산이 overflow하지 않는지 확인해야 합니다. 검사와 실제 복사 사이에 다른 실행 흐름이 mapping을 바꿀 수 있는지도 운영체제별 계약에 따라 고려해야 합니다.

## 요청과 완료는 다른 사건입니다

`read`를 요청했다고 데이터가 이미 준비된 것은 아닙니다. 하나의 system call은 다음 세 경로 중 하나를 택합니다.

### 즉시 완료

page cache나 kernel buffer에 결과가 있고, 필요한 lock과 자원을 바로 확보할 수 있습니다. 커널은 반환값을 준비해 같은 작업으로 복귀합니다.

### 대기

장치 completion, timer, 다른 작업의 unlock 또는 page-in이 필요합니다. 커널은 현재 작업을 wait queue에 등록하고 `BLOCKED`로 전환합니다. CPU는 다른 `READY` 작업에 배정됩니다. 사건이 발생하면 작업은 다시 `READY`가 되고, 선택된 뒤 요청을 이어서 처리합니다.

### 실패 또는 부분 진행

인자, 권한, 자원 한도와 장치 상태가 계약을 만족하지 않을 수 있습니다. 일부 API는 0 또는 음수로만 실패를 표현하지 않습니다. 부분 `read`·`write`, interrupt로 중단된 대기와 일부 완료처럼 진행량과 재시도 책임을 함께 반환할 수 있습니다.

따라서 system call 비용을 “모드가 두 번 바뀌는 고정 비용”으로 보면 부족합니다. 실제 경로에는 memory copy, lock 경쟁, page fault, scheduler, device latency와 filesystem·network 계층이 포함될 수 있습니다.

## timer interrupt와 선점

사용자 프로그램이 자발적으로 CPU를 돌려주지 않아도 커널이 다시 제어를 얻으려면 timer 사건이 필요합니다. timer handler는 다음 정보를 갱신할 수 있습니다.

- 현재 시간과 만료된 timer
- 실행 중인 작업의 CPU 사용량
- time slice 만료 여부
- 더 높은 우선순위 작업의 실행 필요성
- 주기적 kernel 작업의 예약 상태

모든 timer interrupt가 context switch를 만드는 것은 아닙니다. handler가 끝난 뒤 같은 작업으로 돌아갈 수 있습니다. 반대로 장치 completion이나 unlock이 더 적합한 작업을 `READY`로 만들면 scheduler가 다른 실행 주체를 선택할 수 있습니다.

## interrupt 경로를 짧게 유지하는 이유

interrupt는 현재 실행 흐름을 중단합니다. handler가 오래 걸리면 다른 interrupt 처리, scheduler 지연과 전체 응답 시간이 악화됩니다. 많은 운영체제는 일을 두 경계로 나눕니다.

```text
즉시 해야 하는 일
- 장치 상태와 원인 확인
- completion 정보를 잃지 않게 기록
- 장치에 interrupt 처리 완료를 알림
- 후속 작업 예약

나중에 해도 되는 일
- 큰 packet 처리
- 요청 결과 조립
- 대기 작업 wakeup
- 사용자 공간으로 completion 전달
```

상위·하위 handler, deferred procedure, softirq, work queue 같은 이름은 구현마다 다릅니다. 공통 원리는 **사건을 잃지 않는 최소 기록**과 **시간이 오래 걸리는 후속 처리**를 분리하는 것입니다.

## 실패를 조사할 때 기록할 계약

system call이 실패했을 때 오류 번호만 적고 끝내지 않습니다.

```text
요청 계약: 어떤 인자, 권한과 선행 상태가 필요했습니까?
관측값: 반환값, 진행량, 오류와 log는 무엇입니까?
부분 효과: file offset, buffer, mapping 또는 kernel object가 바뀌었습니까?
소유권: 실패 뒤 누가 memory, FD와 request를 정리합니까?
재시도: 같은 요청을 그대로 반복해도 안전합니까?
복구 조건: 어떤 외부 사건이 발생해야 다시 진행할 수 있습니까?
```

이 질문은 이후 wait queue, page fault, filesystem writeback과 device completion에서도 같은 형태로 반복됩니다.

## 연결 실습

[`syscall-boundary.c`](../../examples/syscall-boundary.c)는 `write` 성공과 존재하지 않는 경로의 `open` 실패를 분리합니다.

```sh
make -C examples build/syscall-boundary
./examples/build/syscall-boundary
```

실행 전에 다음을 예상합니다.

- 첫 출력은 어느 file descriptor로 전달됩니까?
- `open` 실패는 반환값 외에 어떤 상태로 이유를 전달합니까?
- C library buffering과 `write` system call은 같은 계층입니까?
- 이 출력만으로 실제 CPU 진입 instruction과 kernel 내부 handler를 증명할 수 있습니까?

마지막 질문의 답은 아니오입니다. 이 예제는 사용자 공간 계약을 확인합니다. 실제 진입 instruction과 kernel path는 disassembly, tracing 도구와 해당 운영체제의 소스·문서가 추가로 필요합니다.

## 완료 기준

- 네 사건을 동기/비동기와 현재 명령의 관계로 분류한 표를 작성합니다.
- `syscall-boundary`의 성공·실패 출력 field와 증명할 수 없는 내부 상태를 구분합니다.
- block 가능한 요청의 제출·대기·완료·재개의 소유자를 순서대로 표시합니다.

## 실패 조건

- kernel mode 진입을 언제나 context switch라고 부릅니다.
- 오류 번호만 기록하고 부분 효과와 cleanup 책임을 확인하지 않습니다.
- 사용자 공간 출력 하나로 특정 kernel handler 구현을 단정합니다.

## 자기 설명

- timer interrupt가 선점을 가능하게 해도 매번 작업 교체를 강제하지 않는 이유는 무엇입니까?
- system call 요청과 장치 completion이 서로 다른 사건이어야 하는 이유는 무엇입니까?

## 다음 장으로 가져갈 모델

이 장을 마쳤다면 다음을 설명할 수 있어야 합니다.

- system call, fault와 interrupt를 발생 원인으로 구분합니다.
- kernel mode 진입과 context switch가 같은 사건이 아님을 설명합니다.
- 요청이 block될 때 현재 작업이 CPU를 계속 소유하지 않는 이유를 설명합니다.
- 사용자 pointer와 장치 completion을 커널이 검증·기록해야 하는 이유를 설명합니다.
- timer interrupt가 선점을 가능하게 하지만 매번 switch를 강제하지는 않음을 설명합니다.

다음 장에서는 이 사건을 받는 실행 주체가 어떤 상태를 소유하고, switch 때 무엇이 바뀌는지 추적합니다.
