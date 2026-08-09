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
