# Persistent Counter Service

파일 기반 counter를 HTTP API로 제공하고, Docker Compose named volume을 통해 container 재생성 뒤에도 상태를 보존하는 소형 서비스다. 단순한 demo가 아니라 process, image, network, health check, persistent storage의 수명 경계를 한 프로젝트에서 확인할 수 있는 완성된 실행 단위다.

## Features

- `GET /healthz`: process-local liveness 응답
- `GET /count`: 현재 counter 조회
- `POST /increment`: lock으로 직렬화된 read-modify-write
- temporary file, `fsync`, `os.replace`를 이용한 durable atomic write
- non-root container runtime
- service DNS를 사용하는 Compose client
- container와 분리된 named volume lifecycle

## Architecture

`CounterStore`가 counter file과 동시성 제어를 소유한다. HTTP handler는 storage 구현을 직접 다루지 않고 `read()`와 `increment()` contract만 사용한다. Compose에서는 `app`만 volume과 host port를 소유하고, `client`는 `app:8080` service DNS를 통해 접근한다.

## Run

```sh
docker compose up -d --build app
curl http://127.0.0.1:18083/count
curl -X POST http://127.0.0.1:18083/increment
docker compose run --rm client
```

상태를 유지한 채 container와 network만 내리려면 다음을 사용한다.

```sh
docker compose down
docker compose up -d app
```

volume까지 제거하면 counter 상태도 삭제된다.

```sh
docker compose down -v
```

## Tests

Python runtime만으로 API와 concurrent increment를 검증한다.

```sh
python -m unittest discover -s tests -v
```

Docker가 있는 환경에서는 image, service DNS, health gate, named volume persistence를 함께 검증한다.

```sh
./tests/integration.sh
```

## Design decisions

Counter file이 손상된 경우 `0`으로 조용히 초기화하지 않는다. 해당 상태는 데이터 손실 가능성이 있으므로 API가 `500 counter_state_invalid`를 반환한다. Increment는 하나의 lock 아래에서 read, modify, atomic replace를 수행해 같은 process 안의 concurrent request가 update를 잃지 않게 한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Counter storage ownership | `app/server.py` |
| 1-1 | Atomic counter persistence | `app/server.py` |
| 2 | HTTP response and route contract | `app/server.py` |
| 2-1 | Serialized increment transaction | `app/server.py` |
| 3 | Server composition and runtime boundary | `app/server.py` |
| 4 | Process-local readiness probe | `app/healthcheck.py` |
| 5 | Non-root runtime image | `app/Dockerfile` |
| 6 | Compose service ownership | `compose.yaml` |
| 6-1 | Service DNS client | `compose.yaml` |
| 6-2 | Named resource lifecycle | `compose.yaml` |
| 7 | HTTP behavior verification | `tests/test_server.py` |
| 7-1 | Container lifecycle verification | `tests/integration.sh` |

## Scope and limitations

이 프로젝트의 lock은 단일 process 안에서만 유효하다. 같은 counter file을 여러 process가 동시에 수정하는 deployment는 지원하지 않는다. 고가용성 또는 multi-instance 환경에서는 database나 별도의 transactional storage가 필요하다.
