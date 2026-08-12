# 하나의 서버를 이미지로 만들기

1장의 HTTP 서버를 Docker 이미지로 만들고 컨테이너의 PID 1, 포트, 쓰기 가능 계층을 관찰합니다.

## 이미지에 담을 조건

- Dockerfile의 빌드 컨텍스트와 `COPY`를 이해합니다.
- 서버가 컨테이너 안에서 `0.0.0.0:8080`의 연결을 기다리게 합니다.
- 배열 형식의 시작 명령을 사용합니다.
- 비특권 사용자로 서버를 실행합니다.
- 컨테이너의 쓰기 가능 계층이 재생성할 때 사라짐을 확인합니다.

## 실행

저장소 루트에서 작업공간을 만든 뒤 학습자 사본만 수정합니다.

```sh
python3 scripts/new-workspace.py exercises/02-container
cd exercises/02-container
```

`workspace/Dockerfile`의 미완성 경계를 채웁니다. 시작 상태에서는 실패하고 구현 뒤에는 통과해야 합니다.

```sh
./verify.sh workspace
```

관찰과 자기 설명을 끝낸 뒤에만 `reference/`와 `./verify.sh reference`를 비교합니다.

## Dockerfile 작성

`workspace/Dockerfile`을 완성합니다.

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

## 권장 구현 순서

아래 번호는 실제 Git 이력이 아니라 `reference/` 전체의 학습용 construction order입니다. 파일마다 번호를 다시 시작하지 않습니다.

| 번호 | 구현 경계 |
|---:|---|
| 1 | container에서 실행할 HTTP server 계약 |
| 2 | 고정 Python runtime과 listen 환경 |
| 3 | artifact copy와 ownership |
| 4 | non-root process·port·exec entrypoint |

## 완료 기준

- [ ] `./verify.sh workspace`가 통과하고 새 이미지의 서버가 비특권 UID/GID로 `0.0.0.0:8080`에서 응답한다.
- [ ] 컨테이너의 PID 1이 Python 서버이며 종료 신호를 받은 뒤 컨테이너가 제한 시간 안에 멈추는지 확인한다.
- [ ] 쓰기 가능 계층에 만든 파일은 컨테이너 재생성 뒤 사라지고 이미지의 파일은 다시 나타나는 증거를 남긴다.

## 자기 설명

1. 셸 형식 시작 명령보다 JSON 배열 형식으로 서버를 직접 실행하는 편이 신호 전달에 유리한 이유는 무엇인가?
2. `EXPOSE 8080`과 실제 호스트 포트 게시가 각각 보장하는 것은 무엇인가?
3. 이미지 계층, 컨테이너 쓰기 가능 계층, volume 중 어느 상태를 어떤 수명으로 보존해야 하는가?
