# Notes Stack

Nginx TLS gateway, PHP-FPM application, MariaDB, persistent volume, file-based secret injection을 하나의 Compose application으로 제공한다. Database와 application은 host에 port를 공개하지 않으며, 사용자는 gateway의 HTTPS endpoint만 사용한다.

## Features

- MariaDB data directory의 first-run initialization과 일반 restart 분리
- 초기 provisioning 동안 `--skip-networking`을 사용한 임시 database server
- Docker Compose file secret과 runtime permission 축소
- bounded database connection retry
- transaction 안에서 처리하는 idempotent schema seed
- `GET /api/notes`, `POST /api/notes`, `GET /health`
- Nginx static file delivery와 FastCGI routing
- named volume을 통한 database persistence
- transaction-consistent logical backup과 explicit restore
- index 적용 전후 `EXPLAIN`을 재현하는 deterministic dataset
- DNS, authentication, secret, upstream, health check, volume-loss fault injection

## Architecture

`db`는 `/var/lib/mysql` named volume을 단독 소유한다. 빈 volume에서만 system table과 application account를 만들고, 완료 뒤 final `mariadbd`로 process를 교체한다. `app`은 injected secret을 그대로 worker에 노출하지 않고 tmpfs의 `root:www-data:0440` 파일로 복사한다. Schema와 seed가 준비된 경우에만 PHP-FPM을 시작한다. `gateway`만 host port를 공개하며 static request는 직접 처리하고 dynamic request는 FastCGI로 전달한다.

## Run

```sh
./prepare-secrets.sh
docker compose up -d --build
curl -k https://127.0.0.1:19443/health
curl -k https://127.0.0.1:19443/api/notes
curl -k -H 'Content-Type: application/json' \
  -d '{"body":"new note"}' \
  https://127.0.0.1:19443/api/notes
```

포함된 certificate는 local execution 전용 self-signed certificate다. 실제 public deployment에서는 ACME 등 외부 신뢰 chain을 사용해야 하며 `curl -k`를 검증 절차로 사용하면 안 된다.

## Backup and restore

```sh
./backup.sh
./restore.sh backups/appdb.sql
```

Backup은 `mariadb-dump --single-transaction`으로 생성한다. Restore는 지정한 SQL file만 현재 `appdb`에 적용하므로, destructive operation 전 별도의 restore drill이 필요하다.

## Verification

Docker 없이 source와 configuration syntax를 검사한다.

```sh
./tests/static.sh
```

Docker가 있는 환경에서는 full lifecycle과 fault scenarios를 실행한다.

```sh
./tests/integration.sh
./tests/fault-injection.sh all
```

## Design decisions

Schema creation만으로 seed idempotency를 보장할 수 없으므로 `app_meta.seed_v1` 획득과 initial note insert를 같은 transaction에 둔다. Database first-run provisioning은 외부 network listener를 열기 전에 Unix socket으로 완료한다. Volume 삭제는 stateless container recreation과 다른 destructive boundary이므로 fault suite에서 별도 project name과 cleanup 범위를 사용한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Database runtime contract | `db/50-server.cnf` |
| 2 | Secret input and identifier validation | `db/docker-entrypoint.sh` |
| 2-1 | First-run data directory initialization | `db/docker-entrypoint.sh` |
| 2-2 | Isolated bootstrap server readiness | `db/docker-entrypoint.sh` |
| 2-3 | Database provisioning and final process handoff | `db/docker-entrypoint.sh` |
| 3 | Database image assembly | `db/Dockerfile` |
| 4 | Application bootstrap input contract | `app/bin/bootstrap.php` |
| 4-1 | Bounded PDO connection retry | `app/bin/bootstrap.php` |
| 4-2 | Idempotent application schema | `app/bin/bootstrap.php` |
| 4-3 | Transactional seed marker | `app/bin/bootstrap.php` |
| 5 | Runtime secret ownership | `app/docker-entrypoint.sh` |
| 5-1 | Bootstrap-to-FPM process handoff | `app/docker-entrypoint.sh` |
| 6 | Request-time database ownership | `app/public/index.php` |
| 6-1 | Notes API routing and validation | `app/public/index.php` |
| 7 | PHP-FPM image assembly | `app/Dockerfile` |
| 8 | Gateway TLS material lifecycle | `gateway/docker-entrypoint.sh` |
| 8-1 | Static and FastCGI routing | `gateway/default.conf.template` |
| 8-2 | Gateway image assembly | `gateway/Dockerfile` |
| 9 | Stack composition and resource ownership | `compose.yaml` |
| 9-1 | Health-gated service startup | `compose.yaml` |
| 9-2 | Internal network and persistent volume | `compose.yaml` |
| 10 | Transaction-consistent logical backup | `backup.sh` |
| 10-1 | Explicit restore target | `restore.sh` |
| 11 | Deterministic index observation dataset | `sql/index-demo.sql` |
| 12 | End-to-end lifecycle verification | `tests/integration.sh` |
| 12-1 | Fault-injection verification | `tests/fault-injection.sh` |
| 12-2 | Static configuration verification | `tests/static.sh` |

## Scope and limitations

이 구성은 single-host Compose deployment다. Gateway certificate는 local development용이며 automatic public renewal을 제공하지 않는다. Backup file의 off-host 전송, encryption, retention, restore scheduling은 이 프로젝트의 범위 밖이다. Database migration system도 포함하지 않으며 현재 bootstrap은 additive initial schema만 관리한다.
