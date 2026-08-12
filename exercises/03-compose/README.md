# Compose, 서비스 DNS와 볼륨

HTTP 애플리케이션과 일회성 클라이언트를 같은 사용자 정의 네트워크에 연결합니다. 요청 횟수는 이름 있는 볼륨에 저장합니다.

## 구성할 상태

- 서비스 이름 `app`으로 내부 요청합니다.
- 호스트 공개 포트와 컨테이너 내부 포트를 구분합니다.
- 이름 있는 볼륨이 컨테이너 재생성 뒤에도 유지됨을 확인합니다.
- `docker compose down`과 `down -v`의 차이를 확인합니다.

## 실행

저장소 루트에서 작업공간을 만든 뒤 그 사본의 `compose.yaml`만 수정합니다.

```sh
python3 scripts/new-workspace.py exercises/03-compose
cd exercises/03-compose
```

시작 상태에서는 실패하고 구현 뒤에는 통과해야 합니다.

```sh
./verify.sh workspace
```

관찰과 자기 설명을 끝낸 뒤에만 `reference/`와 `./verify.sh reference`를 비교합니다.

## 서비스 연결

- 애플리케이션의 8080 포트를 호스트 `127.0.0.1:18083`에 게시합니다.
- `/data`에 `app-data` 볼륨을 마운트합니다.
- 애플리케이션과 클라이언트를 `app-net`에 연결합니다.
- 애플리케이션 상태 검사가 통과한 뒤 클라이언트가 실행되게 합니다.
- 클라이언트 URL은 컨테이너 IP가 아닌 `http://app:8080/healthz`입니다.

## 수동 관찰

```sh
cd workspace
docker compose up -d app
docker compose run --rm client
docker compose exec app cat /data/counter.txt
docker compose down
docker compose up -d app
docker compose exec app cat /data/counter.txt
docker compose down -v
```

## 권장 구현 순서

아래 번호는 실제 Git 이력이 아니라 `reference/` 전체의 학습용 construction order입니다. 파일마다 번호를 다시 시작하지 않습니다.

| 번호 | 구현 경계 |
|---:|---|
| 1 | counter state와 원자 파일 교체 |
| 2 | route와 동시성 경계 |
| 3 | app-local readiness probe |
| 4 | non-root app image |
| 5 | app의 port·volume·network·health 소유권 |
| 6 | service DNS를 쓰는 client |
| 7 | named network와 volume lifecycle |

## 완료 기준

- [ ] `./verify.sh workspace`가 통과하고 client가 고정 IP가 아닌 `app:8080` 서비스 이름으로 요청한다.
- [ ] app의 상태 검사가 준비되기 전 client가 실행되지 않으며 호스트 공개 포트와 내부 포트를 각각 확인한다.
- [ ] `down` 뒤 counter가 유지되고 `down -v` 뒤에는 초기화되는 관찰 결과를 기록한다.

## 자기 설명

1. 호스트의 `127.0.0.1:18083`, app의 `0.0.0.0:8080`, client의 `app:8080`은 각각 어느 네트워크 관점의 주소인가?
2. 컨테이너 재생성과 volume 삭제가 상태에 서로 다른 결과를 만드는 이유는 무엇인가?
3. 단순 시작 순서와 `service_healthy` 의존성이 보장하는 조건은 어떻게 다른가?
