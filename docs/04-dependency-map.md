# 브랜치 의존성 지도

> 이 문서는 `catalog/branches.json`에서 생성된다. 직접 수정하지 않는다.

전체 graph의 화살표 `A → B`는 B의 핵심 학습이 A를 직접 전제로 한다는 뜻이다. 권장·연결 관계는 표에서 별도로 확인한다.

## 직접 필수 의존성

| 브랜치 | 직접 필수 의존성 | 권장 기반 |
|---|---|---|
| [`git`](https://github.com/seungwoo7050/guides/tree/git) | 없음 | 없음 |
| [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) | 없음 | [`python`](https://github.com/seungwoo7050/guides/tree/python), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) |
| [`c`](https://github.com/seungwoo7050/guides/tree/c) | 없음 | [`git`](https://github.com/seungwoo7050/guides/tree/git) |
| [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp) | 없음 | [`c`](https://github.com/seungwoo7050/guides/tree/c), [`git`](https://github.com/seungwoo7050/guides/tree/git) |
| [`java`](https://github.com/seungwoo7050/guides/tree/java) | 없음 | [`git`](https://github.com/seungwoo7050/guides/tree/git) |
| [`python`](https://github.com/seungwoo7050/guides/tree/python) | 없음 | [`git`](https://github.com/seungwoo7050/guides/tree/git) |
| [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) | 없음 | [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`c`](https://github.com/seungwoo7050/guides/tree/c), [`python`](https://github.com/seungwoo7050/guides/tree/python) |
| [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) | 없음 | [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) |
| [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems) | 없음 | [`c`](https://github.com/seungwoo7050/guides/tree/c), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) |
| [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) | 없음 | [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) |
| [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) | 없음 | [`git`](https://github.com/seungwoo7050/guides/tree/git) |
| [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs) | [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) | [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) |
| [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot) | [`java`](https://github.com/seungwoo7050/guides/tree/java), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) | [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) |
| [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) | 없음 | [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) |
| [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services) | [`java`](https://github.com/seungwoo7050/guides/tree/java), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) | [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems), [`backend-spring-boot`](https://github.com/seungwoo7050/guides/tree/backend-spring-boot) |
| [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) | 없음 | [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) |
| [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) | [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) | [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra), [`python`](https://github.com/seungwoo7050/guides/tree/python), [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) |
| [`mobile-app`](https://github.com/seungwoo7050/guides/tree/mobile-app) | [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) | [`web-front-react-nextjs`](https://github.com/seungwoo7050/guides/tree/web-front-react-nextjs), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) |
| [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning) | [`python`](https://github.com/seungwoo7050/guides/tree/python) | [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms) |
| [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems) | [`python`](https://github.com/seungwoo7050/guides/tree/python), [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) | [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning) |
| [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems) | [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) | [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services) |
| [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering) | [`python`](https://github.com/seungwoo7050/guides/tree/python), [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems) | [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems) |
| [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering) | [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) | [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks), [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering) |
| [`language-implementation`](https://github.com/seungwoo7050/guides/tree/language-implementation) | [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) | [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) |
| [`embedded-systems`](https://github.com/seungwoo7050/guides/tree/embedded-systems) | [`c`](https://github.com/seungwoo7050/guides/tree/c), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) | [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) |
| [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics) | [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) | [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) |

## 전체 graph

```mermaid
flowchart LR
  classDef foundation fill:#eef,stroke:#445;
  classDef language fill:#efe,stroke:#454;
  classDef entry fill:#ffe,stroke:#665;
  classDef specialization fill:#fee,stroke:#655;
  git["git"]
  algorithms["algorithms"]
  c["c"]
  cpp["cpp"]
  java["java"]
  python["python"]
  computer_architecture["computer-architecture"]
  operating_systems["operating-systems"]
  unix_systems["unix-systems"]
  computer_networks["computer-networks"]
  web_app["web-app"]
  web_front_react_nextjs["web-front-react-nextjs"]
  backend_spring_boot["backend-spring-boot"]
  database_systems["database-systems"]
  distributed_services["distributed-services"]
  web_infra["web-infra"]
  cybersecurity["cybersecurity"]
  mobile_app["mobile-app"]
  machine_learning["machine-learning"]
  agentic_systems["agentic-systems"]
  distributed_systems["distributed-systems"]
  data_engineering["data-engineering"]
  platform_engineering["platform-engineering"]
  language_implementation["language-implementation"]
  embedded_systems["embedded-systems"]
  computer_graphics["computer-graphics"]
  web_app --> web_front_react_nextjs
  java --> backend_spring_boot
  web_app --> backend_spring_boot
  java --> distributed_services
  web_app --> distributed_services
  unix_systems --> cybersecurity
  computer_networks --> cybersecurity
  web_app --> mobile_app
  python --> machine_learning
  python --> agentic_systems
  web_app --> agentic_systems
  operating_systems --> distributed_systems
  computer_networks --> distributed_systems
  database_systems --> distributed_systems
  python --> data_engineering
  database_systems --> data_engineering
  web_infra --> platform_engineering
  cpp --> language_implementation
  algorithms --> language_implementation
  computer_architecture --> language_implementation
  c --> embedded_systems
  computer_architecture --> embedded_systems
  operating_systems --> embedded_systems
  cpp --> computer_graphics
  algorithms --> computer_graphics
  computer_architecture --> computer_graphics
  class git foundation;
  class algorithms foundation;
  class c language;
  class cpp language;
  class java language;
  class python language;
  class computer_architecture foundation;
  class operating_systems foundation;
  class unix_systems foundation;
  class computer_networks foundation;
  class web_app entry;
  class web_front_react_nextjs specialization;
  class backend_spring_boot specialization;
  class database_systems specialization;
  class distributed_services specialization;
  class web_infra entry;
  class cybersecurity entry;
  class mobile_app entry;
  class machine_learning entry;
  class agentic_systems entry;
  class distributed_systems specialization;
  class data_engineering specialization;
  class platform_engineering specialization;
  class language_implementation specialization;
  class embedded_systems specialization;
  class computer_graphics specialization;
```

## 분야별 흐름

아래 graph는 카탈로그의 관계에서 생성된다. 실선 `A --> B`는 `requires`, 점선 `A -.-> B`는 `recommends`다. `connects`와 `continues_to`는 순서를 뜻하지 않으므로 표시하지 않는다.

### 웹·데이터·분산·플랫폼

```mermaid
flowchart LR
  web_app["web-app"]
  web_front_react_nextjs["web-front-react-nextjs"]
  java["java"]
  backend_spring_boot["backend-spring-boot"]
  database_systems["database-systems"]
  distributed_services["distributed-services"]
  operating_systems["operating-systems"]
  computer_networks["computer-networks"]
  distributed_systems["distributed-systems"]
  python["python"]
  data_engineering["data-engineering"]
  unix_systems["unix-systems"]
  web_infra["web-infra"]
  platform_engineering["platform-engineering"]
  web_app --> web_front_react_nextjs
  computer_networks -.-> web_front_react_nextjs
  java --> backend_spring_boot
  web_app --> backend_spring_boot
  database_systems -.-> backend_spring_boot
  web_app -.-> database_systems
  operating_systems -.-> database_systems
  java --> distributed_services
  web_app --> distributed_services
  database_systems -.-> distributed_services
  backend_spring_boot -.-> distributed_services
  python -.-> operating_systems
  unix_systems -.-> computer_networks
  operating_systems -.-> computer_networks
  operating_systems --> distributed_systems
  computer_networks --> distributed_systems
  database_systems --> distributed_systems
  distributed_services -.-> distributed_systems
  python --> data_engineering
  database_systems --> data_engineering
  distributed_services -.-> data_engineering
  distributed_systems -.-> data_engineering
  operating_systems -.-> unix_systems
  unix_systems -.-> web_infra
  computer_networks -.-> web_infra
  web_app -.-> web_infra
  web_infra --> platform_engineering
  distributed_services -.-> platform_engineering
  computer_networks -.-> platform_engineering
  data_engineering -.-> platform_engineering
```

### AI·모바일·보안

```mermaid
flowchart LR
  python["python"]
  machine_learning["machine-learning"]
  agentic_systems["agentic-systems"]
  web_app["web-app"]
  web_front_react_nextjs["web-front-react-nextjs"]
  mobile_app["mobile-app"]
  unix_systems["unix-systems"]
  computer_networks["computer-networks"]
  cybersecurity["cybersecurity"]
  python --> machine_learning
  python --> agentic_systems
  web_app --> agentic_systems
  cybersecurity -.-> agentic_systems
  machine_learning -.-> agentic_systems
  web_app --> web_front_react_nextjs
  computer_networks -.-> web_front_react_nextjs
  web_app --> mobile_app
  web_front_react_nextjs -.-> mobile_app
  computer_networks -.-> mobile_app
  cybersecurity -.-> mobile_app
  unix_systems -.-> computer_networks
  unix_systems --> cybersecurity
  computer_networks --> cybersecurity
  web_app -.-> cybersecurity
  python -.-> cybersecurity
```

### 시스템·도구·그래픽스·임베디드

```mermaid
flowchart LR
  c["c"]
  cpp["cpp"]
  python["python"]
  algorithms["algorithms"]
  computer_architecture["computer-architecture"]
  operating_systems["operating-systems"]
  embedded_systems["embedded-systems"]
  language_implementation["language-implementation"]
  computer_graphics["computer-graphics"]
  c -.-> cpp
  python -.-> algorithms
  cpp -.-> algorithms
  algorithms -.-> computer_architecture
  c -.-> computer_architecture
  python -.-> computer_architecture
  algorithms -.-> operating_systems
  python -.-> operating_systems
  c -.-> operating_systems
  computer_architecture -.-> operating_systems
  c --> embedded_systems
  computer_architecture --> embedded_systems
  operating_systems --> embedded_systems
  cpp --> language_implementation
  algorithms --> language_implementation
  computer_architecture --> language_implementation
  operating_systems -.-> language_implementation
  cpp --> computer_graphics
  algorithms --> computer_graphics
  computer_architecture --> computer_graphics
  operating_systems -.-> computer_graphics
```

## 해석 규칙

- 필수 의존성은 브랜치 전체를 무조건 다시 공부하라는 뜻이 아니다. roadmap과 종료 검사를 이용해 이미 가진 능력을 확인한다.
- 권장 관계는 프로젝트 성격에 따라 순서가 달라질 수 있다.
- 업무 트랙의 핵심 목록은 직접 의존성을 생략할 수 있으므로 `docs/03-career-tracks.md`의 “공통·핵심 브랜치와 직접 의존성 순서”를 함께 본다.
- graph에 없더라도 `connects` 관계는 실제 협업에서 중요하다. 상세 내용은 `docs/01-branch-catalog.md`를 본다.
