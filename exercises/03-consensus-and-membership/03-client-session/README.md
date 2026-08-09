# Client session과 snapshot 실습

## 목표

client가 성공 응답을 잃고 같은 명령을 재시도해도 state machine effect가 한 번만 남도록 session state를 설계합니다. log compaction과 snapshot이 deduplication 정보를 제거하지 않도록 recovery 계약을 검토합니다.

## 입력

[`sessions.json`](sessions.json)은 한 client의 순차 요청, response loss, crash와 snapshot 설치를 포함합니다. `safe-snapshot`은 session metadata를 포함하고, `unsafe-snapshot`은 key-value state만 저장합니다.

## 작업

각 event 뒤에 다음 상태를 기록합니다.

```text
commit_index
last_applied
kv value
session[client_id] = {last_sequence, last_result}
response emitted
```

다음 질문에 답합니다.

1. 같은 `(client_id, sequence)`가 다시 오면 log에 새 entry를 넣어야 합니까?
2. 이미 apply됐지만 response가 사라진 요청은 어떤 result를 반환합니까?
3. `sequence`가 하나 이상 건너뛴 요청을 허용할지, 거절할지, 보류할지 어떤 API 계약을 선택합니까?
4. snapshot에 session table의 어느 범위가 들어가야 합니까?
5. session GC가 안전해지려면 client acknowledgement 또는 epoch에 어떤 가정이 필요합니까?

## 보존할 불변식

- 한 client sequence의 command effect는 최대 한 번 apply됩니다.
- 동일 sequence와 다른 command fingerprint는 충돌로 거절됩니다.
- snapshot 설치 뒤에도 snapshot index 이하에서 완료된 요청의 중복 여부를 판정할 수 있습니다.
- restart 뒤 응답 결과가 command effect와 모순되지 않습니다.
- session metadata의 적용 순서는 state machine command와 동일한 commit order를 따릅니다.

## 대표 오답

- deduplication table을 leader의 메모리에만 둡니다.
- snapshot에는 사용자 key-value state만 넣고 session table을 제외합니다.
- duplicate request에 현재 key 값을 다시 계산해 과거 결과처럼 반환합니다.
- `(client_id, sequence)`만 비교하고 command fingerprint 충돌을 확인하지 않습니다.
- 시간만 기준으로 session을 삭제하면서 오래된 retry가 다시 도착하지 않는다는 근거를 두지 않습니다.

## 완료 조건

- `safe-snapshot`의 모든 event 뒤 상태표를 제출합니다.
- `unsafe-snapshot`에서 effect가 두 번 생기는 최소 trace를 표시합니다.
- 자신의 retry API에서 duplicate, stale, next, gap request의 결과를 표로 정의합니다.
- snapshot manifest에 포함할 client session metadata와 restore 검사를 작성합니다.

직접 추적한 뒤 [`reference.md`](reference.md)의 해설과 [`expected.json`](expected.json)의 관측 결과를 비교합니다.
