# 웹 인프라 가이드

웹 요청이 서버 process에 도달하고, container와 network를 지나 application과 database 상태로 연결되는 과정을 단계적으로 정리하는 저장소입니다.

이 가이드의 목표는 특정 command를 암기하는 것이 아니라 다음 경계를 구분하는 것입니다.

- DNS, TCP, TLS와 HTTP
- process와 listening port
- Docker image와 container
- Compose service, network와 volume
- gateway와 application runtime
- database 초기화와 persistent state
- 배포, 관측, backup과 recovery

## 저장소 구조

```text
.
├── .gitignore
├── README.md
├── docs/
└── exercises/
```

`docs/`는 개념과 운영 원칙을 설명하고, `exercises/`는 해당 개념을 실제 동작으로 확인할 수 있는 완성형 standalone project를 담습니다.

## 진행 방향

초기 구간에서는 요청 처리, Docker와 Compose를 사용해 local service의 process·network·storage 경계를 이해합니다. 이후 Nginx, PHP-FPM, MariaDB를 결합한 stack으로 확장하고, 마지막에는 public TLS, release artifact, deployment, secret, observability, backup과 recovery 같은 운영 경계를 다룹니다.

세부 순서는 `docs/00-roadmap.md`에서 관리합니다.
