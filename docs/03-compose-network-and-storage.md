# Compose, 네트워크와 저장소

한 컨테이너만으로 끝나는 애플리케이션은 드뭅니다. 웹 시스템은 요청을 받는 게이트웨이, 코드를 실행하는 애플리케이션, 상태를 저장하는 데이터베이스처럼 책임을 나누는 경우가 많습니다.

이 장에서는 먼저 `docker run`으로 두 컨테이너를 직접 연결합니다. 그다음 동일한 구성을 Compose 파일로 옮깁니다. Compose 문법부터 외우지 않고, 어떤 수동 작업을 선언으로 대체하는지 확인합니다.

## 1. 여러 서비스를 연결할 실습 시스템

`exercises/03-compose`의 관찰 대상은 다음 구조입니다.

```text
호스트 curl
    │ :18083
    ▼
  app ───── 이름 있는 볼륨 app-data
    ▲
    │ http://app:8080
  client
```

- 애플리케이션은 HTTP 요청을 받고 `/data/counter.txt`에 요청 횟수를 저장합니다.
- 클라이언트는 같은 Docker 네트워크에서 `app`이라는 이름으로 요청합니다.
- 애플리케이션 컨테이너를 삭제하고 다시 만들어도 요청 횟수는 볼륨에 남습니다.
- 호스트에는 애플리케이션 포트만 공개하고 클라이언트는 외부 포트를 갖지 않습니다.

## 2. 서비스 분리

프로세스를 컨테이너로 나누는 기준은 “패키지가 다르다” 하나가 아닙니다. 다음 질문을 함께 봅니다.

- 서로 독립적으로 시작·종료할 필요가 있는가?
- 장애와 자원 사용을 분리해야 하는가?
- 배포 주기와 확장 단위가 다른가?
- 상태 저장 방식이 다른가?
- 서로 다른 권한이나 네트워크 노출이 필요한가?

모든 프로세스를 무조건 한 컨테이너씩 나누는 것도 정답은 아닙니다. 강하게 결합된 보조 프로세스까지 분리하면 운영 복잡성만 늘 수 있습니다. 이 가이드에서는 게이트웨이, 애플리케이션, 데이터베이스처럼 책임과 프로토콜이 분명히 다른 단위를 분리합니다.

## 3. 수동으로 네트워크 만들기

먼저 사용자 정의 브리지 네트워크를 만듭니다.

```sh
docker network create app-net
```

app 컨테이너를 실행합니다.

```sh
docker run -d \
  --name app \
  --network app-net \
  -p 18083:8080 \
  app-image
```

같은 네트워크의 임시 클라이언트에서 요청합니다.

```sh
docker run --rm \
  --network app-net \
  curlimages/curl:8.10.1 \
  -fsS http://app:8080/healthz
```

클라이언트는 애플리케이션의 IP를 모릅니다. Docker의 내장 DNS가 `app` 이름을 현재 컨테이너 주소로 해석합니다.

실습이 끝나면 수동 리소스를 지웁니다.

```sh
docker rm -f app
docker network rm app-net
```

서비스가 늘어나면 이 명령들은 길어집니다. 네트워크, 볼륨, 환경변수, 시작 순서를 사람이 기억해야 합니다. Compose는 이 상태를 파일로 선언합니다.

## 4. 브리지 네트워크

Docker의 bridge 네트워크는 한 호스트 안에서 컨테이너 간 통신을 제공합니다.

```text
Docker 호스트
┌──────────────────────────────────────┐
│ 사용자 정의 브리지: app-net          │
│                                      │
│  client ───────────────▶ app:8080    │
│                          │           │
│ host:18083 ──────────────┘           │
└──────────────────────────────────────┘
```

사용자 정의 브리지에 연결된 컨테이너는 서비스 또는 컨테이너 이름으로 서로를 찾을 수 있습니다. 같은 네트워크에 연결되지 않은 컨테이너는 기본적으로 그 이름으로 직접 통신할 수 없습니다.

네트워크는 강한 보안 경계 전체를 대신하지 않습니다. 호스트의 Docker 권한, 커널, 방화벽, 애플리케이션 인증도 중요합니다. 그러나 불필요한 서비스가 서로 도달하지 못하게 네트워크를 나누는 것은 노출 범위를 줄입니다.

## 5. 서비스 이름과 IP 주소

컨테이너 IP를 설정 파일에 직접 넣지 않습니다.

```text
나쁜 설정: DB_HOST=172.19.0.4
좋은 설정: DB_HOST=db
```

컨테이너는 재생성되면 IP가 달라질 수 있습니다. 서비스 이름은 Compose 모델에 속하는 안정적인 식별자입니다.

DNS가 이름을 IP로 바꿔 주더라도 기존 TCP 연결은 자동으로 새 주소에 다시 연결되지 않습니다. 실행 중에 의존 서비스가 재시작될 수 있으므로 애플리케이션은 연결 실패와 재연결을 처리해야 합니다.

## 6. 내부 포트와 공개 포트

Compose의 `expose` 또는 이미지의 `EXPOSE`는 서비스가 사용하는 내부 포트를 설명합니다. `ports`는 호스트 포트를 게시합니다.

```yaml
services:
  app:
    ports:
      - "18083:8080"
```

의미:

```text
host 18083 → app container 8080
```

같은 네트워크의 클라이언트는 호스트 포트를 거치지 않습니다.

```text
http://app:8080
```

데이터베이스가 3306 포트에서 연결을 기다리더라도 호스트에 `3306:3306`을 게시할 필요는 없습니다. 애플리케이션이 같은 내부 네트워크에서 `db:3306`으로 연결하면 됩니다. 외부에서 직접 접근할 이유가 없는 포트는 게시하지 않습니다.

호스트 포트를 `127.0.0.1:18083:8080`처럼 loopback에만 묶을 수도 있습니다.

```yaml
ports:
  - "127.0.0.1:18083:8080"
```

이는 LAN의 다른 장치에서 접근할 필요가 없는 개발 서비스의 노출을 줄입니다.

## 7. 컨테이너 저장소 선택

컨테이너가 파일을 쓰는 위치는 세 종류로 나눌 수 있습니다.

### 7.1 쓰기 가능 계층

마운트하지 않은 컨테이너 내부 경로입니다. 컨테이너 삭제와 함께 사라집니다. 캐시나 임시 파일처럼 잃어도 되는 데이터에만 적합합니다.

### 7.2 이름 있는 볼륨

Docker가 관리하는 영속 저장소입니다.

```sh
docker volume create app-data
docker run -v app-data:/data app-image
```

볼륨의 수명은 특정 컨테이너와 독립적입니다. 컨테이너를 삭제해도 볼륨은 남습니다.

### 7.3 호스트 경로 마운트

호스트의 구체적인 경로를 컨테이너에 연결합니다.

```sh
docker run -v "$PWD/src:/app/src:ro" app-image
```

개발 중 소스 변경을 즉시 반영하거나 호스트 편집기가 파일을 직접 다뤄야 할 때 유용합니다. 대신 호스트 경로, UID/GID, 파일 공유 구현에 종속됩니다.

## 8. 이름 있는 볼륨의 동작

Compose에서 볼륨을 선언합니다.

```yaml
services:
  app:
    volumes:
      - app-data:/data

volumes:
  app-data:
```

`docker compose up`은 프로젝트 이름을 접두사로 실제 볼륨을 만듭니다.

```sh
docker volume ls
```

`docker compose down`은 기본적으로 컨테이너와 네트워크를 제거하지만 이름 있는 볼륨을 보존합니다.

```sh
docker compose down
```

볼륨까지 삭제하려면 명시합니다.

```sh
docker compose down -v
```

이 차이는 데이터베이스 운영에서 결정적입니다. 재배포와 데이터 초기화를 같은 명령으로 취급하면 안 됩니다.

### 빈 볼륨의 초기 내용

빈 볼륨을 이미지 안에 이미 파일이 있는 경로에 처음 마운트하면 Docker가 해당 내용을 볼륨에 복사할 수 있습니다. 이 동작은 초기 파일 배포에 유용하지만, 이미지 교체 후 기존 볼륨의 파일이 자동 갱신된다고 생각하면 안 됩니다. 기존 볼륨은 기존 상태를 유지합니다.

## 9. 읽기 전용 마운트

파일을 읽기만 해야 하는 서비스에는 `read_only` 또는 `:ro`를 사용합니다.

```yaml
volumes:
  - type: bind
    source: ./public
    target: /var/www/html
    read_only: true
```

Nginx가 정적 파일만 제공한다면 파일을 수정할 이유가 없습니다. 읽기 전용 마운트는 실수나 취약점이 파일을 변경할 수 있는 범위를 줄입니다.

읽기 전용 마운트만으로 컨테이너 전체가 읽기 전용이 되는 것은 아닙니다. 필요하면 서비스 수준의 `read_only: true`와 쓰기 가능한 tmpfs 경로를 별도로 설계합니다.

## 10. 설정, 비밀값, 데이터 분리

세 종류를 같은 방식으로 취급하지 않습니다.

| 종류 | 예 | 일반적인 전달 방식 | 수명 |
|---|---|---|---|
| 설정 | 포트, 로그 레벨, 도메인 | 환경변수, 설정 파일 | 배포와 함께 변경 |
| 비밀값 | DB 비밀번호, API 토큰, 개인키 | secret 파일, 외부 secret manager | 별도 회전 필요 |
| 데이터 | 데이터베이스 파일, 업로드 | 이름 있는 볼륨, 외부 저장소 | 컨테이너보다 오래 유지 |

비밀번호를 Dockerfile의 `ENV`, 소스 코드, Compose 파일에 직접 쓰지 않습니다. 학습용 비밀번호라도 실제 값 파일은 `.gitignore`하고 `.example` 파일 또는 생성 스크립트를 제공합니다.

## 11. Compose의 역할

Compose 파일은 명령의 순서를 기록한 셸 스크립트가 아니라 원하는 애플리케이션 상태를 선언합니다.

```yaml
services:
  app:
    build: ./app
    ports:
      - "127.0.0.1:18083:8080"
    volumes:
      - app-data:/data
    networks:
      - app-net

networks:
  app-net:

volumes:
  app-data:
```

`docker compose up`은 현재 상태와 선언을 비교해 필요한 리소스를 만들거나 컨테이너를 재생성합니다. 파일 내용이 바뀌지 않았다면 기존 컨테이너를 그대로 둘 수 있습니다.

## 12. Compose를 위한 최소 YAML

### 매핑

키와 값의 집합입니다.

```yaml
services:
  app:
    image: example
```

### 시퀀스

순서가 있는 목록입니다.

```yaml
ports:
  - "18083:8080"
  - "18084:8081"
```

### 들여쓰기

같은 수준의 키는 같은 열에 맞춥니다. 탭 대신 공백을 사용합니다. 보통 두 칸 들여쓰기를 사용합니다.

### 문자열 따옴표

포트 매핑, `yes`, `no`, 버전처럼 다른 타입으로 해석될 여지가 있는 값은 문자열 따옴표를 사용하는 편이 안전합니다.

```yaml
ports:
  - "18083:8080"
environment:
  FEATURE_MODE: "off"
```

YAML anchor, merge key, 사용자 태그는 이 가이드 범위에서 필요하지 않습니다.

## 13. Compose의 주요 섹션

### `services`

컨테이너로 실체화할 서비스를 정의합니다.

```yaml
services:
  app:
    build:
      context: ./app
    environment:
      APP_PORT: "8080"
```

### `networks`

서비스가 연결될 네트워크를 선언합니다.

```yaml
networks:
  app-net:
    driver: bridge
```

### `volumes`

Docker가 관리할 이름 있는 볼륨입니다.

```yaml
volumes:
  app-data:
```

### `secrets`

민감 값을 서비스에 파일로 노출합니다.

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt
```

## 14. 환경변수와 Compose 보간

Compose 파일은 실행 전에 호스트 환경 또는 `.env` 값을 사용해 문자열을 보간할 수 있습니다.

```yaml
ports:
  - "${APP_BIND_ADDRESS:-127.0.0.1}:${APP_PORT:-18083}:8080"
```

주요 형식:

| 형식 | 의미 |
|---|---|
| `${VAR}` | VAR 값, 없으면 빈 값이 될 수 있음 |
| `${VAR:-default}` | unset 또는 빈 값이면 default |
| `${VAR:?message}` | unset 또는 빈 값이면 Compose가 실패 |

필수 설정에는 `:?`를 사용해 컨테이너를 만들기 전에 실패시키는 편이 낫습니다.

### `.env`와 `environment`의 차이

`.env`는 Compose 파일 텍스트 보간에 사용됩니다. `environment`는 컨테이너 프로세스에 값을 전달합니다.

```yaml
services:
  app:
    environment:
      APP_MODE: "${APP_MODE:-development}"
```

여기서 호스트 또는 `.env`의 `APP_MODE`가 Compose에 의해 먼저 해석되고, 최종 값이 컨테이너 환경변수로 들어갑니다.

렌더된 결과는 다음으로 확인합니다.

```sh
docker compose config
```

비밀값이 있는 구성에서 `config` 출력을 로그에 그대로 남기지 않도록 주의합니다.

## 15. 파일 기반 비밀값

Compose의 비밀값은 서비스 안에 일반적으로 `/run/secrets/<name>` 파일로 마운트됩니다.

```yaml
services:
  app:
    secrets:
      - db_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

애플리케이션 시작 명령은 `DB_PASSWORD_FILE` 경로를 읽고 메모리상의 설정으로 사용합니다.

이 방식의 장점:

- 이미지 레이어에 값이 들어가지 않습니다.
- Compose 서비스 환경변수에 평문 값이 직접 나타나지 않습니다.
- 파일 권한으로 접근을 제한할 수 있습니다.

한계:

- 로컬 Compose에서 비밀값의 원본은 호스트 파일입니다.
- 그 파일을 누가 읽을 수 있는지는 호스트 권한 관리에 달려 있습니다.
- 중앙 비밀값 관리, 접근 감사, 자동 회전을 제공하지 않습니다.

단일 호스트 환경에서는 적절하지만 대규모 운영의 비밀값 관리 전체를 대신하지 않습니다.

## 16. 실행 중과 준비 완료

컨테이너가 `running`이라는 것은 PID 1 프로세스가 종료되지 않았다는 뜻입니다. 서비스가 요청을 처리할 준비가 됐다는 뜻은 아닙니다.

예를 들어 데이터베이스 프로세스는 실행됐지만 다음 작업 중일 수 있습니다.

- 데이터 파일 복구
- 시스템 테이블 업그레이드
- 초기 사용자 생성
- 네트워크 소켓 준비

`healthcheck`는 컨테이너 안에서 명령을 반복 실행하고 종료 코드로 상태를 판정합니다.

```yaml
healthcheck:
  test: ["CMD", "python", "/app/healthcheck.py"]
  interval: 5s
  timeout: 2s
  retries: 10
  start_period: 5s
```

상태는 대략 `starting`, `healthy`, `unhealthy`로 변합니다.

### `CMD`와 `CMD-SHELL`

```yaml
test: ["CMD", "curl", "-f", "http://127.0.0.1:8080/healthz"]
```

셸을 거치지 않고 프로그램을 직접 실행합니다.

```yaml
test: ["CMD-SHELL", "curl -fsS http://127.0.0.1:8080/healthz | grep -q ok"]
```

파이프나 `&&` 같은 셸 문법이 필요할 때 사용합니다. 이미지에 `/bin/sh`가 있어야 합니다.

상태 검사는 가볍고 읽기 전용이어야 합니다. 짧은 주기로 실제 데이터를 변경하거나 외부 인터넷 서비스까지 호출하면 부하와 오판이 생깁니다.

## 17. `depends_on`

짧은 형식은 서비스 생성·시작 순서를 표현하지만 준비 완료를 기다리지 않습니다.

```yaml
depends_on:
  - db
```

`healthcheck`와 `service_healthy`를 함께 사용하면 의존 서비스가 준비된 뒤 시작하도록 제어할 수 있습니다.

```yaml
depends_on:
  db:
    condition: service_healthy
```

그러나 다음을 보장하지 않습니다.

- 실행 중 데이터베이스가 종료됐을 때 애플리케이션이 자동으로 다시 연결함
- 외부 서비스의 준비 상태
- 비즈니스 기능 전체의 정상 동작

시작 순서와 실행 중 복구는 다른 문제입니다. 애플리케이션은 일시적인 연결 실패를 처리해야 합니다.

## 18. 재시작 정책

```yaml
restart: unless-stopped
```

주요 값:

- `no`: 자동 재시작하지 않음
- `on-failure`: 비영 종료일 때 재시작
- `always`: 종료 이유와 관계없이 재시작
- `unless-stopped`: 사용자가 명시적으로 중지한 상태는 존중

재시작 정책은 설정 오류를 해결하지 않습니다. 잘못된 비밀번호로 즉시 종료하는 컨테이너에 `always`를 주면 오류가 사라지는 것이 아니라 재시작을 반복합니다. 최초 오류 로그를 먼저 봅니다.

## 19. Compose 생명주기

### 설정 렌더링과 검증

```sh
docker compose config
docker compose config --quiet
```

### 빌드

```sh
docker compose build
docker compose build --pull
```

### 실행

```sh
docker compose up
docker compose up -d
```

### 상태와 로그

```sh
docker compose ps
docker compose logs
docker compose logs -f app
```

### 컨테이너 내부 명령

```sh
docker compose exec app ps -ef
```

### 종료와 제거

```sh
docker compose stop
docker compose down
docker compose down -v
```

`stop`은 컨테이너를 유지하고 프로세스만 멈춥니다. `down`은 Compose가 만든 컨테이너와 기본 네트워크를 제거합니다. `-v`는 이름 있는 볼륨까지 제거하므로 데이터 초기화 의도가 있을 때만 사용합니다.

## 20. 실습

실습 위치:

```sh
python3 scripts/new-workspace.py exercises/03-compose
cd exercises/03-compose
```

### 실습 1: 자신의 Compose 구성 실행

```sh
./verify.sh workspace
```

검증은 다음을 수행합니다.

1. 애플리케이션을 빌드하고 시작합니다.
2. 호스트 포트에서 상태 검사 경로를 확인합니다.
3. 클라이언트 컨테이너가 `http://app:8080`으로 요청합니다.
4. 요청 횟수를 증가시킵니다.
5. 컨테이너를 제거하되 볼륨은 남깁니다.
6. 다시 실행해 요청 횟수가 유지되는지 확인합니다.
7. 마지막에 검사용 볼륨을 제거합니다.

### 실습 2: 시작 코드의 네트워크 완성

`workspace/compose.yaml`에서 애플리케이션과 클라이언트를 같은 네트워크에 연결합니다. 서비스 이름을 IP로 바꾸지 않습니다.

### 실습 3: 볼륨 제거

`app-data:/data`를 잠시 제거하고 요청 횟수를 증가시킨 뒤 컨테이너를 재생성합니다. 값이 초기화되는 이유를 쓰기 레이어의 수명으로 설명합니다.

### 실습 4: 포트 게시 제거

애플리케이션의 `ports`를 제거합니다.

- 호스트 `curl`은 실패해야 합니다.
- 같은 네트워크의 클라이언트 요청은 성공해야 합니다.

내부 접근과 외부 게시가 독립된 설정임을 확인합니다.

수명 관찰과 자기 설명을 마친 뒤에만 `reference/`와 `./verify.sh reference`를 비교합니다.

## 21. Compose 설정에서 자주 생기는 착각

### “Compose가 컨테이너 오케스트레이션의 모든 문제를 해결합니다”

단일 또는 소수 호스트의 개발·운영 자동화에는 유용하지만, 클러스터 일정 관리, 자동 수평 확장, 분산 비밀값 관리, 고가용성을 자동 제공하지 않습니다.

### “depends_on이면 DB가 쿼리를 받을 준비가 됐습니다”

짧은 형식은 시작 순서만 표현합니다. 준비 상태에는 `healthcheck`와 `service_healthy`가 필요하며, 실행 중 재연결은 애플리케이션 책임입니다.

### “down은 모든 데이터를 삭제합니다”

기본 `down`은 이름 있는 볼륨을 보존합니다. `down -v`가 볼륨을 제거합니다.

### “같은 Compose 파일이면 모든 서비스가 자동으로 통신합니다”

기본 네트워크를 사용하면 대체로 가능하지만, 명시적 네트워크를 나누면 공통 네트워크가 없는 서비스는 통신할 수 없습니다.

### “비밀값 파일이면 완전한 비밀 관리입니다”

이미지와 일반 환경변수 노출을 줄이는 수단입니다. 원본 호스트 파일의 보호와 회전은 별도 책임입니다.

## 22. 서비스 구성 원칙

- 사용자 정의 브리지는 컨테이너 이름 기반 DNS를 제공합니다.
- 내부 서비스는 IP가 아니라 서비스 이름과 컨테이너 포트로 연결합니다.
- 외부에서 필요한 포트만 `ports`로 게시합니다.
- 이름 있는 볼륨은 컨테이너 수명과 독립된 상태를 저장합니다.
- 호스트 경로 마운트는 호스트 파일 접근이 필요할 때 사용하지만 경로와 권한에 종속됩니다.
- 설정, 비밀값, 영속 데이터는 서로 다른 방식으로 관리합니다.
- Compose는 원하는 멀티 서비스 상태를 파일로 선언합니다.
- 실행 중인 상태와 요청을 받을 준비가 된 상태는 다르며, 상태 검사가 후자를 판정합니다.
- `depends_on`은 시작 순서를 제어하지만 실행 중 복구 기능은 아닙니다.

## 공식 문서

- Compose 파일 참고: https://docs.docker.com/reference/compose-file/
- 서비스 정의와 상태 검사: https://docs.docker.com/reference/compose-file/services/
- 시작 순서: https://docs.docker.com/compose/how-tos/startup-order/
- Docker 볼륨: https://docs.docker.com/engine/storage/volumes/
- Docker 네트워크: https://docs.docker.com/engine/network/
