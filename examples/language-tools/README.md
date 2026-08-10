# Language tools 관찰 예제

`tools.py`는 작은 Mica token formatter, semantic-model 기반 linter와 version-aware document store를 제공합니다.

```sh
python3 examples/language-tools/tools.py --self-test
```

Formatter는 comment를 token으로 소유하고 exact output·idempotence·token projection을 검사합니다. Linter는 unused local, unreachable statement, shadowing을 stable code로 정렬합니다. Document store는 UTF-16 position을 계산하고 현재 version과 다른 결과를 폐기합니다.

이는 전체 parser/checker나 JSON-RPC server가 아닙니다. 실제 capstone 도구에서는 parse/check round-trip, framing, cancellation, large-file budget과 false positive/negative를 별도로 검토합니다.
