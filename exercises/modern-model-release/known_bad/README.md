# Known-bad candidates

각 후보는 reference에 한 가지 오류를 의도적으로 주입한다. 회귀 검사기는 다음 공개 실패를 각각 거부해야 한다.

| 후보 | 관찰 가능한 위반 |
|---|---|
| `causal-mask-reversal` | query가 미래 key를 본다 |
| `wrong-softmax-axis` | query별 attention 합이 1이 아니다 |
| `tokenizer-base-mismatch` | bundle tokenizer version이 base 계약과 다르다 |
| `test-based-selection` | model/epoch 선택 split이 test다 |
| `base-identity-missing` | adapter가 결합될 base ID·version·digest를 갖지 않는다 |
| `invalid-input-coercion` | 잘못된 type·unknown token을 조용히 변환한다 |

이들은 정답 형식 예제가 아니라 checker의 negative control이다.
