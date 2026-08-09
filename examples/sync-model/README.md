# 순수 동기화 상태 모델

이 예제는 Expo·SQLite·HTTP package 없이 record sync의 핵심 전이를 Node.js 내장 test runner로 검사한다. 초안의 작은 reference를 보존하면서 permanent failure가 `synced`로 보이던 오류, server version 회귀와 malformed payload 수용 공백을 보정했다.

검사하는 공개 행동:

- request와 업무 command identity를 분리한다.
- 한 번 시도한 command의 id·payload·base version은 바꾸지 않는다.
- active sync 중 새 local edit를 별도 queued command로 보존한다.
- timeout 뒤 같은 command snapshot을 재시도한다.
- stale result, malformed response와 server version 회귀를 거절한다.
- retry, auth block과 permanent failure를 서로 다른 상태로 둔다.
- conflict에서 local·remote를 보존하고 명시적 해결이 새 command를 만든다.

실행:

```sh
node --test examples/sync-model/sync-model.test.mjs
```

## 상태 소유권

```text
local       UI가 읽는 최신 local payload와 revision
remote      마지막으로 검증한 server payload와 단조 증가 version
active      현재 request가 시도하는 불변 command snapshot
retry       UNKNOWN/retryable failure 뒤 같은 snapshot
queued      한 번도 시도하지 않은 최신 local 의도
blocked     재인증 전에는 실행하면 안 되는 기존 snapshot
terminal    자동 retry하지 않는 영구 실패와 기존 snapshot
conflict    local·remote를 함께 보존하는 사용자 결정 상태
```

실제 reference app은 이 의미를 SQLite transaction과 outbox row로 표현한다. 이 예제의 object copy는 database 원자성, multi-process locking, OS file durability나 server-side idempotency를 증명하지 않는다.

## 의도적 제한

- 한 record의 upsert만 모델링한다.
- delete·attachment dependency·queue fairness는 포함하지 않는다.
- server command-result 보존은 fault server가 별도로 검사한다.
- conflict field merge UI와 retry backoff 시간은 다루지 않는다.

구현 모양을 복사하기보다 자신의 repository와 worker가 같은 event history와 관측 결과를 만족하는지 확인한다.
