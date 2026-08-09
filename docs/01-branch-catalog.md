# 브랜치 카탈로그

> 이 문서는 `catalog/branches.json`에서 생성된다. 직접 수정하지 않는다.

전체 학습 브랜치는 **28개**다. 브랜치 종류는 난이도가 아니라 저장소 안에서의 역할을 나타낸다.

## 한눈에 보기

| 브랜치 | 종류 | 핵심 역할 |
|---|---|---|
| [`git`](https://github.com/seungwoo7050/guides/tree/git) | 공통 기반 | 변경을 검토 가능한 단위로 기록하고, 브랜치·Pull Request·충돌·복구를 안전하게 다룬다. |
| [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) | 공통 기반 | 문제를 계약과 불변식으로 바꾸고 정확성·복잡도·반례를 근거로 알고리즘을 설계한다. |
| [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) | 공통 기반 | 비트 표현부터 ISA·파이프라인·캐시·주소 변환·병렬 실행까지 소프트웨어에 보이는 하드웨어 계약을 다룬다. |
| [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) | 공통 기반 | 프로세스·스케줄링·동시성·가상 메모리·저장장치·I/O의 상태와 불변식을 연결한다. |
| [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems) | 공통 기반 | 파일·권한·프로세스·메모리·네트워크 엔드포인트·서비스 상태를 관찰해 실패 계층을 좁힌다. |
| [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) | 공통 기반 | Ethernet부터 IP·TCP·DNS·TLS·QUIC까지 헤더·상태·경로·손실 복구와 장애 증거를 연결한다. |
| [`c`](https://github.com/seungwoo7050/guides/tree/c) | 언어 진입 | 프로그래밍의 기본 계약부터 메모리·파일·프로세스·동시성까지 C와 POSIX로 구현한다. |
| [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) | 언어 진입 | 값 의미론·RAII·객체 책임·CMake·동시성을 이용해 일반 애플리케이션과 시스템 서버에 진입한다. |
| [`java`](https://github.com/seungwoo7050/guides/tree/java) | 언어 진입 | Java·JVM·Maven·JUnit을 이용해 객체 불변식, 동시성, 빌드와 검증을 갖춘 애플리케이션을 만든다. |
| [`python`](https://github.com/seungwoo7050/guides/tree/python) | 언어 진입 | Python 실행 모델과 파일·프로세스·동시성을 이용해 재현 가능한 자동화 도구를 만든다. |
| [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) | 분야 진입 | HTML·CSS·JavaScript·TypeScript·React·API·PostgreSQL·인증·WebSocket을 연결해 작은 풀스택 앱을 만든다. |
| [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) | 분야 진입 | 단일 Linux 호스트에서 컨테이너·DNS·TLS·배포·관측·백업·사고 대응을 갖춘 공개 서비스를 운영한다. |
| [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) | 분야 진입 | 공격 표면과 신뢰 경계를 조사하고 격리 환경에서 취약점을 재현·패치·회귀 검증·탐지·복구한다. |
| [`mobile-app`](https://github.com/seungwoo7050/guides/tree/mobile-app) | 분야 진입 | React Native·Expo를 중심으로 모바일 수명 주기·오프라인 상태·기기 권한·배포를 Android와 iOS에 연결한다. |
| [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning) | 분야 진입 | 데이터 분리·baseline·학습·평가·오류 분석·신경망·transformer·fine-tuning·모델 전달을 하나의 실험 흐름으로 다룬다. |
| [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems) | 분야 진입 | 기존 모델을 구조화된 출력·검색·도구·상태·메모리·평가·권한과 연결해 장기 실행 소프트웨어 시스템을 만든다. |
| [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development) | 분야 진입 | 게임 루프·시간·입력·장면·엔티티·자산·물리·애니메이션·오디오·네트워크 경계를 연결해 게임 코드베이스에 진입한다. |
| [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs) | 심화·전문화 | 기존 Next.js 코드베이스에 합류해 상태·동시성·접근성·성능·운영 산출물까지 수직 기능을 완성한다. |
| [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot) | 심화·전문화 | Spring Core·MVC·Security·JPA·Redis·Kafka·외부 HTTP·Testcontainers·Actuator를 하나의 서비스 경계로 연결한다. |
| [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) | 심화·전문화 | 관계 의미론·인덱스·저장 엔진·MVCC·WAL·실행 계획·안전한 마이그레이션을 애플리케이션과 DBMS 양쪽에서 다룬다. |
| [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services) | 심화·전문화 | 서비스 사이의 부분 실패·중복·순서 역전·불확실한 결과를 멱등성·Outbox·Saga·재조정으로 수렴시킨다. |
| [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing) | 심화·전문화 | 공유 책임·region·availability zone·control plane을 바탕으로 IaaS·PaaS·SaaS와 VM·container·FaaS의 책임·실패·비용·고객 tenant 경계를 비교하고 검증한다. |
| [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems) | 심화·전문화 | 시간·순서·장애 모델부터 복제·일관성·합의·sharding·재구성까지 분산 저장 시스템의 핵심을 구현·검증한다. |
| [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering) | 심화·전문화 | 여러 원천의 데이터를 schema·batch·stream·CDC·품질·lineage·backfill·replay로 신뢰 가능한 데이터 제품으로 만든다. |
| [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering) | 심화·전문화 | 여러 팀이 서비스를 self-service로 생성·검증·배포·관찰하도록 IaC·오케스트레이션·정책·공통 서비스를 플랫폼으로 제공한다. |
| [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation) | 심화·전문화 | lexer·parser·AST·타입 검사·interpreter·bytecode·IR·정적 분석·언어 서버의 경계를 구현한다. |
| [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems) | 심화·전문화 | MCU·메모리 배치·MMIO·interrupt·DMA·RTOS·driver·watchdog·firmware update를 제한된 자원과 시간 계약으로 다룬다. |
| [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics) | 심화·전문화 | 벡터·행렬·이미지·rasterization·shader·GPU resource·동기화·frame budget을 software renderer와 GPU pipeline으로 연결한다. |

## 공통 기반

### `git` — Git과 변경 협업

변경을 검토 가능한 단위로 기록하고, 브랜치·Pull Request·충돌·복구를 안전하게 다룬다.

- **필수 의존성:** 없음
- **권장 기반:** 없음
- **인접 연결:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`c`](https://github.com/seungwoo7050/guides/tree/c), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp)
- **일반적 후속 심화:** 없음

**소유 범위**

- 작업 트리·인덱스·커밋 상태 모델
- 브랜치와 원격 협업
- merge·rebase·충돌
- revert·reset·reflog 기반 복구

**비소유 범위**

- 언어별 빌드 시스템
- 프로젝트별 CI/CD
- 조직별 저장소 정책의 구체 구현

**종료 능력**

- 목적별 커밋을 구성한다
- 리뷰 가능한 Pull Request를 만든다
- 공유 여부에 맞는 복구 방법을 선택한다

### `algorithms` — 알고리즘 설계와 검증

문제를 계약과 불변식으로 바꾸고 정확성·복잡도·반례를 근거로 알고리즘을 설계한다.

- **필수 의존성:** 없음
- **권장 기반:** [`python`](https://github.com/seungwoo7050/guides/tree/python), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp)
- **인접 연결:** [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **일반적 후속 심화:** [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)

**소유 범위**

- 정확성 증명
- 점근 복잡도
- 자료구조와 설계 기법
- 그래프·문자열·환원
- 기준 구현과 반례 기반 검증

**비소유 범위**

- 특정 언어 문법
- 제품 프레임워크
- 운영 시스템 튜닝

**종료 능력**

- 문제를 입력·출력·불변식으로 정의한다
- 후보 알고리즘의 비용과 정확성을 설명한다
- 단순 기준 구현으로 오답을 검출한다

### `computer-architecture` — 컴퓨터 구조와 성능 모델

비트 표현부터 ISA·파이프라인·캐시·주소 변환·병렬 실행까지 소프트웨어에 보이는 하드웨어 계약을 다룬다.

- **필수 의존성:** 없음
- **권장 기반:** [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`c`](https://github.com/seungwoo7050/guides/tree/c), [`python`](https://github.com/seungwoo7050/guides/tree/python)
- **인접 연결:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation), [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics)
- **일반적 후속 심화:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation), [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics)

**소유 범위**

- 데이터 표현과 ISA
- 데이터패스·파이프라인
- 캐시·TLB·주소 변환
- 분기·SIMD·멀티코어 성능 모델

**비소유 범위**

- 운영체제의 페이지 정책
- 언어별 메모리 모델
- 특정 CPU 제품 튜닝

**종료 능력**

- 실행 비용을 구조적 원인으로 분해한다
- 캐시와 주소 변환 실패를 설명한다
- 성능 주장을 측정 근거와 연결한다

### `operating-systems` — 운영체제 원리

프로세스·스케줄링·동시성·가상 메모리·저장장치·I/O의 상태와 불변식을 연결한다.

- **필수 의존성:** 없음
- **권장 기반:** [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)
- **인접 연결:** [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **일반적 후속 심화:** [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems)

**소유 범위**

- 작업과 스케줄링
- 동기화와 deadlock
- 가상 메모리와 COW
- 파일·페이지 캐시·저널
- 장치·DMA·interrupt

**비소유 범위**

- Linux 내부 구조체 암기
- 사용자 공간 진단 명령 전체
- 특정 DBMS·분산 저장소

**종료 능력**

- 커널 상태 전이를 모델링한다
- 동시성과 메모리 실패를 불변식으로 설명한다
- 복구 가능한 저장·I/O 경계를 설계한다

### `unix-systems` — Unix 시스템 관찰과 진단

파일·권한·프로세스·메모리·네트워크 엔드포인트·서비스 상태를 관찰해 실패 계층을 좁힌다.

- **필수 의존성:** 없음
- **권장 기반:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **인접 연결:** [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)
- **일반적 후속 심화:** [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)

**소유 범위**

- 경로와 파일 디스크립터 관찰
- 프로세스·시그널·작업 제어
- 메모리·네트워크 상태 조사
- 서비스 준비 상태와 진단 절차

**비소유 범위**

- POSIX API 재구현
- 커널 내부구조
- 공개 서비스 배포

**종료 능력**

- 증상에서 첫 실패 계층을 좁힌다
- 명령 출력이 증명하는 상태를 설명한다
- 가역적인 복구 절차를 선택한다

### `computer-networks` — 컴퓨터 네트워크 원리와 검증

Ethernet부터 IP·TCP·DNS·TLS·QUIC까지 헤더·상태·경로·손실 복구와 장애 증거를 연결한다.

- **필수 의존성:** 없음
- **권장 기반:** [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **인접 연결:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **일반적 후속 심화:** [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)

**소유 범위**

- 링크·IP·라우팅·NAT
- UDP·TCP 상태와 손실 복구
- DNS·TLS·QUIC
- 계층별 네트워크 장애 분리

**비소유 범위**

- 웹 애플리케이션 인증
- 실제 공개 DNS·TLS 운영
- 완전한 네트워크 스택 구현

**종료 능력**

- 한 요청의 종단 경로를 추적한다
- TCP·DNS·TLS 실패를 분리한다
- 패킷과 상태 증거로 원인을 좁힌다


## 언어 진입

### `c` — C와 POSIX 프로그래밍

프로그래밍의 기본 계약부터 메모리·파일·프로세스·동시성까지 C와 POSIX로 구현한다.

- **필수 의존성:** 없음
- **권장 기반:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **인접 연결:** [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems)
- **일반적 후속 심화:** [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems)

**소유 범위**

- C 언어와 빌드
- 메모리와 자원 소유권
- POSIX 파일·프로세스·시그널
- 기초 동시성
- sanitizer 기반 검증

**비소유 범위**

- 커널 개발
- 임베디드 하드웨어
- 분산 시스템
- GUI

**종료 능력**

- 여러 파일의 C 프로그램을 설계한다
- 자원 수명과 실패 정리를 구현한다
- POSIX 프로그램을 빌드·검증한다

### `cpp` — C++ 애플리케이션과 시스템 개발

값 의미론·RAII·객체 책임·CMake·동시성을 이용해 일반 애플리케이션과 시스템 서버에 진입한다.

- **필수 의존성:** 없음
- **권장 기반:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **인접 연결:** [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **일반적 후속 심화:** [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)

**소유 범위**

- C++ 객체·수명·복사·이동
- RAII와 일반 애플리케이션 구조
- CMake와 테스트
- C++98 시스템 서버 경계

**비소유 범위**

- 컴파일러 내부구조
- GPU 그래픽스
- 특정 제품 프레임워크

**종료 능력**

- C++ 프로젝트를 빈 디렉터리에서 시작한다
- 소유권과 오류 경계를 타입으로 표현한다
- 테스트 가능한 시스템 또는 애플리케이션을 완성한다

### `java` — Java 애플리케이션 개발

Java·JVM·Maven·JUnit을 이용해 객체 불변식, 동시성, 빌드와 검증을 갖춘 애플리케이션을 만든다.

- **필수 의존성:** 없음
- **권장 기반:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **인접 연결:** [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- **일반적 후속 심화:** [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)

**소유 범위**

- Java 언어와 JVM 실행 경계
- 객체와 컬렉션 계약
- 동시성·실행기
- Maven·JUnit·품질 도구

**비소유 범위**

- Spring 프레임워크
- 데이터베이스 내부구조
- 분산 시스템 일반 원리

**종료 능력**

- Java 애플리케이션을 설계·빌드한다
- 동시 상태와 자원 수명을 검증한다
- Maven·JUnit 기반 변경을 제출한다

### `python` — Python 자동화와 검증

Python 실행 모델과 파일·프로세스·동시성을 이용해 재현 가능한 자동화 도구를 만든다.

- **필수 의존성:** 없음
- **권장 기반:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **인접 연결:** [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **일반적 후속 심화:** [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)

**소유 범위**

- Python 언어와 패키징
- 파일·CLI·구조화 데이터
- subprocess와 수명 관리
- 동시성·취소·테스트

**비소유 범위**

- 웹 프레임워크
- 데이터 분석·ML 자체
- 분산 실행 플랫폼

**종료 능력**

- 설치 가능한 Python CLI를 만든다
- 외부 프로세스를 제한하고 정리한다
- 결정적 테스트와 보고서를 작성한다


## 분야 진입

### `web-app` — 웹 애플리케이션 개발

HTML·CSS·JavaScript·TypeScript·React·API·PostgreSQL·인증·WebSocket을 연결해 작은 풀스택 앱을 만든다.

- **필수 의존성:** 없음
- **권장 기반:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **인접 연결:** [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)
- **일반적 후속 심화:** [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)

**소유 범위**

- 웹 실행 모델과 HTTP 애플리케이션
- 브라우저 UI와 상태
- API와 관계형 데이터 사용
- 세션·권한·CSRF·CORS
- WebSocket과 기본 테스트

**비소유 범위**

- 프런트엔드 대형 코드베이스 심화
- Spring 고유 경계
- DBMS 내부구조
- 공개 운영 인프라

**종료 능력**

- 작은 풀스택 웹 앱을 독립적으로 만든다
- 인증·데이터·실시간 상태를 검증한다
- 후속 웹 전문 트랙에 진입한다

### `web-infra` — 웹 인프라와 공개 운영

단일 Linux 호스트에서 컨테이너·DNS·TLS·배포·관측·백업·사고 대응을 갖춘 공개 서비스를 운영한다.

- **필수 의존성:** 없음
- **권장 기반:** [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- **인접 연결:** [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing)
- **일반적 후속 심화:** [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**소유 범위**

- Linux 호스트와 Docker Compose
- DNS·ACME·TLS
- 이미지·SBOM·provenance
- CI/CD·rollback
- secret·관측·backup·incident response

**비소유 범위**

- Kubernetes 다중 팀 플랫폼
- multi-region HA
- 애플리케이션 프레임워크 내부
- 분산 업무 상태 수렴

**종료 능력**

- 작은 서비스를 공개 배포한다
- 변경·장애·데이터 손실을 관찰하고 복구한다
- 새 호스트에서 정확한 릴리스를 재구축한다

### `cybersecurity` — 사이버보안 공격과 방어

공격 표면과 신뢰 경계를 조사하고 격리 환경에서 취약점을 재현·패치·회귀 검증·탐지·복구한다.

- **필수 의존성:** [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)
- **권장 기반:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)
- **인접 연결:** [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems), [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **일반적 후속 심화:** [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**소유 범위**

- 위협 모델과 공격 표면
- 애플리케이션·시스템 취약점 조사
- 권한 상승·자격 증명·내부 이동의 격리 실습
- 패치·회귀 테스트·탐지·사고 복원

**비소유 범위**

- 네트워크·OS·웹 기초 전체 재교육
- 실제 무단 공격
- 조직 규제·감사 전 과정
- 고급 exploit 연구 전부

**종료 능력**

- 허가된 환경에서 공격 경로를 증명한다
- root cause와 최소 패치를 만든다
- 동일 공격의 차단과 탐지를 검증한다

### `mobile-app` — 크로스플랫폼 모바일 애플리케이션

React Native·Expo를 중심으로 모바일 수명 주기·오프라인 상태·기기 권한·배포를 Android와 iOS에 연결한다.

- **필수 의존성:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- **권장 기반:** [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **인접 연결:** [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **일반적 후속 심화:** 없음

**소유 범위**

- 모바일 앱 수명 주기와 navigation
- 오프라인 캐시·동기화
- 카메라·위치·알림·background 작업
- Android·iOS 빌드·서명·배포
- 네이티브 모듈 경계 읽기

**비소유 범위**

- Kotlin·Swift 언어 전체
- 네이티브 Android·iOS 전문 트랙
- 모바일 백엔드 운영

**종료 능력**

- Android·iOS에서 동작하는 앱을 만든다
- 오프라인·권한·기기 기능 실패를 처리한다
- 실제 빌드와 배포 산출물을 검증한다

### `machine-learning` — 머신러닝 모델 개발

데이터 분리·baseline·학습·평가·오류 분석·신경망·transformer·fine-tuning·모델 전달을 하나의 실험 흐름으로 다룬다.

- **필수 의존성:** [`python`](https://github.com/seungwoo7050/guides/tree/python)
- **권장 기반:** [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms)
- **인접 연결:** [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **일반적 후속 심화:** [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)

**소유 범위**

- 데이터 분리와 평가
- 손실·최적화·일반화
- 신경망·attention·transformer
- fine-tuning과 모델 artifact
- 재현 가능한 inference와 모델 카드

**비소유 범위**

- 대규모 데이터 파이프라인 운영
- 에이전트 도구 실행
- 분산 GPU 시스템 전체
- 제품 웹 개발

**종료 능력**

- 데이터와 baseline을 정의한다
- 작은 모델을 학습·평가·개선한다
- 재현 가능한 모델 artifact와 추론 인터페이스를 제공한다

### `agentic-systems` — 에이전틱 시스템 개발

기존 모델을 구조화된 출력·검색·도구·상태·메모리·평가·권한과 연결해 장기 실행 소프트웨어 시스템을 만든다.

- **필수 의존성:** [`python`](https://github.com/seungwoo7050/guides/tree/python), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- **권장 기반:** [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)
- **인접 연결:** [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **일반적 후속 심화:** [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**소유 범위**

- 모델 API와 구조화된 출력
- RAG와 출처·권한 경계
- 도구 호출과 agent loop
- checkpoint·resume·취소·budget
- sandbox·identity·평가·trace

**비소유 범위**

- 모델 학습 원리 전체
- 일반 웹 개발 재교육
- 사이버보안 전체
- 대규모 플랫폼 운영 전체

**종료 능력**

- 도구를 사용하는 에이전트를 구현한다
- 외부 verifier로 성공을 판정한다
- 권한·네트워크·비용·실행 시간을 제한한다

### `game-development` — 게임 시스템과 엔진 기반 개발

게임 루프·시간·입력·장면·엔티티·자산·물리·애니메이션·오디오·네트워크 경계를 연결해 게임 코드베이스에 진입한다.

- **필수 의존성:** 없음
- **권장 기반:** [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)
- **인접 연결:** [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **일반적 후속 심화:** [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)

**소유 범위**

- 고정·가변 시간 단계와 game loop
- 입력·카메라·장면·엔티티·컴포넌트의 상태 경계
- 자산 로딩·직렬화·resource lifetime과 editor workflow
- 물리·애니메이션·오디오·렌더링 하위 시스템의 게임 계층 통합
- 게임플레이 기능의 상태 전이·저장·재현·테스트
- frame budget·profiling·client/server authoritative 경계의 게임 맥락

**비소유 범위**

- GPU 렌더링 파이프라인과 shader 내부구조
- 운영체제·네트워크 프로토콜·분산 합의의 일반 원리
- 특정 상용 엔진 API 전체
- 게임 기획·아트·사운드 제작 직무 교육

**종료 능력**

- 기존 엔진 프로젝트의 update·render·asset·tool 경계를 복원한다
- 입력부터 상태·표현·저장까지 이어지는 작은 게임플레이 기능을 구현한다
- frame·resource·simulation 실패를 재현하고 profiling 근거로 수정한다


## 심화·전문화

### `web-front-react-nextjs` — React와 Next.js 프런트엔드 설계

기존 Next.js 코드베이스에 합류해 상태·동시성·접근성·성능·운영 산출물까지 수직 기능을 완성한다.

- **필수 의존성:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- **권장 기반:** [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)
- **인접 연결:** [`mobile-app`](https://github.com/seungwoo7050/guides/tree/mobile-app), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **일반적 후속 심화:** [`mobile-app`](https://github.com/seungwoo7050/guides/tree/mobile-app)

**소유 범위**

- Next.js 프로젝트 합류
- UI·URL·서버 데이터 상태 소유권
- 요청 취소·순서 역전·충돌 복구
- 접근성·성능·브라우저 검증

**비소유 범위**

- 웹 기초 재교육
- 호스트·DNS·TLS 운영
- 네이티브 모바일 플랫폼 전체

**종료 능력**

- 기존 프런트엔드 저장소의 실행 경계를 복원한다
- 운영 가능한 수직 기능을 구현한다
- 접근성·성능·동시성 실패를 자동 검증한다

### `backend-spring-boot` — Java와 Spring Boot 백엔드

Spring Core·MVC·Security·JPA·Redis·Kafka·외부 HTTP·Testcontainers·Actuator를 하나의 서비스 경계로 연결한다.

- **필수 의존성:** [`java`](https://github.com/seungwoo7050/guides/tree/java), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- **권장 기반:** [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **인접 연결:** [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **일반적 후속 심화:** [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)

**소유 범위**

- Spring Bean과 설정 수명
- MVC·Security 요청 경계
- JPA·Flyway·Redis 어댑터
- Kafka·외부 HTTP 클라이언트
- Spring 기반 통합 테스트·운영 지표

**비소유 범위**

- Java 언어 자체
- DBMS 내부구조
- 분산 시스템 일반 이론
- 호스트 운영

**종료 능력**

- 기존 Spring 코드베이스에 합류한다
- 보안·트랜잭션·외부 연동을 포함한 기능을 구현한다
- 통합 테스트와 운영 신호로 경계를 검증한다

### `database-systems` — 데이터베이스 시스템

관계 의미론·인덱스·저장 엔진·MVCC·WAL·실행 계획·안전한 마이그레이션을 애플리케이션과 DBMS 양쪽에서 다룬다.

- **필수 의존성:** 없음
- **권장 기반:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **인접 연결:** [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)
- **일반적 후속 심화:** [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)

**소유 범위**

- 관계 모델과 제약
- 페이지·인덱스·버퍼 풀
- MVCC·잠금·WAL
- 질의 실행과 계획
- 마이그레이션과 운영 질의 검토

**비소유 범위**

- 웹 프레임워크
- 서비스 간 saga
- 분산 합의·복제 전체
- 데이터 파이프라인 orchestration

**종료 능력**

- 스키마·트랜잭션·질의를 정확성 기준으로 설계한다
- 인덱스와 실행 계획을 해석한다
- 저장·동시성·복구 내부 동작을 설명한다

### `distributed-services` — 분산 서비스 설계와 복구

서비스 사이의 부분 실패·중복·순서 역전·불확실한 결과를 멱등성·Outbox·Saga·재조정으로 수렴시킨다.

- **필수 의존성:** [`java`](https://github.com/seungwoo7050/guides/tree/java), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- **권장 기반:** [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot)
- **인접 연결:** [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **일반적 후속 심화:** [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**소유 범위**

- 서비스 간 정본과 명령 경계
- 멱등성·Outbox·Saga
- retry·Circuit Breaker·DLQ·역압
- 릴리스 조합과 장애 실험

**비소유 범위**

- 합의 알고리즘
- DBMS 저장 엔진
- Kubernetes 플랫폼
- Spring 어댑터 사용법

**종료 능력**

- UNKNOWN 결과와 중복 전달을 모델링한다
- 부분 실패 뒤 상태를 수렴시킨다
- 다중 서비스 장애를 재현·복구한다

### `cloud-computing` — 클라우드 컴퓨팅과 서비스 모델

공유 책임·region·availability zone·control plane을 바탕으로 IaaS·PaaS·SaaS와 VM·container·FaaS의 책임·실패·비용·고객 tenant 경계를 비교하고 검증한다.

- **필수 의존성:** [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **권장 기반:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **인접 연결:** [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)
- **일반적 후속 심화:** [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**소유 범위**

- on-demand·resource pooling·elasticity·measured service와 공급자·소비자 공유 책임
- region·availability zone·failure domain과 compute·network·storage·identity의 관리 경계
- IaaS·PaaS·SaaS 서비스 모델과 VM·container·CaaS·serverless/FaaS 실행 모델의 구분
- FaaS event source·delivery·concurrency·cold start·timeout 제약에 기존 전달 계약을 적용하는 방법
- 고객 조직을 위한 SaaS tenant 수명·control/data plane·격리·metering·quota·export·deletion
- 예산·탄력성·가용성·portability·vendor lock-in의 근거 기반 비교

**비소유 범위**

- 단일 Linux 호스트·Docker Compose·DNS·TLS 운영 재교육
- 웹 프레임워크·인증·업무 도메인 구현 전체
- 일반적인 retry·idempotency·Outbox·Saga·DLQ와 분산 합의 재교육
- DBMS 내부구조와 tenant 관계 스키마·제약 설계 전체
- 자격 증명 공격·취약점 탐지·사고 복구 같은 보안 전문 과정
- 여러 내부 팀·workload의 Kubernetes·IaC module·golden path·self-service tenancy 플랫폼 운영
- 특정 클라우드 공급자의 제품 목록·자격증 전 범위

**종료 능력**

- 마케팅 명칭이 아니라 소비자와 공급자의 책임 경계로 cloud service를 분류한다
- 같은 workload를 IaaS·managed platform·FaaS에 배치하고 실패·비용·운영 책임의 변화를 설명한다
- 작은 SaaS의 공급자·고객 책임, control/data plane, tenant별 격리 요구·metering·quota·data lifecycle 계약을 정의하고 구현 소유 브랜치에 연결한다
- 예산·최소 권한·관측·cleanup 근거를 갖춘 격리된 cloud 실험을 재현하고 한계를 설명한다

### `distributed-systems` — 분산 시스템과 복제 상태 기계

시간·순서·장애 모델부터 복제·일관성·합의·sharding·재구성까지 분산 저장 시스템의 핵심을 구현·검증한다.

- **필수 의존성:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **권장 기반:** [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- **인접 연결:** [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **일반적 후속 심화:** 없음

**소유 범위**

- 분산 시간·순서·failure detector
- 복제와 일관성 모델
- leader election·합의·replicated log
- snapshot·membership change·sharding
- 결정적 장애 주입과 history 검증

**비소유 범위**

- 서비스 업무 saga 재교육
- DBMS 단일 노드 내부 전체
- Kubernetes 운영
- 특정 클라우드 제품

**종료 능력**

- 복제 상태 기계의 safety·liveness를 설명한다
- partition과 leader 교체를 재현한다
- 작은 분산 저장소를 구현·검증한다

### `data-engineering` — 데이터 엔지니어링

여러 원천의 데이터를 schema·batch·stream·CDC·품질·lineage·backfill·replay로 신뢰 가능한 데이터 제품으로 만든다.

- **필수 의존성:** [`python`](https://github.com/seungwoo7050/guides/tree/python), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **권장 기반:** [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)
- **인접 연결:** [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **일반적 후속 심화:** [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**소유 범위**

- 데이터 계약과 schema evolution
- batch·stream 처리
- event time·window·late data
- CDC·warehouse·lake
- orchestration·quality·lineage·backfill

**비소유 범위**

- 모델 학습
- DBMS 내부구조 전체
- 애플리케이션 saga
- 플랫폼 자원 provisioning 전체

**종료 능력**

- 재실행 가능한 데이터 파이프라인을 설계한다
- late event와 backfill을 처리한다
- 품질·freshness·lineage를 운영 근거로 남긴다

### `platform-engineering` — 플랫폼 엔지니어링

여러 팀이 서비스를 self-service로 생성·검증·배포·관찰하도록 IaC·오케스트레이션·정책·공통 서비스를 플랫폼으로 제공한다.

- **필수 의존성:** [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **권장 기반:** [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)
- **인접 연결:** [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **일반적 후속 심화:** 없음

**소유 범위**

- 플랫폼 사용자와 golden path
- Infrastructure as Code와 drift
- 컨테이너 오케스트레이션
- 재사용 가능한 CI/CD·GitOps
- identity·secret·관측·catalog·multi-tenancy

**비소유 범위**

- 단일 서비스 공개 운영 재교육
- 애플리케이션 도메인 로직
- 조직 문화 일반론만의 DevOps
- 특정 클라우드 자격증 범위

**종료 능력**

- self-service 서비스 경로를 설계한다
- 정책·배포·관측을 플랫폼 계약으로 자동화한다
- 플랫폼 SLO·용량·업그레이드를 운영한다

### `language-implementation` — 프로그래밍 언어 구현과 도구

lexer·parser·AST·타입 검사·interpreter·bytecode·IR·정적 분석·언어 서버의 경계를 구현한다.

- **필수 의존성:** [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)
- **권장 기반:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **인접 연결:** 없음
- **일반적 후속 심화:** 없음

**소유 범위**

- 문법·파서·AST
- scope·symbol·type checking·diagnostic
- interpreter·VM·runtime
- IR·CFG·data-flow·최적화
- formatter·linter·static analyzer·language server

**비소유 범위**

- C++ 언어 기초
- 특정 상용 컴파일러 전체
- CPU microarchitecture 설계

**종료 능력**

- 작은 언어의 frontend를 만든다
- 정적 타입과 실행 모델을 구현한다
- 분석·진단·변환 도구를 확장한다

### `embedded-systems` — 임베디드 시스템과 펌웨어

MCU·메모리 배치·MMIO·interrupt·DMA·RTOS·driver·watchdog·firmware update를 제한된 자원과 시간 계약으로 다룬다.

- **필수 의존성:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **권장 기반:** [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **인접 연결:** 없음
- **일반적 후속 심화:** 없음

**소유 범위**

- firmware image와 linker·memory map
- GPIO·UART·I2C·SPI·MMIO
- interrupt·timer·DMA
- RTOS task·queue·priority
- watchdog·bootloader·안전한 update

**비소유 범위**

- 일반 POSIX 애플리케이션
- 전자회로 설계 전체
- 모바일 앱
- 특정 보드 제품 매뉴얼 전체

**종료 능력**

- 펌웨어의 메모리·시간·전력 경계를 설명한다
- interrupt와 task 사이 상태를 안전하게 전달한다
- 실패 복구와 update 상태 기계를 검증한다

### `computer-graphics` — 컴퓨터 그래픽스와 GPU 렌더링

벡터·행렬·이미지·rasterization·shader·GPU resource·동기화·frame budget을 software renderer와 GPU pipeline으로 연결한다.

- **필수 의존성:** [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)
- **권장 기반:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **인접 연결:** [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **일반적 후속 심화:** 없음

**소유 범위**

- 좌표계·camera·projection
- image·color·sampling
- software rasterization
- shader와 GPU pipeline
- resource lifetime·CPU/GPU synchronization·profiling

**비소유 범위**

- C++ 기초
- 게임 엔진 전체
- 3D 아트 제작
- GPU 하드웨어 설계

**종료 능력**

- 작은 software renderer를 구현한다
- 같은 장면을 GPU pipeline으로 옮긴다
- frame-time과 자원 수명을 측정·진단한다
