# 웹 애플리케이션 개발

HTML·CSS·JavaScript에서 시작해 React·Next.js, Fastify, PostgreSQL, 인증, WebSocket과 테스트까지 연결하는 웹 애플리케이션 개발 가이드입니다.

이 저장소는 개념 문서와 직접 실행할 수 있는 작은 프로젝트를 함께 구성합니다. 각 주제는 필요한 실행 모델과 경계를 먼저 설명한 뒤, 해당 개념을 실제 코드로 확인하는 방식으로 확장합니다.

## 현재 구조

```text
README.md
docs/
exercises/
```

문서의 전체 순서와 각 영역의 범위는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에서 관리합니다.

## 학습 범위

초기 로드맵은 다음 흐름을 기준으로 합니다.

```text
웹과 브라우저 기반
→ JavaScript·TypeScript·Node.js
→ React·Next.js
→ HTTP API
→ PostgreSQL과 transaction
→ session과 authorization
→ WebSocket과 실시간 상태
→ 테스트와 통합 프로젝트
```

각 프로젝트는 최종적으로 `exercises/<project>/` 하나만 복사해도 독립적으로 설치·실행·검증할 수 있는 형태를 목표로 합니다.
