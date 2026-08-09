# Mica Python skeleton

이 디렉터리는 답안이 아니라 phase boundary를 시작하기 위한 package입니다.

```sh
PYTHONPATH=src python3 -m mica check ../fixtures/valid/literal-main.mica --json
```

초기 상태는 종료 코드 `2`와 `MICA0000`으로 실패합니다. `driver.py`의 command adapter를 유지하면서 내부 phase를 순서대로 구현합니다.

권장 순서:

```text
source.py / diagnostic.py
→ token.py / lexer.py
→ syntax.py / parser.py
→ symbol.py / resolver.py
→ types.py / typecheck.py / flow.py
→ interpreter.py
→ 선택 VM/backend/tooling
```

`SourceText`, `Span`, `Diagnostic`의 public field를 바꾸면 JSON adapter와 fixture를 함께 갱신합니다. Host traceback을 사용자 오류로 사용하지 않습니다.
