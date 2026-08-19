# Secret Rotation Store

Versioned secret candidate, consumer validation, atomic current pointer, previous version tracking, protected retirement, HMAC-based audit fingerprint를 제공하는 Python library다. Secret value를 event log나 current metadata에 기록하지 않는다.

## Usage

```python
from pathlib import Path
from secret_store import SecretStore

store = SecretStore(Path("./secret-state"))
accepted = store.install(
    "database_password",
    "v1",
    "replace-with-runtime-input",
    lambda candidate: candidate.stat().st_size >= 16,
)
if accepted:
    print(store.current("database_password"))
    print(store.secret_path("database_password"))
```

`validator`는 candidate path를 받아 실제 consumer의 reload, authentication, parse 같은 확인을 수행해야 한다. `False`를 반환하거나 exception을 발생시키면 candidate file은 삭제되고 current pointer는 유지된다.

## Storage layout

```text
secret-state/
├── audit_hmac_key.bin
├── events.jsonl
└── database_password/
    ├── .rotation.lock
    ├── current.json
    └── versions/
        ├── v1
        └── v2
```

Root와 version directory는 `0700`, secret file, pointer, lock, audit key, event log는 `0600`으로 유지한다.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Design decisions

일반 SHA-256 fingerprint는 secret 후보를 추측할 수 있는 환경에서 offline verification oracle이 될 수 있다. Audit fingerprint는 store별 32-byte HMAC key를 사용하고 일부 digest만 기록한다. Current version은 candidate file 검증 성공 뒤에만 atomic JSON replace로 전환한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Store and audit-key ownership | `secret_store.py` |
| 2 | Name, path, mode, and process-lock invariants | `secret_store.py` |
| 3 | Secret-safe audit fingerprints | `secret_store.py` |
| 4 | Atomic version candidate | `secret_store.py` |
| 5 | Consumer validation and current pointer | `secret_store.py` |
| 6 | Protected retirement lifecycle | `secret_store.py` |
| 7 | Secret lifecycle regression suite | `tests/test_secret_store.py` |

## Scope and limitations

이 library는 local filesystem store다. Secret encryption at rest, remote KMS/HSM, distributed lock, replicated audit log, automatic consumer reload를 제공하지 않는다. Caller는 secret value를 안전한 runtime input에서 전달하고 validator가 실제 consumer boundary를 확인하도록 구성해야 한다.
