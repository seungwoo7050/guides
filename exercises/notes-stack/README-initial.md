# Notes Stack

Nginx gateway, PHP-FPM application과 MariaDB를 하나의 service stack으로 구성하는 project입니다. 첫 구현 단계에서는 전체 stack의 persistent state를 소유하는 database runtime과 first-run initialization 경계를 먼저 확정합니다.

## 현재 구성

```text
notes-stack/
├── README.md
├── .gitignore
├── db/
│   ├── 50-server.cnf
│   ├── Dockerfile
│   └── docker-entrypoint.sh
├── prepare-secrets.sh
└── secrets/
    ├── db_password.txt.example
    └── db_root_password.txt.example
```

## Database boundary

현재 단계의 database image는 다음 책임을 가집니다.

- `/var/lib/mysql`을 persistent datadir로 사용
- empty datadir에서만 system table 초기화
- bootstrap 동안 network listener를 열지 않고 Unix socket 사용
- application database와 user provisioning
- bootstrap server 종료 뒤 foreground `mariadbd`로 process handoff
- password를 file-based secret input으로 수신

## 현재 Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Database runtime contract | `db/50-server.cnf` |
| 2 | Secret input and identifier validation | `db/docker-entrypoint.sh` |
| 2-1 | First-run data directory initialization | `db/docker-entrypoint.sh` |
| 2-2 | Isolated bootstrap server readiness | `db/docker-entrypoint.sh` |
| 2-3 | Database provisioning and final process handoff | `db/docker-entrypoint.sh` |
| 3 | Database image assembly | `db/Dockerfile` |

Application bootstrap, request routing, HTTPS gateway, Compose composition, backup/restore와 end-to-end verification은 이후 commit에서 같은 project 안에 통합합니다.
