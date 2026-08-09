# Sequential specification

## State

```text
kv: map<string, value>
sessions: map<client_id, {last_sequence, fingerprint, result}>
```

## Operation

### put

`TODO`: 입력, 상태 전이와 결과를 적습니다.

### get

`TODO`: read protocol과 결과를 적습니다.

### compare_and_set

`TODO`: 성공·mismatch의 상태 전이를 적습니다.

### duplicate request

`TODO`: 동일 sequence·동일 fingerprint와 충돌 fingerprint의 결과를 적습니다.

다음 status를 빠짐없이 정의합니다.

```text
OK, NOT_FOUND, MISMATCH, NOT_LEADER,
CONFLICT, STALE_SEQUENCE, SEQUENCE_GAP
```

`fingerprint`는 canonical JSON command의 SHA-256이며 client ID·sequence는 `ClientRequest`만 소유합니다. replicated log는 request 전체를 저장합니다.
