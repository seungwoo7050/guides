# 업무 분야별 트랙

> 이 문서는 `catalog/tracks.json`과 브랜치 의존성에서 생성된다. 직접 수정하지 않는다.

트랙은 모든 브랜치를 나열하는 커리큘럼이 아니다. 목표 업무에 필요한 **핵심 경로**, 인접 협업에 필요한 **권장 폭**, 이후 전문화를 위한 **심화 경로**를 구분한다.

## 트랙 요약

| 트랙 | 핵심 브랜치 | 목표 |
|---|---|---|
| [공통 개발 역량](#software-foundations) | `git`, (`c` / `cpp` / `java` / `python` / `web-app` 중 하나) | 업무 분야를 정하기 전 변경 관리, 한 개의 구현 언어, 문제 검증과 시스템 관찰의 최소 기반을 만든다. |
| [웹 백엔드 개발](#web-backend) | `git`, `web-app`, `java`, `backend-spring-boot`, `database-systems` | HTTP·Java·Spring·관계형 데이터와 운영 경계를 연결해 기존 백엔드 서비스에 합류한다. |
| [웹 프런트엔드 개발](#web-frontend) | `git`, `web-app`, `web-front-react-nextjs` | 브라우저·React·Next.js 상태와 접근성·성능·운영 빌드를 연결한다. |
| [풀스택 웹 개발](#full-stack-web) | `git`, `web-app`, `web-front-react-nextjs`, `java`, `backend-spring-boot`, `database-systems`, `web-infra` | 브라우저부터 API·데이터베이스·배포까지 작은 제품의 전체 흐름을 독립적으로 소유한다. |
| [인프라·플랫폼 엔지니어링](#infrastructure-platform) | `git`, `unix-systems`, `computer-networks`, `web-infra`, `platform-engineering` | 단일 서비스 공개 운영에서 여러 팀의 self-service 플랫폼까지 확장한다. |
| [사이버보안](#cybersecurity) | `git`, `unix-systems`, `computer-networks`, `web-app`, `cybersecurity` | 시스템과 웹의 공격 표면을 이해하고, 허가된 환경에서 공격·수정·탐지·복구를 한 흐름으로 수행한다. |
| [모바일 애플리케이션 개발](#mobile) | `git`, `web-app`, `mobile-app` | 웹·React 기반을 모바일 수명 주기, 오프라인 상태, 기기 기능과 Android·iOS 배포로 확장한다. |
| [머신러닝 모델 개발](#machine-learning) | `git`, `python`, `machine-learning` | 데이터·학습·평가·오류 분석·모델 전달의 재현 가능한 흐름을 만든다. |
| [에이전틱 시스템 개발](#agentic-systems) | `git`, `python`, `web-app`, `agentic-systems` | 모델을 도구·상태·검색·평가·권한과 연결해 실제 작업을 수행하는 시스템을 만든다. |
| [데이터 엔지니어링](#data-engineering) | `git`, `python`, `database-systems`, `data-engineering` | 운영 데이터와 이벤트를 batch·stream·CDC·품질·lineage·backfill로 신뢰 가능한 데이터 제품으로 만든다. |
| [분산 시스템 개발](#distributed-systems) | `git`, `operating-systems`, `computer-networks`, `database-systems`, `distributed-systems`, (`c` / `cpp` / `java` / `python` 중 하나) | 부분 실패를 넘어 복제·합의·일관성·sharding을 구현하고 장애 history로 검증한다. |
| [데이터베이스 엔지니어링](#database-engineering) | `git`, `database-systems`, (`c` / `cpp` / `java` / `python` 중 하나) | 애플리케이션 스키마와 질의부터 저장 엔진·동시성·복구·분산 저장까지 데이터 시스템을 깊게 다룬다. |
| [시스템 프로그래밍](#systems-programming) | `git`, `unix-systems`, `computer-architecture`, `operating-systems`, (`c` / `cpp` 중 하나) | 자원 수명·프로세스·메모리·동시성·하드웨어 계약을 연결해 저수준 프로젝트에 진입한다. |
| [컴파일러·언어 도구 개발](#language-tooling) | `git`, `cpp`, `algorithms`, `computer-architecture`, `language-implementation` | 언어 문법과 의미 분석에서 실행기·IR·정적 분석·IDE 도구까지 구현한다. |
| [임베디드·펌웨어 개발](#embedded) | `git`, `c`, `computer-architecture`, `operating-systems`, `embedded-systems` | 제한된 메모리와 시간, 주변장치와 interrupt, RTOS와 안전한 update를 다룬다. |
| [컴퓨터 그래픽스 개발](#graphics) | `git`, `cpp`, `algorithms`, `computer-architecture`, `computer-graphics` | 수학·C++·하드웨어 성능 기반 위에서 rasterizer와 GPU renderer를 만든다. |

## 공통 개발 역량

<a id="software-foundations"></a>

업무 분야를 정하기 전 변경 관리, 한 개의 구현 언어, 문제 검증과 시스템 관찰의 최소 기반을 만든다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** 없음
- **택일 필수:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) 중 하나
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **택일 선택별 추가 의존성 순서:**
  - [`c`](https://github.com/seungwoo7050/guides/tree/c) 선택: [`c`](https://github.com/seungwoo7050/guides/tree/c)
  - [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) 선택: [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp)
  - [`java`](https://github.com/seungwoo7050/guides/tree/java) 선택: [`java`](https://github.com/seungwoo7050/guides/tree/java)
  - [`python`](https://github.com/seungwoo7050/guides/tree/python) 선택: [`python`](https://github.com/seungwoo7050/guides/tree/python)
  - [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) 선택: [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- **권장 인접 지식:** [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)
- **후속 심화:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)

**트랙 종료 능력**

- 작은 프로젝트를 시작하고 변경을 검토한다
- 오류를 재현하고 증거를 남긴다
- 원하는 전문 트랙의 선행 부족을 스스로 보완한다


## 웹 백엔드 개발

<a id="web-backend"></a>

HTTP·Java·Spring·관계형 데이터와 운영 경계를 연결해 기존 백엔드 서비스에 합류한다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **권장 인접 지식:** [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **후속 심화:** [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**트랙 종료 능력**

- 수직 기능을 API·DB·권한·테스트까지 구현한다
- 트랜잭션과 실패 뒤 상태를 설명한다
- 로그·metric·DB 증거로 장애 계층을 좁힌다


## 웹 프런트엔드 개발

<a id="web-frontend"></a>

브라우저·React·Next.js 상태와 접근성·성능·운영 빌드를 연결한다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs)
- **권장 인접 지식:** [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **후속 심화:** [`mobile-app`](https://github.com/seungwoo7050/guides/tree/mobile-app), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)

**트랙 종료 능력**

- 기존 프런트엔드 저장소의 상태·라우트·빌드 경계를 복원한다
- 동시성과 접근성을 포함한 기능을 완성한다
- 실제 브라우저와 운영 빌드로 결과를 검증한다


## 풀스택 웹 개발

<a id="full-stack-web"></a>

브라우저부터 API·데이터베이스·배포까지 작은 제품의 전체 흐름을 독립적으로 소유한다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **권장 인접 지식:** [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- **후속 심화:** [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)

**트랙 종료 능력**

- 작은 웹 제품을 종단 간 구현한다
- 상태 소유권과 배포 경계를 설명한다
- 기능 실패와 운영 실패를 분리해 복구한다


## 인프라·플랫폼 엔지니어링

<a id="infrastructure-platform"></a>

단일 서비스 공개 운영에서 여러 팀의 self-service 플랫폼까지 확장한다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **권장 인접 지식:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)
- **후속 심화:** [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)

**트랙 종료 능력**

- 서비스와 플랫폼의 책임을 분리한다
- 배포·정책·관측·복구를 자동화한다
- 여러 팀이 사용하는 운영 경로를 제품처럼 관리한다


## 사이버보안

<a id="cybersecurity"></a>

시스템과 웹의 공격 표면을 이해하고, 허가된 환경에서 공격·수정·탐지·복구를 한 흐름으로 수행한다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **권장 인접 지식:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)
- **후속 심화:** [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems)

**트랙 종료 능력**

- 공격 전제와 경로를 증거로 남긴다
- 취약점을 패치하고 회귀 검사를 만든다
- 침해 시도와 복구 타임라인을 재구성한다


## 모바일 애플리케이션 개발

<a id="mobile"></a>

웹·React 기반을 모바일 수명 주기, 오프라인 상태, 기기 기능과 Android·iOS 배포로 확장한다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`mobile-app`](https://github.com/seungwoo7050/guides/tree/mobile-app)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`mobile-app`](https://github.com/seungwoo7050/guides/tree/mobile-app)
- **권장 인접 지식:** [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **후속 심화:** 없음

**트랙 종료 능력**

- Android·iOS 공통 기능을 구현한다
- 오프라인·권한·background 실패를 처리한다
- 실제 기기와 배포 artifact로 완료를 증명한다


## 머신러닝 모델 개발

<a id="machine-learning"></a>

데이터·학습·평가·오류 분석·모델 전달의 재현 가능한 흐름을 만든다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`python`](https://github.com/seungwoo7050/guides/tree/python), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)
- **권장 인접 지식:** [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)
- **후속 심화:** [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)

**트랙 종료 능력**

- baseline과 평가 기준을 정의한다
- 모델을 학습·개선하고 실패 사례를 분석한다
- 모델 artifact와 추론 경계를 재현 가능하게 전달한다


## 에이전틱 시스템 개발

<a id="agentic-systems"></a>

모델을 도구·상태·검색·평가·권한과 연결해 실제 작업을 수행하는 시스템을 만든다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`python`](https://github.com/seungwoo7050/guides/tree/python), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)
- **권장 인접 지식:** [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **후속 심화:** [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**트랙 종료 능력**

- 도구 호출 agent를 구현한다
- 외부 verifier로 결과를 판정한다
- 권한·비용·실행·네트워크 한계를 강제한다


## 데이터 엔지니어링

<a id="data-engineering"></a>

운영 데이터와 이벤트를 batch·stream·CDC·품질·lineage·backfill로 신뢰 가능한 데이터 제품으로 만든다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`python`](https://github.com/seungwoo7050/guides/tree/python), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)
- **권장 인접 지식:** [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **후속 심화:** [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)

**트랙 종료 능력**

- 재실행 가능한 pipeline을 설계한다
- late data와 backfill을 처리한다
- 품질·freshness·lineage를 운영한다


## 분산 시스템 개발

<a id="distributed-systems"></a>

부분 실패를 넘어 복제·합의·일관성·sharding을 구현하고 장애 history로 검증한다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)
- **택일 필수:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`python`](https://github.com/seungwoo7050/guides/tree/python) 중 하나
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)
- **택일 선택별 추가 의존성 순서:**
  - [`c`](https://github.com/seungwoo7050/guides/tree/c) 선택: [`c`](https://github.com/seungwoo7050/guides/tree/c)
  - [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) 선택: [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp)
  - [`java`](https://github.com/seungwoo7050/guides/tree/java) 선택: [`java`](https://github.com/seungwoo7050/guides/tree/java)
  - [`python`](https://github.com/seungwoo7050/guides/tree/python) 선택: [`python`](https://github.com/seungwoo7050/guides/tree/python)
- **권장 인접 지식:** [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **후속 심화:** 없음

**트랙 종료 능력**

- safety와 liveness를 구분한다
- leader 교체와 partition을 재현한다
- 복제 저장 시스템의 history를 검증한다


## 데이터베이스 엔지니어링

<a id="database-engineering"></a>

애플리케이션 스키마와 질의부터 저장 엔진·동시성·복구·분산 저장까지 데이터 시스템을 깊게 다룬다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **택일 필수:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`python`](https://github.com/seungwoo7050/guides/tree/python) 중 하나
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **택일 선택별 추가 의존성 순서:**
  - [`c`](https://github.com/seungwoo7050/guides/tree/c) 선택: [`c`](https://github.com/seungwoo7050/guides/tree/c)
  - [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) 선택: [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp)
  - [`java`](https://github.com/seungwoo7050/guides/tree/java) 선택: [`java`](https://github.com/seungwoo7050/guides/tree/java)
  - [`python`](https://github.com/seungwoo7050/guides/tree/python) 선택: [`python`](https://github.com/seungwoo7050/guides/tree/python)
- **권장 인접 지식:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms)
- **후속 심화:** [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)

**트랙 종료 능력**

- 질의와 저장 엔진 동작을 연결한다
- 동시성·복구 실패를 설명한다
- 데이터 계층의 변경과 마이그레이션을 안전하게 설계한다


## 시스템 프로그래밍

<a id="systems-programming"></a>

자원 수명·프로세스·메모리·동시성·하드웨어 계약을 연결해 저수준 프로젝트에 진입한다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **택일 필수:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) 중 하나
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **택일 선택별 추가 의존성 순서:**
  - [`c`](https://github.com/seungwoo7050/guides/tree/c) 선택: [`c`](https://github.com/seungwoo7050/guides/tree/c)
  - [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) 선택: [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp)
- **권장 인접 지식:** [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **후속 심화:** [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems), [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)

**트랙 종료 능력**

- 자원과 상태의 소유자를 명확히 한다
- 프로세스·메모리·동시성 실패를 재현한다
- 시스템 코드 변경을 sanitizer와 상태 근거로 검증한다


## 컴파일러·언어 도구 개발

<a id="language-tooling"></a>

언어 문법과 의미 분석에서 실행기·IR·정적 분석·IDE 도구까지 구현한다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation)
- **권장 인접 지식:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **후속 심화:** 없음

**트랙 종료 능력**

- parser와 타입 검사기를 만든다
- 작은 interpreter·VM·IR을 구현한다
- 진단·분석·변환 도구에 기여한다


## 임베디드·펌웨어 개발

<a id="embedded"></a>

제한된 메모리와 시간, 주변장치와 interrupt, RTOS와 안전한 update를 다룬다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems)
- **권장 인접 지식:** [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **후속 심화:** 없음

**트랙 종료 능력**

- MMIO·interrupt·task 경계를 구현한다
- 실시간 실패와 watchdog 복구를 검증한다
- firmware update 상태를 안전하게 관리한다


## 컴퓨터 그래픽스 개발

<a id="graphics"></a>

수학·C++·하드웨어 성능 기반 위에서 rasterizer와 GPU renderer를 만든다.

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics)
- **권장 인접 지식:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **후속 심화:** 없음

**트랙 종료 능력**

- software rasterizer를 구현한다
- shader와 GPU resource를 관리한다
- frame budget과 동기화 병목을 측정한다
