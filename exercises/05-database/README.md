# MariaDB 최초 초기화, 영속화와 인덱스

공식 완성 이미지를 그대로 실행하지 않고 Debian 기반의 작은 MariaDB 이미지를 만들어 데이터 디렉터리 생명주기를 관찰합니다.

## 보존할 데이터

- 빈 볼륨에서만 `mariadb-install-db`를 실행합니다.
- 초기 설정 중 TCP를 끄고 Unix 소켓으로 SQL을 적용합니다.
- 애플리케이션 전용 데이터베이스와 사용자를 만듭니다.
- 컨테이너 재생성 뒤 데이터가 유지됨을 확인합니다.
- 논리 백업을 삭제된 테이블에 복원합니다.
- 인덱스 전후 `EXPLAIN`이 선택한 키를 비교합니다.

## 실행

```sh
./verify.sh reference
```

시작 코드의 TODO를 채운 뒤:

```sh
./verify.sh skeleton
```

검증은 실제 비밀값 파일을 `.example`에서 생성합니다. 생성된 `secrets/*.txt`와 `backups/*.sql`은 Git 대상이 아닙니다.

## 초기화 스크립트 작성

- `db/docker-entrypoint.sh`에서 비밀값 읽기와 필수값 검증을 구현합니다.
- `/var/lib/mysql/mysql`이 없을 때만 시스템 테이블을 초기화합니다.
- 임시 서버를 `--skip-networking`으로 실행합니다.
- 준비 대기에 시간 제한을 둡니다.
- 데이터베이스, 애플리케이션 사용자와 권한을 만듭니다.
- 임시 서버를 정상 종료하고 마지막에 `exec "$@"` 합니다.
- `50-server.cnf`에서 컨테이너 네트워크, 데이터 디렉터리, `utf8mb4` 기본값을 설정합니다.

## 수동 명령

```sh
cd reference
./prepare-secrets.sh
docker compose up -d --build
docker compose logs -f db
./backup.sh
docker compose down
docker compose up -d
docker compose down -v
```

## 완료 기준

- [ ] `./verify.sh skeleton`이 통과하고 같은 volume으로 재시작할 때 시스템 테이블과 초기 사용자가 중복 생성되지 않는다.
- [ ] 컨테이너 재생성 뒤 데이터를 읽고, 논리 backup으로 삭제한 테이블을 복원하며, `EXPLAIN`의 선택 인덱스 변화를 확인한다.
- [ ] 실제 secret과 backup 산출물이 Git 대상이 아니고 초기화 중 TCP가 열리지 않았다는 증거를 남긴다.

## 자기 설명

1. 데이터 디렉터리의 어떤 상태를 근거로 최초 초기화와 일반 시작을 구분하는가?
2. 초기 SQL 적용 중 `--skip-networking`을 쓰는 것이 어떤 노출 시간을 줄이는가?
3. volume 지속성과 논리 backup은 서로 어떤 장애를 복구하며 왜 둘 다 필요한가?
