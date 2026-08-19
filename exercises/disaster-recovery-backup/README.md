# Disaster Recovery Backup

Database snapshot, release identity, upload files를 checksum manifest와 deterministic archive로 묶고, integrity 검증 뒤 존재하지 않는 target directory에 원자적으로 restore하는 Python CLI다.

## Usage

```sh
python backup.py create examples/source ./backup-state backup-001
python backup.py verify ./backup-state
python backup.py restore ./backup-state ./restored
```

`CURRENT` pointer는 마지막으로 성공적으로 공개된 backup ID를 가리킨다. 특정 backup을 검증하거나 복원하려면 `--backup-id`를 사용한다.

```sh
python backup.py verify ./backup-state --backup-id backup-001
python backup.py restore ./backup-state ./restored-001 --backup-id backup-001
```

## Backup contract

- `database.json`: schema version, latest record timestamp, upload path와 expected checksum
- `release.txt`: restore할 exact release identity
- `uploads.tar.gz`: normalized metadata와 fixed gzip timestamp를 사용하는 deterministic archive
- `manifest.json`: artifact SHA-256와 byte size
- `CURRENT`: successful backup publication pointer

## Restore safety

Restore는 manifest와 모든 artifact checksum을 먼저 검증한다. Archive member는 `uploads/` 아래 regular file만 허용하며 absolute path, `..`, symlink, hard link를 거부한다. Candidate directory 안에서 restored source invariant를 다시 검증한 뒤 target directory를 공개한다. Target은 미리 존재하면 안 된다.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Design decisions

Backup candidate를 완성하기 전에 `CURRENT`를 바꾸지 않는다. Artifact directory를 atomic rename으로 공개한 뒤에만 pointer를 갱신한다. Restore도 동일하게 candidate tree 전체를 검증하고 directory rename으로 전환해 partial restore target이 노출되지 않게 한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Durable checksum and pointer primitives | `backup.py` |
| 2 | Source snapshot and path validation | `backup.py` |
| 3 | Deterministic archive entries | `backup.py` |
| 4 | Staged backup artifact and manifest | `backup.py` |
| 5 | Atomic backup publication | `backup.py` |
| 6 | Safe restore extraction | `backup.py` |
| 7 | Atomic restore publication | `backup.py` |
| 8 | Backup and restore CLI | `backup.py` |
| 9 | Recovery integrity verification | `tests/test_backup.py` |

## Scope and limitations

이 프로젝트는 local directory를 backup target으로 사용한다. Remote upload, encryption, retention, key management, database quiescing은 제공하지 않는다. 실제 database에서는 consistent dump 또는 snapshot을 먼저 생성해 `database.json`과 함께 source directory에 배치해야 한다.
