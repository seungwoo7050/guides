# Bytecode verifier와 stack VM

`vm.py`는 `CONST`, `ADD`, `MUL`, `RETURN`만 가진 작은 typed stack machine입니다. 작은 expression compiler와 deterministic disassembler를 포함하지만 Mica source compiler는 포함하지 않습니다.

```sh
python3 examples/bytecode-vm/vm.py
python3 examples/bytecode-vm/vm.py --self-test
```

검증 순서:

```text
instruction shape와 constant index
→ abstract stack type 전이
→ return contract
→ verified program만 실행
```

Known-bad program은 실행 중 Python `IndexError`가 나기 전에 verifier의 `VerificationError`로 거부됩니다. Mica VM에서는 이 경계를 `MICA500x` diagnostic으로 바꿉니다.

동일 expression을 독립 tree evaluator와 VM에서 비교하고 i64 overflow가 둘 다 `MICA4002`가 되는지 확인합니다. 이 작은 linear verifier는 branch merge나 call frame을 검증하지 않으므로 capstone bytecode verifier의 대체물이 아닙니다.
