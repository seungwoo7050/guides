# 명령 빠른 참조

명령을 복사하기 전에 현재 디렉터리, Compose 프로젝트, 삭제 대상 볼륨을 확인합니다.

## HTTP와 TLS

```sh
curl -i http://127.0.0.1:8080/
curl -fsS http://127.0.0.1:8080/healthz >/dev/null
curl -vk https://127.0.0.1:18443/
curl --cacert development.crt https://localhost:18443/
```

```sh
openssl s_client -connect 127.0.0.1:18443 -servername localhost </dev/null
openssl x509 -in development.crt -noout -subject -issuer -dates -ext subjectAltName
```

## 호스트 프로세스와 포트

```sh
ps -ef
ps -o pid,ppid,user,stat,command -p PID
ss -ltnp
ss -lxnp
lsof -nP -iTCP:8080 -sTCP:LISTEN
kill -TERM PID
```

## 이미지

```sh
docker image ls
docker build -t name:tag .
docker build --pull -t name:tag .
docker image inspect name:tag
docker image history name:tag
```

## 컨테이너

```sh
docker ps
docker ps -a
docker logs CONTAINER
docker logs -f --tail=100 CONTAINER
docker inspect CONTAINER
docker exec CONTAINER ps -ef
docker exec -it CONTAINER sh
docker stop CONTAINER
docker rm CONTAINER
```

## Compose

```sh
docker compose config --quiet
docker compose config
docker compose build --pull
docker compose up -d
docker compose ps -a
docker compose logs --timestamps
docker compose logs -f app
docker compose exec app sh
docker compose restart app
docker compose down
docker compose down -v
```

## Docker 네트워크

```sh
docker network ls
docker network inspect NETWORK
docker compose exec gateway getent hosts app
docker compose exec app getent hosts db
```

## Docker 볼륨

```sh
docker volume ls
docker volume inspect VOLUME
docker inspect CONTAINER --format '{{json .Mounts}}'
```

볼륨을 지우기 전에 실제 연결 컨테이너와 프로젝트를 확인합니다.

## Nginx

```sh
docker compose exec gateway nginx -t
docker compose exec gateway nginx -T
docker compose logs gateway
```

## PHP-FPM

```sh
docker compose exec app ps -ef
```

```sh
docker compose exec app sh -c '
  REQUEST_METHOD=GET \
  SCRIPT_NAME=/ping \
  SCRIPT_FILENAME=/ping \
  cgi-fcgi -bind -connect 127.0.0.1:9000
'
```

## MariaDB

```sh
docker compose exec db mariadb-admin \
  --protocol=socket \
  --socket=/run/mysqld/mysqld.sock \
  ping --silent
```

```sh
docker compose exec db mariadb -uroot -p
docker compose exec -T db mariadb appdb < file.sql
docker compose exec -T db mariadb-dump appdb > backup.sql
```

```sql
SHOW DATABASES;
SHOW TABLES;
SHOW VARIABLES LIKE 'max_connections';
SHOW STATUS LIKE 'Threads_connected';
EXPLAIN SELECT * FROM notes WHERE id = 1;
```

## 상태 검사 결과

```sh
docker compose ps
docker inspect CONTAINER --format '{{json .State.Health}}'
docker inspect CONTAINER --format '{{.State.Status}} {{.State.ExitCode}} {{.RestartCount}}'
```

## 정적 검증

저장소 루트에서:

```sh
python3 scripts/static-verify.py
```

전체 완성 코드 실행:

```sh
./scripts/verify-all.sh
```
