# Pratt expression parser

`pratt.py`는 정수, prefix `-`, `+ - * /`와 괄호만 가진 작은 expression을 parse합니다. Mica parser 답안이 아니라 binding power와 progress invariant를 관찰하는 예제입니다.

```sh
python3 examples/pratt-parser/pratt.py '1 + 2 * 3 - 4'
python3 examples/pratt-parser/pratt.py --self-test
```

확인할 invariant:

- `parse_expr(min_bp)`는 성공하면 token cursor를 전진시킵니다.
- left binding power가 `min_bp`보다 낮으면 current expression을 반환합니다.
- left-associative operator는 right binding power를 더 크게 둡니다.
- 오류는 현재 token index를 포함하고 무한 재귀나 silent token drop으로 바뀌지 않습니다.
