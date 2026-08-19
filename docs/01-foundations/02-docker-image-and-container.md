# Docker 이미지와 컨테이너

이 장에서는 1장의 HTTP 서버를 재현 가능한 이미지로 만들고 컨테이너로 실행합니다. 목표는 Docker 명령을 외우는 것이 아니라 이미지, 컨테이너, 프로세스, 파일 시스템의 경계를 구분하는 것입니다.

완료하면 다음 질문에 답할 수 있어야 합니다.

- 이미지는 실행 중인 프로세스인가?
- 컨테이너를 삭제하면 어떤 데이터가 사라지는가?
- Dockerfile의 명령 순서가 빌드 시간과 이미지 크기에 왜 영향을 주는가?
- 컨테이너의 주 프로세스를 백그라운드로 보내면 왜 컨테이너가 종료되는가?

## 1. Docker가 해결하는 문제

애플리케이션은 소스 코드만으로 실행되지 않습니다. 다음 조건이 실행 결과에 영향을 줍니다.

- 운영체제와 CPU 아키텍처
- 런타임 버전
- 설치된 시스템 라이브러리
- 패키지 버전
- 설정 파일
- 환경변수
- 실행 사용자와 파일 권한
- 시작 명령

개발자의 노트북에서 수동으로 설치한 환경은 다른 사람에게 그대로 전달되지 않습니다. “Python 3을 설치하고 이 패키지를 받은 뒤 이 파일을 복사하고 이 명령을 실행하라”는 절차가 길어질수록 누락과 환경 차이가 생기기 쉽습니다.

Docker는 애플리케이션 실행에 필요한 파일 시스템과 실행 메타데이터를 이미지로 묶고, 그 이미지를 격리된 프로세스로 실행하는 표준 인터페이스를 제공합니다.

```text
소스 코드 + Dockerfile + 빌드 컨텍스트
                    │
                    ▼
                  이미지
                    │
              docker run
                    ▼
                 컨테이너
```

Docker가 모든 재현성 문제를 자동으로 해결하지는 않습니다. 가변 태그, 빌드 시 외부 다운로드, 고정하지 않은 패키지 저장소는 같은 Dockerfile에서도 다른 결과를 만들 수 있습니다. Docker는 재현 가능한 절차를 표현할 기반을 제공하며 실제 재현성은 작성자가 관리해야 합니다.

## 2. 컨테이너와 가상 머신

가상 머신은 일반적으로 게스트 운영체제의 커널까지 포함합니다. 컨테이너는 호스트의 Linux 커널을 공유하면서 프로세스, 네트워크, 마운트 등의 관점을 격리합니다.

```text
가상 머신                         컨테이너
┌─────────────┐                 ┌─────────────┐
│ 앱           │                 │ 앱           │
│ 라이브러리    │                 │ 라이브러리    │
│ 게스트 OS     │                 │ 이미지 파일계층 │
│ 게스트 커널   │                 ├─────────────┤
├─────────────┤                 │ 호스트 커널 공유│
│ 하이퍼바이저  │                 └─────────────┘
└─────────────┘
```

컨테이너는 별도의 작은 컴퓨터가 아니라 호스트 커널 위에서 실행되는 프로세스입니다. 이 구조에는 다음 특성이 있습니다.

- 컨테이너 시작이 빠릅니다.
- 같은 호스트에서 이미지 레이어를 공유할 수 있습니다.
- Linux 컨테이너 안의 프로그램은 Linux 커널 ABI를 전제로 합니다.
- macOS와 Windows의 Docker Desktop은 내부 Linux VM을 통해 Linux 컨테이너를 실행합니다.

## 3. 이미지와 컨테이너

### 3.1 이미지

이미지는 읽기 전용 파일 시스템 레이어와 설정 메타데이터의 묶음입니다.

메타데이터에는 다음이 포함될 수 있습니다.

- 기본 실행 명령
- entrypoint
- 환경변수
- 작업 디렉터리
- 실행 사용자
- 노출 포트에 대한 설명

이미지 자체는 실행 중인 프로세스가 아닙니다.

### 3.2 컨테이너

컨테이너는 이미지를 실행한 인스턴스입니다. 이미지의 읽기 전용 레이어 위에 컨테이너 전용 쓰기 가능 레이어가 추가됩니다.

```text
컨테이너
┌──────────────────────────┐
│ writable container layer │  컨테이너마다 별도
├──────────────────────────┤
│ application layer        │
├──────────────────────────┤
│ runtime layer            │  이미지의 읽기 전용 레이어
├──────────────────────────┤
│ base image layers        │
└──────────────────────────┘
```

같은 이미지에서 여러 컨테이너를 만들면 읽기 전용 이미지 레이어는 공유하지만 각 컨테이너의 프로세스와 쓰기 레이어는 서로 다릅니다.

### 3.3 컨테이너를 삭제할 때 사라지는 데이터

컨테이너를 삭제하면 그 컨테이너의 쓰기 가능 계층도 사라집니다. 애플리케이션이 컨테이너 내부 경로에 쓴 파일은 별도 볼륨이나 호스트 경로 마운트가 없다면 함께 사라집니다.

이미지는 그대로 남으므로 같은 이미지로 새 컨테이너를 만들 수 있지만 이전 컨테이너에서 실행 중 변경한 내용은 새 컨테이너에 포함되지 않습니다.

## 4. Dockerfile과 빌드 흐름

Dockerfile은 이미지를 만드는 단계의 목록입니다.

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
WORKDIR /app
COPY server.py /app/server.py
ENV APP_HOST=0.0.0.0 APP_PORT=8080
EXPOSE 8080
ENTRYPOINT ["python", "/app/server.py"]
```

빌드합니다.

```sh
docker build -t web-infra-http:exercise .
```

실행합니다.

```sh
docker run --rm -p 18082:8080 web-infra-http:exercise
```

`-t`는 이미지에 사람이 읽을 수 있는 태그를 붙입니다. `--rm`은 컨테이너 종료 뒤 컨테이너 객체를 자동으로 제거합니다. `-p 18082:8080`은 호스트의 18082 포트를 컨테이너의 8080 포트에 연결합니다.

## 5. 빌드 컨텍스트

다음 명령에서 마지막 `.`은 현재 디렉터리를 빌드 컨텍스트로 사용한다는 뜻입니다.

```sh
docker build -t example .
```

Dockerfile의 `COPY`와 `ADD`는 이 컨텍스트 안의 파일만 읽을 수 있습니다.

```dockerfile
COPY app/server.py /app/server.py
```

`../secret.txt`처럼 컨텍스트 밖의 파일을 복사하려고 하면 접근할 수 없습니다. 빌드에 필요한 파일을 포함하는 디렉터리를 컨텍스트 루트로 선택해야 합니다.

### 5.1 `.dockerignore`

빌더에 전달하지 않을 파일을 지정합니다.

```text
.git
.env
*.log
__pycache__
node_modules
backups
```

주요 효과는 다음과 같습니다.

1. 컨텍스트 전송량을 줄입니다.
2. 무관한 파일 변경으로 `COPY` 캐시가 무효화되는 일을 줄입니다.
3. 비밀 파일이나 로컬 산출물이 실수로 이미지에 포함될 가능성을 낮춥니다.

`.dockerignore`만으로 보안 경계가 완성되지는 않습니다. 민감 파일은 애초에 빌드 컨텍스트 밖에 두고 필요한 비밀값은 빌드나 실행 시 별도의 안전한 경로로 전달해야 합니다.

## 6. 자주 사용하는 Dockerfile 명령

### `FROM`

```dockerfile
FROM python:3.12-slim-bookworm
```

베이스 이미지를 선택합니다. 태그가 가리키는 대상은 시간이 지나면서 바뀔 수 있습니다. 장기간 같은 결과가 필요하다면 다이제스트 고정을 검토합니다.

### `RUN`

```dockerfile
RUN python -m compileall /app
```

빌드 시점에 명령을 실행하고 파일 시스템 변경 결과를 이미지 레이어로 남깁니다. 컨테이너가 시작될 때 실행되는 명령과 구분해야 합니다.

### `COPY`

```dockerfile
COPY app/ /app/
```

빌드 컨텍스트의 파일을 이미지에 복사합니다. 단순 파일 복사는 `ADD`보다 `COPY`가 의도를 명확하게 드러냅니다.

### `WORKDIR`

```dockerfile
WORKDIR /app
```

이후 `RUN`, `COPY`의 상대 목적지, 컨테이너 시작 명령의 기본 작업 디렉터리를 설정합니다. `RUN cd /app && ...`를 반복하는 것보다 명확합니다.

### `ENV`

```dockerfile
ENV APP_PORT=8080
```

이미지와 컨테이너의 기본 환경변수를 설정합니다. 실행할 때 `docker run -e`로 덮어쓸 수 있습니다. 비밀번호를 `ENV`에 넣으면 이미지 설정과 검사 결과에 남으므로 사용하지 않습니다.

### `USER`

```dockerfile
USER 65532:65532
```

이후 `RUN` 단계의 실행 사용자와 컨테이너의 기본 실행 사용자를 설정합니다. 서비스가 관리자 권한을 필요로 하지 않는다면 비특권 사용자로 실행해 권한 침해 시 피해 범위를 줄입니다.

숫자 UID만 사용하는 경우 파일 소유권과 볼륨 권한을 별도로 확인해야 합니다.

### `EXPOSE`

```dockerfile
EXPOSE 8080
```

이미지가 어떤 포트에서 서비스를 제공할 예정인지 메타데이터로 설명합니다. 실제로 호스트 포트를 열지는 않습니다. 외부 게시에는 `docker run -p` 또는 Compose의 `ports`를 사용합니다.

### `ENTRYPOINT`와 `CMD`

두 값은 컨테이너의 기본 실행 명령을 조합합니다.

```dockerfile
ENTRYPOINT ["python", "/app/server.py"]
CMD ["--verbose"]
```

개념적으로 실제 명령은 다음과 같습니다.

```text
python /app/server.py --verbose
```

`docker run image --quiet`처럼 실행 시 뒤쪽 인자를 주면 일반적으로 CMD가 교체됩니다. ENTRYPOINT까지 바꾸려면 `--entrypoint`를 사용합니다.

항상 두 지시어를 함께 쓸 필요는 없습니다. 실행 파일과 인자를 외부에서 쉽게 교체할 필요가 없는 간단한 이미지라면 ENTRYPOINT 하나로 충분할 수 있습니다.

## 7. 레이어와 이미지 크기

파일 시스템을 변경하는 Dockerfile 단계는 대체로 새로운 레이어를 만듭니다. 레이어는 이전 상태에 대한 변경분입니다.

```dockerfile
RUN apt-get install -y build-essential
RUN apt-get remove -y build-essential
```

두 번째 레이어에서 파일이 최종 파일 시스템에 보이지 않도록 해도 첫 번째 레이어의 바이트는 이미지 구성에 남습니다. 이미 만들어진 아래 레이어를 수정하는 것이 아니라 위 레이어에 삭제 상태를 추가하기 때문입니다.

임시 파일은 만든 단계에서 함께 제거합니다.

```dockerfile
RUN build-command \
    && copy-result /out/app \
    && rm -rf /tmp/build-files
```

빌드 도구와 런타임 파일을 근본적으로 분리하려면 멀티스테이지 빌드를 사용합니다.

```dockerfile
FROM golang:1.24-bookworm AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /out/app ./cmd/app

FROM scratch
COPY --from=build /out/app /app
ENTRYPOINT ["/app"]
```

최종 이미지는 마지막 `FROM`부터 시작하므로 빌드 스테이지의 컴파일러가 포함되지 않습니다.

## 8. Debian 패키지 설치 패턴

Debian 또는 Ubuntu 기반 이미지에서는 다음 패턴을 사용합니다.

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*
```

### `apt-get update`

패키지 자체를 업그레이드하지 않습니다. 저장소에 어떤 패키지 버전이 있는지 나타내는 인덱스를 내려받습니다.

### `apt-get install`

인덱스를 기준으로 패키지와 필수 의존성을 설치합니다.

### `-y`

비대화형 빌드에서 확인 질문에 자동으로 동의합니다.

### `--no-install-recommends`

필수 의존성 외의 추천 패키지를 자동으로 설치하지 않습니다. 필요한 기능이 추천 패키지에 있다면 해당 패키지를 명시적으로 추가합니다.

### 같은 `RUN`에 두는 이유

`apt-get update`를 별도 단계에 두면 그 레이어가 캐시된 상태에서 설치 목록만 바뀌는 경우가 생깁니다. 오래된 인덱스로 새 패키지를 설치하려다 실패할 수 있으므로 업데이트, 설치, 인덱스 제거를 같은 단계에 둡니다.

이미지 빌드에서는 대화형 사용을 염두에 둔 `apt`보다 스크립트 인터페이스인 `apt-get`을 사용합니다.

## 9. 빌드 캐시

Docker 빌더는 각 단계의 명령과 입력이 이전 빌드와 같으면 결과를 재사용합니다.

```dockerfile
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/
```

의존성 목록을 먼저 복사하고 설치한 뒤 자주 바뀌는 소스를 복사하면 소스만 바뀌었을 때 무거운 의존성 설치 레이어를 재사용할 수 있습니다.

반대로 다음 순서는 소스 파일 하나만 바뀌어도 `COPY .` 단계의 캐시가 무효화되어 `pip install`이 다시 실행될 수 있습니다.

```dockerfile
COPY . /app/
RUN pip install --no-cache-dir -r requirements.txt
```

캐시는 정확성보다 속도를 위한 기능입니다. 최신 베이스 이미지를 다시 확인해야 한다면 `docker build --pull`을 사용합니다. 모든 단계를 재실행하려면 `--no-cache`를 사용할 수 있지만 일상적인 문제 해결 수단으로 남용하지 않습니다.

## 10. 실행 명령의 배열 형식과 셸 형식

### 배열 형식

```dockerfile
ENTRYPOINT ["python", "/app/server.py"]
```

셸을 거치지 않고 프로그램을 직접 실행합니다. 프로그램이 컨테이너의 PID 1이 되어 시그널을 직접 받습니다.

### 셸 형식

```dockerfile
ENTRYPOINT python /app/server.py
```

일반적으로 `/bin/sh -c`가 먼저 실행되고 실제 서버는 그 자식이 됩니다.

```text
PID 1: /bin/sh -c python /app/server.py
└─ PID 7: python /app/server.py
```

셸이 시그널을 올바르게 전달하지 않으면 `docker stop`의 SIGTERM이 서버까지 도달하지 않을 수 있습니다. `ENTRYPOINT`와 `CMD`는 특별한 이유가 없으면 배열 형식을 사용합니다.

`RUN`은 `&&`, 변수 확장, 파이프 등 셸 문법이 자주 필요하므로 셸 형식이 자연스럽습니다.

## 11. PID 1과 컨테이너 수명

Docker는 컨테이너의 주 프로세스가 살아 있는 동안 컨테이너를 실행 상태로 봅니다. 컨테이너 안에서 서버를 백그라운드로 보내고 시작 스크립트가 끝나면 PID 1이 종료되어 컨테이너도 끝납니다.

잘못된 예:

```sh
#!/bin/sh
python /app/server.py &
exit 0
```

올바른 단순 예:

```sh
#!/bin/sh
exec python /app/server.py
```

`exec`는 셸 프로세스를 서버 프로세스로 교체합니다. 서버가 PID 1이 되고 Docker의 시그널을 직접 받습니다.

PID 1에는 일반 프로세스와 다른 시그널 처리·고아 프로세스 회수 특성이 있습니다. 자식 프로세스를 많이 만드는 애플리케이션이라면 `--init` 또는 작은 init 프로세스를 검토할 수 있지만 먼저 불필요한 셸 계층을 없애고 주 프로세스를 직접 실행합니다.

## 12. 포트 게시

컨테이너 안의 서버가 `0.0.0.0:8080`에서 수신한다고 해서 호스트나 외부 네트워크에 자동으로 노출되지는 않습니다.

```sh
docker run -p 18082:8080 image
```

의미:

```text
host :18082 → container :8080
```

호스트의 18082와 컨테이너의 8080은 서로 다른 네트워크 네임스페이스의 포트입니다.

서버가 컨테이너 내부에서 `127.0.0.1:8080`에만 바인드하면 Docker의 포트 전달을 통해 외부에서 접근하지 못할 수 있습니다. 컨테이너 외부에서 받아야 하는 서비스는 일반적으로 컨테이너 안에서 `0.0.0.0`에 바인드합니다.

## 13. 컨테이너 데이터

다음 명령으로 컨테이너 안에 파일을 만듭니다.

```sh
docker run --name temp-data image sh -c 'echo hello >/tmp/value && cat /tmp/value'
```

컨테이너를 삭제한 뒤 같은 이미지로 새 컨테이너를 만들면 `/tmp/value`는 존재하지 않습니다.

```sh
docker rm temp-data
docker run --rm image cat /tmp/value
```

영속 데이터는 다음 장에서 볼륨에 둡니다. 로그처럼 외부 수집 시스템으로 내보낼 데이터는 표준 출력과 표준 오류를 사용합니다. 애플리케이션 코드와 기본 설정은 이미지에 둡니다. 무엇을 어디에 둘지 구분하는 것이 중요합니다.

## 14. 기본 진단 명령

### 이미지

```sh
docker image ls
docker image inspect web-infra-http:exercise
docker image history web-infra-http:exercise
```

### 컨테이너

```sh
docker ps
docker ps -a
docker inspect container-name
```

### 로그

```sh
docker logs container-name
docker logs -f container-name
```

### 내부 명령

```sh
docker exec container-name ps -ef
docker exec -it container-name sh
```

`docker exec`는 이미 실행 중인 컨테이너에 새 프로세스를 추가합니다. 이미지 내용이 바뀌는 것은 아니며 수동 수정은 컨테이너 재생성 시 사라질 수 있습니다. 디버깅에 사용하고 영구 변경은 Dockerfile에 반영합니다.

### 종료

```sh
docker stop container-name
docker kill container-name
```

`stop`은 먼저 SIGTERM을 보내고 유예 시간이 지난 뒤 SIGKILL을 사용합니다. `kill`은 기본적으로 SIGKILL을 보냅니다.

## 15. 실습

실습 위치:

```sh
python3 scripts/new-workspace.py exercises/02-container
cd exercises/02-container
```

### 실습 1: 자신의 이미지 빌드와 실행

```sh
./verify.sh workspace
```

검증은 다음을 확인합니다.

- 이미지 빌드 성공
- 컨테이너의 HTTP 응답
- 이미지의 entrypoint 형태
- 서버 프로세스의 종료

### 실습 2: 시작 코드 완성

`workspace/Dockerfile`의 미완성 부분을 채웁니다. `reference/`를 먼저 읽지 말고 다음 질문에 답한 뒤 작성합니다.

- 서버 파일은 이미지의 어느 경로에 있어야 하는가?
- 서버는 컨테이너 안에서 어느 주소에 바인드해야 하는가?
- 호스트 포트와 컨테이너 포트는 각각 무엇인가?
- 메인 프로세스를 직접 실행하는 JSON 배열은 무엇인가?

### 실습 3: 백그라운드 실행 실패

`breakages/Dockerfile.background`를 빌드하고 실행합니다.

```sh
docker build -f breakages/Dockerfile.background -t web-infra-background .
docker run --name background-test web-infra-background
docker ps -a --filter name=background-test
docker logs background-test
docker rm background-test
```

서버 프로세스가 잠시 생성됐더라도 entrypoint 셸이 끝나면 컨테이너가 종료되는 것을 확인합니다.

### 실습 4: 쓰기 레이어 소실

```sh
docker build -t web-infra-exercise02:layer-observation workspace
docker run -d --name layer-test web-infra-exercise02:layer-observation
docker exec layer-test sh -c 'echo runtime >/tmp/runtime-value'
docker exec layer-test cat /tmp/runtime-value
docker rm -f layer-test
docker run --rm web-infra-exercise02:layer-observation sh -c 'test ! -e /tmp/runtime-value'
docker image rm web-infra-exercise02:layer-observation
```

수명 관찰과 자신의 설명을 정리한 뒤에만 `reference/`와 `./verify.sh reference`를 비교합니다.

## 16. 이미지와 컨테이너를 혼동하기 쉬운 경우

### “이미지를 실행하면 이미지가 바뀝니다”

컨테이너의 쓰기 레이어가 바뀝니다. 원본 이미지는 바뀌지 않습니다.

### “EXPOSE가 방화벽을 열어 줍니다”

`EXPOSE`는 메타데이터입니다. 실제 게시에는 `-p` 또는 Compose의 `ports`가 필요합니다.

### “컨테이너에 들어가서 패키지를 설치하면 수정이 완료됩니다”

현재 컨테이너에만 남는 임시 변경입니다. Dockerfile을 수정하고 이미지를 다시 빌드해야 재현할 수 있습니다.

### “레이어를 많이 합칠수록 항상 좋습니다”

관련된 임시 생성과 정리는 같은 `RUN`에 두는 것이 맞지만 모든 작업을 하나의 거대한 `RUN`으로 합치면 캐시 활용과 가독성이 나빠집니다. 논리적으로 함께 성공·실패해야 하는 작업을 묶습니다.

### “latest는 최신 버전을 고정합니다”

`latest`는 특별한 갱신 규칙이 아니라 단순한 태그 이름입니다. 시간이 지나 다른 다이제스트를 가리킬 수 있습니다.

## 17. 이미지 관리 원칙

- 이미지는 읽기 전용 파일 계층과 실행 메타데이터입니다.
- 컨테이너는 이미지를 실행한 프로세스와 쓰기 레이어입니다.
- Dockerfile은 이미지 생성 절차를 코드로 남깁니다.
- 빌드 컨텍스트는 `COPY`가 읽을 수 있는 입력 범위입니다.
- Dockerfile 순서는 캐시 효율에 영향을 줍니다.
- Debian 패키지 설치는 update, install, 목록 제거를 같은 `RUN`에 둡니다.
- `ENTRYPOINT`와 `CMD`는 기본적으로 배열 형식을 사용합니다.
- 메인 프로세스가 종료되면 컨테이너도 종료됩니다.
- 컨테이너 쓰기 레이어의 데이터는 컨테이너 삭제와 함께 사라집니다.

## 공식 문서

- Dockerfile reference: https://docs.docker.com/reference/dockerfile/
- Docker build best practices: https://docs.docker.com/build/building/best-practices/
- Docker run reference: https://docs.docker.com/reference/cli/docker/container/run/
- Multi-stage builds: https://docs.docker.com/build/building/multi-stage/
