# update state model

`model.py`는 두 image slot의 candidate·trial·confirmed·revert 상태를 단순화합니다.

## 실행

```sh
python3 model.py fixtures/normal-confirm.json --check
python3 model.py fixtures/invalid-candidate.json --check
python3 model.py fixtures/trial-reset-revert.json --check
python3 model.py fixtures/self-test-fail.json --check
python3 model.py fixtures/both-invalid-recovery.json --check
python3 model.py fixtures/confirm-power-loss-cuts.json --check --trace
python3 model.py fixtures/revert-power-loss-cuts.json --check --trace
```

핵심 사건:

- `DOWNLOAD`: inactive slot에 candidate를 둡니다.
- `MARK_PENDING`: validity와 compatibility를 확인하고 다음 boot trial을 요청합니다.
- `RESET`: pending candidate를 trial로 선택하거나 unconfirmed attempt를 증가시키고 필요하면 revert합니다.
- `BOOT_OK`와 `SELF_TEST_PASS`: 서로 독립적인 ephemeral confirmation gate입니다.
- `CONFIRM`: 두 gate가 모두 관찰된 trial image만 durable confirmed로 만듭니다.
- `SELF_TEST_FAIL`: previous image로 즉시 revert합니다.
- `POWER_LOSS`: confirm/revert metadata commit 직전·직후 cut을 주입합니다.
- `COMMIT_SCHEMA`: data schema가 binary rollback과 호환되는지 드러냅니다.
- `CORRUPT`: fixture에서 slot validation failure를 주입합니다.

metadata commit은 atomic record 선택으로 추상화합니다. 이 모델은 image bytes,
signature, 실제 flash program unit, trailer와 swap algorithm을 구현하지 않습니다.
MCUboot나 다른 bootloader의 실제 보장은 사용하는 mode와 release의 공식 설계를
확인해야 합니다.
