# 값 객체 계약 실습

금액의 값과 통화를 따로 전달하면 음수, 통화 불일치와 오버플로를 호출할 때마다 다시 확인해야 합니다. 생성과 연산 규칙을 `Money` 안에 모아 잘못된 상태가 만들어지지 않게 합니다.

## 목표

금액과 통화를 하나의 불변 값으로 묶고, 생성·덧셈·뺄셈의 모든 실패를 객체 경계에서 일관되게 거절합니다.

## 구현할 계약

정본 skeleton을 `.workspace/value-object-contract`로 복사한 뒤 학습자 복사본의 `Money`를 수정합니다.

- 최소 단위 금액은 0 이상입니다.
- 통화는 `null`일 수 없습니다.
- 서로 다른 통화는 더하거나 뺄 수 없습니다.
- 덧셈의 정수 오버플로를 예외로 드러냅니다.
- 뺄셈 결과가 음수이면 상태를 만들지 않고 거절합니다.
- 성공한 연산은 원래 값을 변경하지 않고 새 값을 반환합니다.

```sh
./scripts/new-workspace.sh exercises/01-language-and-domain/02-value-object-contract
./scripts/check-workspace.sh exercises/01-language-and-domain/02-value-object-contract
```

완성 예시는 다음 명령으로 확인합니다.

```sh
./mvnw -pl :value-object-contract-reference -am test
```

테스트를 삭제하거나 예외 범위를 넓혀 통과시키지 않습니다. 생성 실패, 통화 불일치, 오버플로와 음수 결과가 각각 어느 경계에서 거절되는지 설명할 수 있어야 합니다.

## 완료 기준

- [ ] 음수 금액과 `null` 통화는 유효한 `Money`가 만들어지기 전에 거절됩니다.
- [ ] `null` 피연산자와 다른 통화의 연산은 원래 값을 바꾸지 않고 각각 명확히 실패합니다.
- [ ] 덧셈 오버플로와 음수 뺄셈 결과를 감지하면서 성공 연산은 새 값을 반환합니다.

## 자기 설명

- 통화 검사를 호출자마다 반복하는 것보다 `Money` 내부에 두는 편이 안전한 이유는 무엇인가요?
- 오버플로와 잔액 부족을 같은 예외로 뭉개지 않으면 어떤 진단 근거를 얻나요?

## 검증

```sh
./scripts/check-workspace.sh exercises/01-language-and-domain/02-value-object-contract
./scripts/mvn-guide.sh -pl :value-object-contract-reference -am test
```
