# Schema evolution 판정

old writer와 new reader, new writer와 old reader의 호환성을 구분하는 작은 모델을 구현한다.

문서: [`schema evolution과 호환성`](../../../docs/01-contracts-and-records/02-schema-evolution-and-compatibility.md)

## 입력 계약

schema는 다음 형태다.

```python
{
    "order_id": {"type": "string", "required": True},
    "amount": {"type": "int", "required": True},
    "channel": {"type": "string", "required": False, "default": None},
}
```

`reader_accepts(writer, reader)`는 reader가 writer record를 읽을 수 있으면 `True`, 아니면 `False`를 반환한다.

축소 모델이므로 다음만 지원한다.

- 같은 type
- `int -> long -> double` widening
- writer에 없는 reader field는 optional이거나 명시적 default가 있을 때 허용
- rename은 자동 추론하지 않음

## 완료 기준

- 새 optional field 추가는 old data를 읽는 new reader에서 허용된다.
- default 없는 required field 추가는 거부된다.
- `int` writer를 `long` reader가 읽을 수 있다.
- `long` writer를 `int` reader가 읽는 narrowing은 거부된다.
- old/new 방향을 바꿔 forward compatibility를 별도로 판정할 수 있다.

## 자기 설명

1. 이 모델이 physical schema만 판정하고 semantic change는 판정하지 못하는 이유는 무엇인가?
2. `default="KR"`가 표현상 호환돼도 업무상 위험할 수 있는 이유는 무엇인가?
3. 실제 Avro/Protobuf/JSON Schema에서는 왜 공식 구현으로 다시 검사해야 하는가?

## 검증

```bash
./scripts/new-workspace.sh exercises/01-contracts-and-records/01-schema-evolution
./scripts/check-workspace.sh exercises/01-contracts-and-records/01-schema-evolution
```

초기 skeleton은 `GUIDE_SEMANTIC:schema-evolution`으로 실패한다.
