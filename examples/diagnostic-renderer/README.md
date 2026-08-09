# UTF-8 diagnostic renderer

`render.py`는 core span을 UTF-8 byte offset으로 보존하면서 한 줄의 line/column과 underline을 계산합니다.

```sh
python3 examples/diagnostic-renderer/render.py --self-test
python3 examples/diagnostic-renderer/render.py
```

관찰할 점:

- `🙂`는 UTF-8에서 4 byte지만 source column은 code point 하나입니다.
- Span은 `[start, end)`입니다.
- Byte offset이 code point 중간을 가리키면 renderer가 internal input error로 거부합니다.
- LSP의 UTF-16 position 변환은 이 core renderer의 책임이 아닙니다.
