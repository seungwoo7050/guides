# Semantic model 관찰 예제

이 예제는 parser와 무관한 작은 scope/type/flow 모델입니다. 같은 이름의 shadowing이 다른 `SymbolId`를 만들고 scope exit 뒤 바깥 binding이 복원되는지, type rule이 명시적인지, definite-assignment join이 교집합인지 관찰합니다.

```sh
python3 examples/semantic-model/semantic_model.py --self-test
python3 examples/semantic-model/semantic_model.py
```

전체 Mica resolver/type checker 답안은 아닙니다. declaration order, overload, generic type이나 soundness proof를 제공하지 않으며 Exercise 03에서 언어별 정책을 명시해야 합니다.
