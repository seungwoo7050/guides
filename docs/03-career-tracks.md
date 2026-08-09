# 업무 분야별 트랙

> 이 문서는 `catalog/tracks.json`과 브랜치 의존성에서 생성된다. 직접 수정하지 않는다.

트랙은 모든 브랜치를 나열하는 커리큘럼이 아니다. 목표 업무에 필요한 **핵심 경로**, 인접 협업에 필요한 **권장 폭**, 이후 전문화를 위한 **심화 경로**를 구분한다.

`권장 선형 경로`는 처음 시작하는 사람이 순서대로 진행할 실제 학습 경로다. 엄밀한 필수 의존성만 뜻하지 않으며, 직무 진입에 유용한 권장 기반을 포함할 수 있다.

## 트랙 요약

| 분야 | 트랙 | 권장 경로 | 목표 |
|---|---|---|---|
| 공통 시작점 | [공통 개발 역량](#software-foundations) | 5개 — C 기반 / C++ 기반 / Java 기반 / Python 기반 / 웹 기반 | 업무 분야를 정하기 전 변경 관리, 한 개의 구현 언어, 문제 검증과 시스템 관찰의 최소 기반을 만든다. |
| 웹 개발 | [웹 백엔드 개발](#web-backend) | `git` → `web-app` → `java` → `backend-spring-boot` → `database-systems` → `web-infra` | HTTP·Java·Spring·관계형 데이터와 운영 경계를 연결해 기존 백엔드 서비스에 합류한다. |
| 웹 개발 | [웹 프런트엔드 개발](#web-frontend) | `git` → `web-app` → `web-front-react-nextjs` → `web-infra` | 브라우저·React·Next.js 상태와 접근성·성능·운영 빌드를 연결한다. |
| 웹 개발 | [풀스택 웹 개발](#full-stack-web) | `git` → `web-app` → `web-front-react-nextjs` → `java` → `backend-spring-boot` → `database-systems` → `web-infra` | 브라우저부터 API·데이터베이스·배포까지 작은 제품의 전체 흐름을 독립적으로 소유한다. |
| 웹 개발 | [SaaS 제품 개발](#saas-product-engineering) | 2개 — 작은 SaaS 제품 / Spring 기반 SaaS | 웹 제품을 고객 tenant·조직·권한·구독·quota·metering·감사·데이터 수명과 cloud 책임 경계까지 확장한다. |
| 인프라·클라우드·플랫폼·보안 | [클라우드 엔지니어링](#cloud-engineering) | `git` → `unix-systems` → `computer-networks` → `web-infra` → `cloud-computing` | 단일 호스트 운영을 cloud resource·managed service·serverless·shared responsibility·비용·failure domain 설계로 확장한다. |
| 인프라·클라우드·플랫폼·보안 | [인프라·플랫폼 엔지니어링](#infrastructure-platform) | 2개 — 호스트 운영에서 플랫폼까지 / 클라우드 기반 플랫폼 | 단일 서비스 공개 운영에서 여러 팀의 self-service 플랫폼까지 확장한다. |
| 인프라·클라우드·플랫폼·보안 | [사이버보안](#cybersecurity) | `git` → `unix-systems` → `computer-networks` → `web-app` → `web-infra` → `cybersecurity` | 시스템과 웹의 공격 표면을 이해하고, 허가된 환경에서 공격·수정·탐지·복구를 한 흐름으로 수행한다. |
| 모바일 애플리케이션 | [모바일 애플리케이션 개발](#mobile) | `git` → `web-app` → `web-front-react-nextjs` → `mobile-app` | 웹·React 기반을 모바일 수명 주기, 오프라인 상태, 기기 기능과 Android·iOS 배포로 확장한다. |
| AI·데이터 | [머신러닝 모델 개발](#machine-learning) | `git` → `python` → `algorithms` → `machine-learning` | 데이터·학습·평가·오류 분석·모델 전달의 재현 가능한 흐름을 만든다. |
| AI·데이터 | [에이전틱 시스템 개발](#agentic-systems) | `git` → `python` → `web-app` → `agentic-systems` | 모델을 도구·상태·검색·평가·권한과 연결해 실제 작업을 수행하는 시스템을 만든다. |
| AI·데이터 | [데이터 엔지니어링](#data-engineering) | `git` → `python` → `database-systems` → `data-engineering` | 운영 데이터와 이벤트를 batch·stream·CDC·품질·lineage·backfill로 신뢰 가능한 데이터 제품으로 만든다. |
| 시스템·저수준·개발 도구 | [분산 시스템 개발](#distributed-systems) | `git` → `c` → `computer-architecture` → `operating-systems` → `computer-networks` → `database-systems` → `distributed-systems` | 부분 실패를 넘어 복제·합의·일관성·sharding을 구현하고 장애 history로 검증한다. |
| 시스템·저수준·개발 도구 | [데이터베이스 엔지니어링](#database-engineering) | 2개 — DBMS 내부구조 / 애플리케이션·데이터 | 애플리케이션 스키마와 질의부터 저장 엔진·동시성·복구까지 깊게 다루고, 분산 저장과 데이터 파이프라인으로 확장한다. |
| 시스템·저수준·개발 도구 | [시스템 프로그래밍](#systems-programming) | 2개 — C 시스템 경로 / C++ 시스템 경로 | 자원 수명·프로세스·메모리·동시성·하드웨어 계약을 연결해 저수준 프로젝트에 진입한다. |
| 시스템·저수준·개발 도구 | [컴파일러·언어 도구 개발](#language-tooling) | `git` → `c` → `cpp` → `algorithms` → `computer-architecture` → `language-implementation` | 언어 문법과 의미 분석에서 실행기·IR·정적 분석·IDE 도구까지 구현한다. |
| 시스템·저수준·개발 도구 | [임베디드·펌웨어 개발](#embedded) | `git` → `c` → `computer-architecture` → `operating-systems` → `embedded-systems` | 제한된 메모리와 시간, 주변장치와 interrupt, RTOS와 안전한 update를 다룬다. |
| 시스템·저수준·개발 도구 | [컴퓨터 그래픽스 개발](#graphics) | `git` → `c` → `cpp` → `algorithms` → `computer-architecture` → `computer-graphics` | 수학·C++·하드웨어 성능 기반 위에서 rasterizer와 GPU renderer를 만든다. |
| 게임회사 개발 직군 | [게임회사 — 클라이언트·게임플레이 개발](#game-client-gameplay) | 2개 — 프로그래밍부터 시작 / 다른 언어 경험자 | 엔진 프로젝트에서 입력·게임 상태·장면·자산·표현을 연결하는 게임플레이 기능을 구현한다. |
| 게임회사 개발 직군 | [게임회사 — 엔진·코어 시스템 개발](#game-engine-core) | `git` → `c` → `cpp` → `algorithms` → `computer-architecture` → `operating-systems` → `game-development` | 메모리·동시성·플랫폼·resource lifetime을 게임 루프와 연결해 엔진 하위 시스템을 다룬다. |
| 게임회사 개발 직군 | [게임회사 — 렌더링·그래픽스 개발](#game-rendering) | `git` → `c` → `cpp` → `algorithms` → `computer-architecture` → `game-development` → `computer-graphics` | 게임 엔진 맥락과 GPU 렌더링 파이프라인을 연결해 화면 품질과 frame budget을 다룬다. |
| 게임회사 개발 직군 | [게임회사 — Java/Spring 게임 서버 개발](#game-server) | `git` → `web-app` → `java` → `backend-spring-boot` → `database-systems` → `game-development` → `computer-networks` → `distributed-services` → `web-infra` | Java와 Spring 기반에서 권위 상태·세션·매치·실시간 통신·영속화·부분 실패를 운영 가능한 게임 서버로 연결한다. |
| 게임회사 개발 직군 | [게임회사 — 개발 도구·빌드·플랫폼](#game-tools-platform) | `git` → `python` → `unix-systems` → `game-development` → `web-infra` → `platform-engineering` | asset·build·test·배포 workflow를 자동화하고 여러 개발자가 반복 사용하는 내부 경로를 만든다. |
| 게임회사 개발 직군 | [게임회사 — 데이터·머신러닝 개발](#game-data-ml) | `git` → `python` → `algorithms` → `game-development` → `database-systems` → `data-engineering` → `machine-learning` | 플레이 이벤트·운영 데이터·모델 평가를 신뢰 가능한 pipeline과 게임 도메인 의사결정에 연결한다. |
| 게임회사 개발 직군 | [게임회사 — 보안·안티치트 개발](#game-security-anticheat) | `git` → `c` → `cpp` → `algorithms` → `game-development` → `computer-architecture` → `operating-systems` → `unix-systems` → `computer-networks` → `cybersecurity` | 클라이언트·운영체제·네트워크·서버 신뢰 경계를 분석하고 조작 탐지와 안전한 대응을 설계한다. |

## 공통 시작점

목표 직무를 아직 정하지 않았을 때 구현 언어 하나와 변경·검증 기반을 선택한다.

### 공통 개발 역량

<a id="software-foundations"></a>

업무 분야를 정하기 전 변경 관리, 한 개의 구현 언어, 문제 검증과 시스템 관찰의 최소 기반을 만든다.

**권장 선형 경로**

1. **C 기반** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems)
2. **C++ 기반** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems)
3. **Java 기반** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`java`](https://github.com/seungwoo7050/guides/tree/java) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems)
4. **Python 기반** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`python`](https://github.com/seungwoo7050/guides/tree/python) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems)
5. **웹 기반** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) → [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)

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


## 웹 개발

프런트엔드·백엔드·풀스택·SaaS 제품은 책임 범위가 다르므로 직무별 선형 경로를 제공한다.

### 웹 백엔드 개발

<a id="web-backend"></a>

HTTP·Java·Spring·관계형 데이터와 운영 경계를 연결해 기존 백엔드 서비스에 합류한다.

**권장 선형 경로**

1. **백엔드 직무 진입** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) → [`java`](https://github.com/seungwoo7050/guides/tree/java) → [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot) → [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **권장 인접 지식:** [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **후속 심화:** [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**트랙 종료 능력**

- 수직 기능을 API·DB·권한·테스트까지 구현한다
- 트랜잭션과 실패 뒤 상태를 설명한다
- 로그·metric·DB 증거로 장애 계층을 좁힌다

### 웹 프런트엔드 개발

<a id="web-frontend"></a>

브라우저·React·Next.js 상태와 접근성·성능·운영 빌드를 연결한다.

**권장 선형 경로**

1. **프런트엔드 직무 진입** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) → [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)

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

### 풀스택 웹 개발

<a id="full-stack-web"></a>

브라우저부터 API·데이터베이스·배포까지 작은 제품의 전체 흐름을 독립적으로 소유한다.

**권장 선형 경로**

1. **풀스택 직무 진입** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) → [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs) → [`java`](https://github.com/seungwoo7050/guides/tree/java) → [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot) → [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **권장 인접 지식:** [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- **후속 심화:** [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)

**트랙 종료 능력**

- 작은 웹 제품을 종단 간 구현한다
- 상태 소유권과 배포 경계를 설명한다
- 기능 실패와 운영 실패를 분리해 복구한다

### SaaS 제품 개발

<a id="saas-product-engineering"></a>

웹 제품을 고객 tenant·조직·권한·구독·quota·metering·감사·데이터 수명과 cloud 책임 경계까지 확장한다.

**권장 선형 경로**

1. **작은 SaaS 제품** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) → [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) → [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing)
2. **Spring 기반 SaaS** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) → [`java`](https://github.com/seungwoo7050/guides/tree/java) → [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot) → [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) → [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing)
- **권장 인접 지식:** [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- **후속 심화:** [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)

**트랙 종료 능력**

- 고객 tenant와 사용자·조직·역할을 구분하고 API·DB 접근을 tenant 경계로 검증한다
- 구독·quota·metering·audit를 업무 상태와 cloud 비용 근거에 연결한다
- onboarding·migration·export·deletion·장애 복구를 고객 tenant 수명 주기로 설계·검증한다


## 인프라·클라우드·플랫폼·보안

단일 서비스 운영, cloud service model, 내부 플랫폼, 공격·방어는 인접하지만 서로 다른 상태와 실패를 소유한다.

### 클라우드 엔지니어링

<a id="cloud-engineering"></a>

단일 호스트 운영을 cloud resource·managed service·serverless·shared responsibility·비용·failure domain 설계로 확장한다.

**권장 선형 경로**

1. **클라우드 운영과 서비스 모델** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems) → [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) → [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing)
- **권장 인접 지식:** [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **후속 심화:** [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)

**트랙 종료 능력**

- IaaS·PaaS·SaaS와 VM·container·FaaS의 책임·권한·운영 경계를 구분한다
- region·availability zone·cloud identity·network·storage·compute를 failure domain과 비용 기준으로 설계한다
- 예산·최소 권한·관측·cleanup을 포함한 재현 가능한 cloud workload 실험을 수행하고 근거를 남긴다

### 인프라·플랫폼 엔지니어링

<a id="infrastructure-platform"></a>

단일 서비스 공개 운영에서 여러 팀의 self-service 플랫폼까지 확장한다.

**권장 선형 경로**

1. **호스트 운영에서 플랫폼까지** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems) → [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) → [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) → [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
2. **클라우드 기반 플랫폼** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems) → [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) → [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing) → [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) → [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **권장 인접 지식:** [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`cloud-computing`](https://github.com/seungwoo7050/guides/tree/cloud-computing)
- **후속 심화:** [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)

**트랙 종료 능력**

- 서비스와 플랫폼의 책임을 분리한다
- 배포·정책·관측·복구를 자동화한다
- 여러 팀이 사용하는 운영 경로를 제품처럼 관리한다

### 사이버보안

<a id="cybersecurity"></a>

시스템과 웹의 공격 표면을 이해하고, 허가된 환경에서 공격·수정·탐지·복구를 한 흐름으로 수행한다.

**권장 선형 경로**

1. **공격·방어 통합 진입** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems) → [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) → [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) → [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)

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


## 모바일 애플리케이션

웹·React 기반을 모바일 수명 주기·오프라인·기기 기능·배포로 확장한다.

### 모바일 애플리케이션 개발

<a id="mobile"></a>

웹·React 기반을 모바일 수명 주기, 오프라인 상태, 기기 기능과 Android·iOS 배포로 확장한다.

**권장 선형 경로**

1. **크로스플랫폼 모바일 진입** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) → [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs) → [`mobile-app`](https://github.com/seungwoo7050/guides/tree/mobile-app)

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


## AI·데이터

모델 학습, 에이전틱 시스템, 데이터 파이프라인을 독립적인 결과물 기준으로 분리한다.

### 머신러닝 모델 개발

<a id="machine-learning"></a>

데이터·학습·평가·오류 분석·모델 전달의 재현 가능한 흐름을 만든다.

**권장 선형 경로**

1. **모델 개발 진입** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`python`](https://github.com/seungwoo7050/guides/tree/python) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)

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

### 에이전틱 시스템 개발

<a id="agentic-systems"></a>

모델을 도구·상태·검색·평가·권한과 연결해 실제 작업을 수행하는 시스템을 만든다.

**권장 선형 경로**

1. **에이전트 시스템 진입** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`python`](https://github.com/seungwoo7050/guides/tree/python) → [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) → [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)

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

### 데이터 엔지니어링

<a id="data-engineering"></a>

운영 데이터와 이벤트를 batch·stream·CDC·품질·lineage·backfill로 신뢰 가능한 데이터 제품으로 만든다.

**권장 선형 경로**

1. **데이터 파이프라인 진입** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`python`](https://github.com/seungwoo7050/guides/tree/python) → [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) → [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)

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


## 시스템·저수준·개발 도구

운영체제·하드웨어·DBMS·컴파일러·그래픽스·임베디드 내부구조를 구현 수준으로 확장한다.

### 분산 시스템 개발

<a id="distributed-systems"></a>

부분 실패를 넘어 복제·합의·일관성·sharding을 구현하고 장애 history로 검증한다.

**권장 선형 경로**

1. **복제·합의 시스템 진입** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) → [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) → [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) → [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) → [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)

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

### 데이터베이스 엔지니어링

<a id="database-engineering"></a>

애플리케이션 스키마와 질의부터 저장 엔진·동시성·복구까지 깊게 다루고, 분산 저장과 데이터 파이프라인으로 확장한다.

**권장 선형 경로**

1. **DBMS 내부구조** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) → [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) → [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) → [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
2. **애플리케이션·데이터** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`python`](https://github.com/seungwoo7050/guides/tree/python) → [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)

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

### 시스템 프로그래밍

<a id="systems-programming"></a>

자원 수명·프로세스·메모리·동시성·하드웨어 계약을 연결해 저수준 프로젝트에 진입한다.

**권장 선형 경로**

1. **C 시스템 경로** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) → [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems)
2. **C++ 시스템 경로** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) → [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) → [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems)

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

### 컴파일러·언어 도구 개발

<a id="language-tooling"></a>

언어 문법과 의미 분석에서 실행기·IR·정적 분석·IDE 도구까지 구현한다.

**권장 선형 경로**

1. **컴파일러·언어 도구** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) → [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation)

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

### 임베디드·펌웨어 개발

<a id="embedded"></a>

제한된 메모리와 시간, 주변장치와 interrupt, RTOS와 안전한 update를 다룬다.

**권장 선형 경로**

1. **임베디드·펌웨어** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) → [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) → [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems)

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

### 컴퓨터 그래픽스 개발

<a id="graphics"></a>

수학·C++·하드웨어 성능 기반 위에서 rasterizer와 GPU renderer를 만든다.

**권장 선형 경로**

1. **컴퓨터 그래픽스** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) → [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics)

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


## 게임회사 개발 직군

게임회사 전체에 공통인 단일 기술 경로는 없다. 클라이언트·엔진·렌더링·서버·도구·데이터·보안 중 목표 개발 직군 하나를 선택한다. 기획·아트·사운드·사업 직군은 이 저장소의 범위가 아니다.

### 게임회사 — 클라이언트·게임플레이 개발

<a id="game-client-gameplay"></a>

엔진 프로젝트에서 입력·게임 상태·장면·자산·표현을 연결하는 게임플레이 기능을 구현한다.

**권장 선형 경로**

1. **프로그래밍부터 시작** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
2. **다른 언어 경험자** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **권장 인접 지식:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)
- **후속 심화:** [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)

**트랙 종료 능력**

- 기존 게임 프로젝트의 frame·scene·asset 경계를 복원한다
- 입력부터 상태·표현·저장까지 이어지는 작은 기능을 완성한다
- 기능 회귀와 frame/resource 문제를 재현한다

### 게임회사 — 엔진·코어 시스템 개발

<a id="game-engine-core"></a>

메모리·동시성·플랫폼·resource lifetime을 게임 루프와 연결해 엔진 하위 시스템을 다룬다.

**권장 선형 경로**

1. **엔진·코어** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) → [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) → [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- **권장 인접 지식:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **후속 심화:** [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems)

**트랙 종료 능력**

- 엔진 하위 시스템의 상태·수명·thread 경계를 설명한다
- 플랫폼 또는 resource 관리 기능을 구현한다
- 성능·메모리·동시성 문제를 측정 근거로 좁힌다

### 게임회사 — 렌더링·그래픽스 개발

<a id="game-rendering"></a>

게임 엔진 맥락과 GPU 렌더링 파이프라인을 연결해 화면 품질과 frame budget을 다룬다.

**권장 선형 경로**

1. **렌더링·그래픽스** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) → [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development) → [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development), [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics)
- **권장 인접 지식:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- **후속 심화:** [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation)

**트랙 종료 능력**

- 게임 장면과 렌더링 pipeline의 입력·출력을 연결한다
- shader·resource·synchronization 변경을 구현한다
- 화질과 frame-time trade-off를 측정한다

### 게임회사 — Java/Spring 게임 서버 개발

<a id="game-server"></a>

Java와 Spring 기반에서 권위 상태·세션·매치·실시간 통신·영속화·부분 실패를 운영 가능한 게임 서버로 연결한다.

**권장 선형 경로**

1. **Java/Spring 게임 서버** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) → [`java`](https://github.com/seungwoo7050/guides/tree/java) → [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot) → [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) → [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development) → [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) → [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`java`](https://github.com/seungwoo7050/guides/tree/java), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)
- **권장 인접 지식:** [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems)
- **후속 심화:** [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**트랙 종료 능력**

- 클라이언트 요청과 권위 서버 상태의 경계를 설계한다
- 세션·매치·영속 상태를 실패 뒤에도 수렴시킨다
- 배포·관측·복구가 가능한 서버 변경을 완성한다

### 게임회사 — 개발 도구·빌드·플랫폼

<a id="game-tools-platform"></a>

asset·build·test·배포 workflow를 자동화하고 여러 개발자가 반복 사용하는 내부 경로를 만든다.

**권장 선형 경로**

1. **도구·빌드·플랫폼** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`python`](https://github.com/seungwoo7050/guides/tree/python) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems) → [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development) → [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) → [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`python`](https://github.com/seungwoo7050/guides/tree/python), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- **권장 인접 지식:** [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)
- **후속 심화:** [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)

**트랙 종료 능력**

- asset·build·test pipeline의 실패 경계를 복원한다
- 반복 가능한 개발 도구와 CI workflow를 만든다
- self-service 배포·관측 경로를 운영한다

### 게임회사 — 데이터·머신러닝 개발

<a id="game-data-ml"></a>

플레이 이벤트·운영 데이터·모델 평가를 신뢰 가능한 pipeline과 게임 도메인 의사결정에 연결한다.

**권장 선형 경로**

1. **게임 데이터·ML** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`python`](https://github.com/seungwoo7050/guides/tree/python) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development) → [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) → [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering) → [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`python`](https://github.com/seungwoo7050/guides/tree/python), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)
- **권장 인접 지식:** [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- **후속 심화:** [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

**트랙 종료 능력**

- 플레이 이벤트와 분석 지표의 의미 계약을 정의한다
- 재처리 가능한 pipeline과 품질 검사를 운영한다
- 게임 문제에 대한 baseline·모델·평가 결과를 전달한다

### 게임회사 — 보안·안티치트 개발

<a id="game-security-anticheat"></a>

클라이언트·운영체제·네트워크·서버 신뢰 경계를 분석하고 조작 탐지와 안전한 대응을 설계한다.

**권장 선형 경로**

1. **보안·안티치트** — [`git`](https://github.com/seungwoo7050/guides/tree/git) → [`c`](https://github.com/seungwoo7050/guides/tree/c) → [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) → [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) → [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development) → [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) → [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) → [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems) → [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) → [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)

- **공통:** [`git`](https://github.com/seungwoo7050/guides/tree/git)
- **핵심 브랜치:** [`c`](https://github.com/seungwoo7050/guides/tree/c), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **택일 필수:** 없음
- **공통·핵심 브랜치와 직접 의존성 순서:** [`git`](https://github.com/seungwoo7050/guides/tree/git), [`c`](https://github.com/seungwoo7050/guides/tree/c), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)
- **권장 인접 지식:** [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- **후속 심화:** [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)

**트랙 종료 능력**

- 클라이언트·서버 신뢰 가정과 공격 경로를 문서화한다
- 조작을 재현하고 패치·탐지·회귀 검사를 연결한다
- 오탐·우회·운영 비용을 포함해 대응을 평가한다
