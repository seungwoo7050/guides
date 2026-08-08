# 로그, 지표와 상태 경계

표준 라이브러리 HTTP service에 관측 계약을 구현합니다. 특정 수집 제품보다 신호의 의미와 schema를 검증합니다.

관련 문서: [`docs/14-observability-and-alerting.md`](../../docs/14-observability-and-alerting.md)

## 구현 계약

`skeleton/app.py`의 `create_server(log_stream, release, ready)`를 완성합니다.

- `/healthz`: process 생존, dependency와 무관하게 200
- `/readyz`: dependency 준비 여부에 따라 200 또는 503
- `/api/items/<id>`: 정상 사용자 경로
- `/api/fail`: dependency failure를 나타내는 503
- `/metrics`: 요청 수와 duration 집계
- 유효한 `X-Request-ID`는 보존하고 잘못된 값은 새로 생성
- JSON log에 timestamp, service, release, request_id, event, route, status, duration_ms 포함
- Authorization·Cookie 값은 로그에 남기지 않음
- metric label은 실제 item ID가 아니라 `/api/items/:id` route 사용

## 검증

```sh
cd exercises/14-observability
./verify.sh skeleton
./verify.sh reference
```

검증기는 실제 loopback HTTP 요청을 보내 로그와 metric을 함께 확인합니다.

## 완료 기준

- [ ] `./verify.sh skeleton`이 통과하고 `/healthz`와 `/readyz`가 dependency 실패에서 서로 다른 상태를 반환한다.
- [ ] 한 요청을 request ID로 응답·JSON log·metric 결과까지 추적할 수 있고 Authorization·Cookie 값은 어디에도 남지 않는다.
- [ ] item별 ID가 아닌 안정된 route label로 요청 수와 duration이 집계되어 label 집합이 입력 수에 따라 늘지 않는다.

## 자기 설명

1. liveness와 readiness를 같은 dependency 검사로 구현하면 장애와 재시작 동작이 어떻게 악화될 수 있는가?
2. 실제 item ID를 metric label로 쓰면 저장·질의 비용과 경보 신뢰도에 어떤 문제가 생기는가?
3. 외부 `X-Request-ID`를 무조건 신뢰하지 않고 형식을 제한해야 하는 이유는 무엇인가?
