# 멱등한 애플리케이션 초기화

## 재시작에도 유지할 조건

애플리케이션 컨테이너가 시작될 때 데이터베이스 스키마와 초기 데이터를 준비하되, 재시작하거나 재생성해도 같은 데이터가 중복되지 않게 만듭니다.

## 제공된 구성과 맡을 부분

`workspace/app/docker-entrypoint.sh`와 `workspace/app/bin/bootstrap.php`는 의도적으로 미완성인 시작 상태에서 복사됩니다. 나머지 데이터베이스, Nginx, PHP-FPM 구성은 제공됩니다. 상태를 먼저 조회하고 필요한 변경만 적용하여 초기화 과정을 여러 번 실행해도 같은 결과가 나오는지 확인합니다.

## 구현 조건

1. 필수 환경변수와 비밀값 파일을 시작 직후 검증합니다.
2. 데이터베이스 연결은 최대 30초까지만 재시도합니다.
3. 테이블 생성은 `IF NOT EXISTS`를 사용합니다.
4. `seed_v1` 마커를 처음 넣은 실행에서만 `seed note`를 추가합니다.
5. 초기화가 끝난 뒤 `exec "$@"`로 PHP-FPM을 실행합니다.
6. 시작 스크립트는 `/run/secrets/...`에 주입된 비밀값을 읽고, PHP-FPM 작업자는 `/run`의 권한 제한 복사본만 읽습니다.

## 실행

저장소 루트에서 작업공간을 만들고 그 사본을 실행합니다.

```sh
python3 scripts/new-workspace.py exercises/06-app-bootstrap
cd exercises/06-app-bootstrap/workspace
./prepare-secrets.sh
docker compose up --build
```

시작 상태에서는 실패하고 구현 뒤에는 다음 검증이 통과해야 합니다.

```sh
../verify.sh workspace
```

관찰과 자기 설명을 끝낸 뒤에만 기준 구현을 검증하고 비교합니다.

```sh
../verify.sh reference
```

## 관찰할 것

- 첫 실행 로그에는 `초기 애플리케이션 데이터를 추가했습니다.`가 한 번 나타납니다.
- 앱을 재시작하면 `초기 애플리케이션 데이터가 이미 있어 건너뜁니다.`가 나타납니다.
- `POST /api/notes`로 추가한 데이터는 앱 컨테이너를 재생성해도 남습니다.
- 데이터베이스 볼륨을 삭제하면 상태가 새로 초기화됩니다.

## 권장 구현 순서

아래 번호는 실제 Git 이력이 아니라 `reference/` 전체의 학습용 construction order입니다. 파일마다 번호를 다시 시작하지 않습니다. DB와 gateway foundation은 앞 실습의 완료 구성을 재사용합니다.

| 번호 | 구현 경계 |
|---:|---|
| [Implementation 0] | app의 FastCGI 도구와 `pdo_mysql` dependency 설치 |
| 1 | injected secret·tmpfs·DB health dependency |
| 2 | bootstrap input 경계 |
| 3 | bounded PDO connection retry |
| 4 | idempotent schema |
| 5 | transaction 안의 `seed_v1` marker와 seed |
| 6 | entrypoint 환경·secret preflight와 runtime 권한 |
| 7 | PHP bootstrap CLI 뒤 최종 FPM `exec` |
| 8 | request-time PDO ownership |
| 9 | route·input validation·prepared write |
| 10 | 완성된 bootstrap·entrypoint·public route의 image assembly |

7번의 `php /opt/app/bootstrap.php`는 project bootstrap이 아니라 schema와 seed를 준비하는 중간 CLI입니다.

## 완료 기준

- [ ] `./verify.sh workspace`가 통과하고 재시작·재생성 뒤에도 `seed_v1`과 초기 note가 정확히 한 번만 존재한다.
- [ ] 사용자가 추가한 note가 app 재생성 뒤 유지되고, volume 삭제 뒤에는 새 상태로 초기화되는 경계를 확인한다.
- [ ] 누락 secret과 준비되지 않은 DB에서 제한 시간 안에 명확히 실패하며 최종 PHP-FPM이 `exec`로 실행되는지 확인한다.

## 자기 설명

1. `CREATE TABLE IF NOT EXISTS`만으로 seed 데이터의 멱등성까지 보장할 수 없는 이유는 무엇인가?
2. 초기화 완료 marker와 실제 업무 상태가 불일치할 때 어떤 순서로 복구해야 하는가?
3. 재시도 횟수나 시간이 무제한이면 배포와 상태 검사에서 어떤 실패가 숨겨지는가?
