# 하나의 서버를 이미지로 만들기

1장의 HTTP 서버를 Docker 이미지로 만들고 컨테이너의 PID 1, 포트, 쓰기 가능 계층을 관찰합니다.

## 이미지에 담을 조건

- Dockerfile의 빌드 컨텍스트와 `COPY`를 이해합니다.
- 서버가 컨테이너 안에서 `0.0.0.0:8080`의 연결을 기다리게 합니다.
- 배열 형식의 시작 명령을 사용합니다.
- 비특권 사용자로 서버를 실행합니다.
- 컨테이너의 쓰기 가능 계층이 재생성할 때 사라짐을 확인합니다.

## 실행

```sh
./verify.sh reference
```

시작 코드의 TODO를 채운 뒤:

```sh
./verify.sh skeleton
```

## Dockerfile 작성

`skeleton/Dockerfile`을 완성합니다.

1. `python:3.12-slim-bookworm`에서 시작합니다.
2. 작업 디렉터리를 `/app`으로 둡니다.
3. `app/server.py`를 `/app/server.py`로 복사합니다.
4. `APP_HOST=0.0.0.0`, `APP_PORT=8080`을 기본값으로 설정합니다.
5. 8080을 문서화합니다.
6. UID/GID 65532로 전환합니다.
7. JSON 배열 형식으로 Python 서버를 직접 실행합니다.

## 장애 관찰

```sh
docker build -f breakages/Dockerfile.background -t web-infra-exercise02:background .
docker run --name web-infra-exercise02-background web-infra-exercise02:background
docker ps -a --filter name=web-infra-exercise02-background
docker logs web-infra-exercise02-background
docker rm web-infra-exercise02-background
```

서버를 백그라운드로 보낸 셸이 종료되면 컨테이너도 종료됩니다.
