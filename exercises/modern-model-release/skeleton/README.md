# Starter candidate

`candidate.py` is intentionally incomplete. Implement these public commands without changing fixtures or the checker:

```text
attention --base PATH --tokens 1,2,3
build --fixtures DIR --output EMPTY_DIR
infer --bundle DIR --input INPUT.json
```

`build` must create every artifact named in [`../contracts/stages.json`](../contracts/stages.json). Use validation for model and epoch selection, leave test for one final evaluation, and copy the exact base/tokenizer identities into the adapter and manifest.

Check progress from the exercise directory:

```sh
python3 tests/check.py --candidate skeleton
```

The starter is expected to fail until all four stages are implemented.
