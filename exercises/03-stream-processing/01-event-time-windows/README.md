# Event-time window와 late correction

도착 순서가 아니라 `occurred_at`을 기준으로 fixed window 집계를 만들고, duplicate와 late event의 처리 경계를 구현한다.

문서:

- [`unbounded data와 event time`](../../../docs/03-stream-processing/01-unbounded-data-and-event-time.md)
- [`window·watermark·trigger`](../../../docs/03-stream-processing/02-windows-watermarks-and-triggers.md)
- [`state·dedup·delivery`](../../../docs/03-stream-processing/03-state-deduplication-and-delivery.md)

## 입력 계약

각 event는 다음 필드를 가진다.

```python
{
    "event_id": "e-1",
    "key": "store-a",
    "occurred_at": "2026-08-09T00:04:59Z",
    "amount": 7,
}
```

`solution.py`는 다음 함수를 제공한다.

```python
def window_totals(events: list[dict], window_minutes: int) -> list[dict]: ...
def lateness_class(event_time: str, watermark: str, allowed_minutes: int) -> str: ...
```

`window_totals`:

- `event_id`가 같은 event는 한 번만 반영한다.
- UTC event time을 `[window_start, window_end)` fixed window에 배치한다.
- 입력 도착 순서와 무관한 정렬 결과를 반환한다.
- processing time이나 현재 시각을 사용하지 않는다.

`lateness_class`:

- watermark가 window 또는 event보다 앞이면 `ON_TIME`
- watermark는 지났지만 allowed lateness 안이면 `CORRECTABLE`
- allowed lateness도 지났으면 `DROPPED`

이 축소 모델에서 lateness는 event time 자체를 기준으로 판정한다. 실제 pipeline에서는 window end, source별 watermark, idle partition과 trigger 정책을 함께 정의해야 한다.

## 완료 기준

- 5분 window에서 `00:04:59`와 `00:05:00`이 서로 다른 window에 들어간다.
- 입력을 뒤집어도 결과가 같다.
- duplicate event가 합계를 두 번 늘리지 않는다.
- timezone이 없는 timestamp는 거부한다.
- on-time, correctable late, dropped late를 구분한다.

## 자기 설명

1. processing time으로 window를 만들면 replay 결과가 달라질 수 있는 이유는 무엇인가?
2. watermark가 “그 이전 event가 절대 오지 않는다”는 보장이 아닌 이유는 무엇인가?
3. correction을 허용할 때 sink는 어떤 stable result key와 version 계약이 필요한가?

## 검증

```bash
./scripts/new-workspace.sh exercises/03-stream-processing/01-event-time-windows
./scripts/check-workspace.sh exercises/03-stream-processing/01-event-time-windows
```

초기 skeleton은 `GUIDE_SEMANTIC:event-time-windows`로 실패한다.
