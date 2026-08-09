# Window, watermark와 trigger

## 학습 목표

- window가 무한 input을 유한한 계산 단위로 나누는 방법을 설명한다.
- watermark를 완전성 보장이 아닌 progress estimate로 해석한다.
- trigger, pane, accumulation과 allowed lateness가 결과 수정 방식에 미치는 영향을 설명한다.
- latency·completeness·cost 사이의 trade-off를 소비자 계약으로 만든다.

## 핵심 모델

```text
window
  어떤 event들이 같은 논리 계산 단위에 속하는가

watermark
  앞으로 이 시각보다 이른 event가 정상적으로 올 가능성이 낮다는 progress 추정

trigger
  현재 window state를 언제 결과로 emit할 것인가

pane
  한 window에서 한 번의 trigger가 만든 결과 묶음

allowed lateness
  watermark 뒤에도 얼마 동안 state를 유지하고 correction을 받을 것인가
```

window 종료 시각, watermark 통과 시각과 결과 publish 시각은 다르다.

## window 종류

### fixed/tumbling window

겹치지 않는 고정 길이 구간이다.

예:

```text
[10:00, 10:05)
[10:05, 10:10)
```

경계와 timezone을 고정해야 batch와 stream이 같은 결과를 만든다.

### sliding/hopping window

길이보다 짧은 간격으로 시작해 event가 여러 window에 속한다.

예: 최근 1시간 합계를 5분마다 계산한다. storage와 update volume이 커질 수 있다.

### session window

같은 key의 event 사이 gap이 일정 시간 이하인 동안 하나의 session으로 묶는다. late event가 두 session을 합칠 수 있으므로 merge와 correction 계약이 필요하다.

### global window

모든 record가 하나의 window다. unbounded aggregation이라면 trigger와 state cleanup 없이는 완료되지 않는다.

### calendar window

일·월·회계 기간처럼 timezone과 calendar 규칙을 따른다. 고정 24시간 duration과 다를 수 있다.

## watermark

watermark는 data source와 engine이 계산하는 추정이다. 다음 문장은 위험하다.

> watermark가 10:00을 지났으므로 10:00 이전 event는 절대 오지 않는다.

더 정확한 해석:

> 현재 source와 정책에 따르면 10:00 이전 event 대부분이 도착했다고 보고 결과를 진행한다. 이후 도착은 late data 정책으로 처리한다.

### watermark 품질

- partition 중 가장 느린 watermark가 전체 progress를 막을 수 있다.
- idle partition을 처리하지 않으면 watermark가 멈출 수 있다.
- producer timestamp가 잘못되면 지나치게 늦거나 빠르게 진행할 수 있다.
- source backlog와 event distribution 변화가 추정을 깨뜨릴 수 있다.

watermark lag와 late-event distribution을 관찰한다.

## trigger

### event-time trigger

watermark가 window end를 지날 때 emit한다. 일반적인 “on-time” 결과다.

### processing-time early trigger

watermark 전에도 낮은 latency의 잠정 결과를 emit한다. dashboard는 빠르게 보지만 값이 계속 바뀔 수 있다.

### count/data trigger

record 수가 일정량 쌓일 때 emit한다. traffic이 적으면 오래 기다릴 수 있고, traffic이 많으면 update가 잦다.

### late trigger

watermark 이후 late data가 도착하면 correction pane을 emit한다.

## accumulation mode

### accumulating

매 pane이 지금까지 window에 포함된 전체 결과를 담는다.

```text
pane 1: 10
pane 2: 15
pane 3: 18
```

consumer가 latest value로 upsert하기 쉽다. 같은 pane을 중복 적용하지 않도록 window key와 pane/version이 필요하다.

### discarding

각 pane이 새로 들어온 부분만 담는다.

```text
pane 1: +10
pane 2: +5
pane 3: +3
```

consumer가 정확히 한 번씩 합쳐야 한다. retry와 duplicate에 더 민감하다.

### retracting/update

이전 결과를 취소하고 새 결과를 적용한다. join/session merge처럼 과거 결과가 구조적으로 바뀔 때 필요하다. sink가 retraction을 지원하는지 확인한다.

## allowed lateness와 state lifetime

allowed lateness가 길면 completeness는 높아질 수 있지만 state와 update 비용이 증가한다.

결정 기준:

- 실제 late distribution p95/p99
- 업무 correction 허용 기간
- sink update 가능성
- state size와 checkpoint 비용
- consumer가 과거 변경을 처리할 수 있는가
- 마감·감사 정책

allowed lateness가 끝나면 late record를 무조건 버리기보다 다음 중 하나를 선택한다.

- dead-letter/quarantine
- 별도 correction pipeline
- batch backfill
- owner 승인
- metric만 기록하고 무시

## output key

window 결과는 적어도 다음으로 식별한다.

```text
business key
+ window start/end 또는 window ID
+ result version/pane identity
```

processing timestamp만 key로 쓰면 retry가 duplicate row를 만든다.

## finality

“final”에는 여러 수준이 있다.

- on-time: watermark가 window end를 지남
- lateness closed: allowed lateness가 끝남
- business closed: 회계 마감 등 외부 승인 완료
- immutable: 이후 correction이 별도 journal로만 반영

consumer에게 어느 수준인지 표시한다. `is_final=true` 하나로 모든 도메인 마감을 표현하기 어렵다.

## 예시: 실시간 주문 매출

정책:

```text
window           5분 fixed, UTC
early trigger    processing time 30초마다
on-time trigger  watermark가 window end 통과
late trigger     late event 1개 이상 도착 시 1분 debounce
allowed lateness 24시간
output           accumulating upsert
key              store_id + window_start
```

필요 metadata:

- result version
- emitted_at
- watermark_at_emit
- completeness state: EARLY/ON_TIME/CORRECTED/CLOSED
- source coverage

## 실패 모드

### watermark as wall clock

현재 시각에서 5분을 빼 watermark로 고정하지만 source 지연이 변한다. source progress와 late distribution을 반영한다.

### early result treated as final

consumer가 early pane을 확정 값으로 export한다. completeness state와 correction subscription을 contract에 포함한다.

### late data silently dropped

allowed lateness 0으로 두고 metric도 없다. discard count와 reason을 관찰하고 업무 영향에 따라 correction 경로를 둔다.

### session merge unsupported

late event가 두 session을 합치지만 sink가 이미 두 row를 append했다. retraction/upsert 또는 closed session 정책을 설계한다.

### unbounded global aggregation

trigger만 반복하고 state cleanup이 없어 state가 계속 증가한다. window, TTL 또는 approximate aggregation을 선택한다.

### pane duplicate

sink retry가 같은 increment pane을 두 번 더한다. stable pane ID, idempotent upsert 또는 transactional sink가 필요하다.

## 검증 질문

1. window boundary와 timezone이 batch path와 일치하는가?
2. watermark가 무엇을 관찰해 진전되는가?
3. early/on-time/late pane을 consumer가 구분하는가?
4. accumulating/discarding/retracting 중 무엇이며 sink 적용 규칙은 무엇인가?
5. allowed lateness 이후 record는 어디로 가는가?
6. state가 언제 삭제되고 과거 correction은 어떻게 처리되는가?

## 연결 연습

[`event-time windows`](../../exercises/03-stream-processing/01-event-time-windows/README.md)에서 fixed window, watermark와 late correction을 작은 모델로 구현한다.

## 완료 기준

- window·watermark·trigger가 서로 다른 책임임을 설명한다.
- latency·completeness·state cost를 정책으로 선택한다.
- 잠정 결과와 correction을 sink와 consumer가 안전하게 적용하도록 key와 version을 설계한다.
- late data를 숨기지 않고 관찰·수정 경로를 제공한다.

## 공식 자료 연결

Apache Beam Programming Guide의 windowing, watermarks, triggers와 late data 설명을 참고한다. 링크는 [`reference/official-sources.md`](../../reference/official-sources.md)에 있다.
