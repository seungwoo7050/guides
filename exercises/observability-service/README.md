# Observability Service

Structured JSON log, correlation ID, bounded-label Prometheus metrics, liveness, readiness, normalized API route를 제공하는 dependency-free Python HTTP service다.

## Run

```sh
python app.py --host 127.0.0.1 --port 8080 --release release-42 --log-file requests.jsonl
curl -i http://127.0.0.1:8080/healthz
curl -i http://127.0.0.1:8080/readyz
curl -i -H 'X-Request-ID: trace-123' http://127.0.0.1:8080/api/items/42
curl http://127.0.0.1:8080/metrics
```

Readiness failure를 재현하려면 `--no-ready`를 사용한다.

## Endpoints

- `/healthz`: process liveness
- `/readyz`: configured readiness state
- `/api/items/:id`: normalized application route
- `/api/fail`: dependency failure response
- `/metrics`: request count와 duration sum/count

## Telemetry contract

Log record는 UTC timestamp, level, service, release, request ID, method, normalized route, status, duration을 포함한다. Metric label에는 method, normalized route, status class, release만 포함한다. Raw item ID나 request ID를 label에 넣지 않아 cardinality가 request volume에 따라 증가하지 않게 한다.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Design decisions

Metric state와 log stream write를 같은 lock boundary에서 갱신해 multi-thread request의 count와 JSONL record가 깨지지 않게 한다. Caller가 전달한 `X-Request-ID`는 제한된 character set과 길이를 통과한 경우에만 신뢰하고, 나머지는 random identifier로 교체한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Telemetry state ownership | `app.py` |
| 2 | Synchronized request telemetry recording | `app.py` |
| 3 | Bounded-label metrics projection | `app.py` |
| 4 | Server and handler lifecycle | `app.py` |
| 5 | Correlation ID validation | `app.py` |
| 6 | Health and API routing | `app.py` |
| 7 | Executable service CLI | `app.py` |
| 8 | HTTP telemetry verification | `tests/test_app.py` |

## Scope and limitations

Metrics는 process memory에만 존재하며 restart 시 초기화된다. Histogram bucket, trace export, log shipping, authentication, TLS termination은 포함하지 않는다. Production에서는 `/metrics`와 health endpoint의 exposure policy를 별도로 적용해야 한다.
