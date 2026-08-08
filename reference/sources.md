# 공식 명세와 도구 자료

이 가이드는 고정된 교육용 모델과 실제 하드웨어 문서를 구분합니다. `Tiny-RISC`, 단순 5단계 파이프라인, LRU 캐시, 단순 TLB와 안정 상태 MESI는 학습을 위한 모델입니다. 실제 제품이나 컴파일러의 동작을 판단할 때는 아래 공식 문서와 사용하는 버전의 출시 안내를 우선하세요.

## ISA와 수치 표현

- [RISC-V ISA Specifications](https://docs.riscv.org/reference/isa/)는 비준된 ISA 문서와 확장 명세를 모읍니다.
- [RISC-V Unprivileged ISA](https://docs.riscv.org/reference/isa/unpriv/unpriv-index.html)는 기본 명령, 메모리 모델과 표준 확장이 보장하는 동작을 설명합니다.
- [RISC-V Privileged Architecture](https://docs.riscv.org/reference/isa/priv/)는 권한 수준, 트랩, 페이지 테이블 방식과 제어·상태 레지스터를 다룹니다.
- [IEEE 754-2019 표준 페이지](https://standards.ieee.org/ieee/754/6210/)는 부동소수점 산술 표준의 정본 정보를 제공합니다. 전체 표준 본문에는 별도의 접근 조건이 따를 수 있습니다.

RISC-V 문서는 판본과 비준 상태가 바뀔 수 있습니다. 문서 제목만 인용하지 말고 확인한 판본이나 발행일을 함께 기록하세요.

## x86 마이크로아키텍처와 최적화

- [Intel 64 and IA-32 Architectures Software Developer Manuals](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)는 명령, 시스템 프로그래밍, 메모리 순서와 성능 계수기 사건을 설명합니다.
- [Intel 64 and IA-32 Architectures Optimization Reference Manual](https://www.intel.com/content/www/us/en/content-details/671488/intel-64-and-ia-32-architectures-optimization-reference-manual.html)는 캐시, 분기, SIMD, 데이터 배치와 성능 조정 지침을 설명합니다.

구체적인 지연 시간, 처리량, 캐시 크기와 계수기 사건은 프로세서 세대마다 다를 수 있습니다. 설명서의 일반 원칙보다 측정 대상 모델에 맞춘 자료를 우선하세요.

## 컴파일러 최적화와 벡터화

- [GCC Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)는 `-O` 단계, 벡터화와 부동소수점 관련 선택 사항을 설명합니다.
- [GCC Developer Options](https://gcc.gnu.org/onlinedocs/gcc/Developer-Options.html)는 최적화 중간 결과와 `-fopt-info` 보고서 선택 사항을 설명합니다.
- [GCC tree-SSA vectorization project](https://gcc.gnu.org/projects/tree-ssa/vectorization.html)는 벡터화기가 지원하는 반복문 형태와 구현의 변천을 정리합니다.
- [Clang Users Manual의 optimization reports](https://clang.llvm.org/docs/UsersManual.html#options-to-emit-optimization-reports)는 `-Rpass`, `-Rpass-missed`와 분석 비고를 확인하는 방법을 설명합니다.
- [LLVM Loop Vectorizer](https://llvm.org/docs/Vectorizers.html#the-loop-vectorizer)는 의존성, 실행 중 검사, 축약 연산, 나머지 처리와 비용 모델을 설명합니다.

컴파일러 보고서의 성공 문구만으로 성능 향상을 보장할 수 없습니다. 생성된 어셈블리, 대상 프로세서 기능, 입력과 실행 측정을 함께 확인해야 합니다.

## C와 POSIX 실행 환경

- [POSIX `clock_gettime`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/clock_gettime.html)는 시계 선택과 반환 규칙을 설명합니다.
- [POSIX threads](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/pthread.h.html)는 `pthread` 인터페이스의 표준 선언을 제공합니다.
- [POSIX `posix_memalign`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/posix_memalign.html)는 정렬 조건과 메모리 할당 결과를 설명합니다.

이 저장소의 C 벤치마크는 Linux, macOS와 WSL2에서 공통으로 쓸 수 있는 인터페이스만 사용합니다. 다만 컴파일러, C 라이브러리와 운영체제에 따라 선택 사항이나 타이머 해상도가 달라질 수 있습니다.

## Linux 성능 계수기

- [Linux perf security](https://docs.kernel.org/admin-guide/perf-security.html)는 `perf_event_open` 접근 권한과 보안 설정을 설명합니다.
- [Linux perf ring buffer](https://docs.kernel.org/userspace-api/perf_ring_buffer.html)는 표본 데이터가 커널에서 사용자 공간으로 전달되는 구조를 설명합니다.
- [perf stat manual](https://man7.org/linux/man-pages/man1/perf-stat.1.html)는 계수기 지정, 반복 측정과 출력 선택 사항을 설명합니다.

`cycles`, `instructions`, `cache-misses` 같은 사건 이름이 모든 CPU에서 같은 물리 현상을 뜻한다고 단정하지 마세요. 지원 여부, 사건 대응 관계, 다중화와 커널 접근 권한을 결과와 함께 남겨야 합니다.

## 확인 원칙

외부 자료를 이용해 이 가이드를 수정할 때는 다음을 지켜 주세요.

1. 개인 기술 글보다 ISA·컴파일러·운영체제의 공식 문서를 먼저 확인합니다.
2. 아키텍처가 보장하는 동작과 특정 마이크로아키텍처의 수치를 구분합니다.
3. 문서 판본과 CPU 모델, 컴파일러 버전을 기록합니다.
4. 한 자료의 표를 그대로 옮기지 말고 상태 모델에 필요한 의미만 설명합니다.
5. 공개 명세와 `Tiny-RISC`가 다르면 차이를 문서에 명시합니다.
