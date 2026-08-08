# Compose, 서비스 DNS와 볼륨

HTTP 애플리케이션과 일회성 클라이언트를 같은 사용자 정의 네트워크에 연결합니다. 요청 횟수는 이름 있는 볼륨에 저장합니다.

## 구성할 상태

- 서비스 이름 `app`으로 내부 요청합니다.
- 호스트 공개 포트와 컨테이너 내부 포트를 구분합니다.
- 이름 있는 볼륨이 컨테이너 재생성 뒤에도 유지됨을 확인합니다.
- `docker compose down`과 `down -v`의 차이를 확인합니다.

## 실행

```sh
./verify.sh reference
```

시작 코드의 `compose.yaml` TODO를 채운 뒤:

```sh
./verify.sh skeleton
```

## 서비스 연결

- 애플리케이션의 8080 포트를 호스트 `127.0.0.1:18083`에 게시합니다.
- `/data`에 `app-data` 볼륨을 마운트합니다.
- 애플리케이션과 클라이언트를 `app-net`에 연결합니다.
- 애플리케이션 상태 검사가 통과한 뒤 클라이언트가 실행되게 합니다.
- 클라이언트 URL은 컨테이너 IP가 아닌 `http://app:8080/healthz`입니다.

## 수동 관찰

```sh
cd reference
docker compose up -d app
docker compose run --rm client
docker compose exec app cat /data/counter.txt
docker compose down
docker compose up -d app
docker compose exec app cat /data/counter.txt
docker compose down -v
```
