# Save and replay

## save envelope

- format/schema:
- build/content:
- profile id:
- checksum:
- payload ownership:

## v1 → v2 migration

| v1 | v2 | conversion/default | invariant | failure/rollback |
|---|---|---|---|---|
| bestTimeSeconds |  |  |  |  |
| unlockedSkins |  |  |  |  |
| dashKey/holdToDash |  |  |  |  |
| subtitle |  |  |  |  |

## atomic result/save commit

- idempotency key:
- temp/write/validate/replace:
- previous generation:
- suspend/storage failure:

## replay

- determinism scope:
- initial snapshot/seed:
- command ordering:
- content/build identity:
- checkpoint cadence:
- first divergence report:
- excluded presentation state:
