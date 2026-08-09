# Attention과 transformer

Attention은 query가 key와의 관계를 사용해 value를 가중합하는 연산이다. Transformer는 attention, position-wise feed-forward, residual과 normalization을 반복해 sequence representation을 만든다. 이 문서는 agent나 tool use가 아니라 **모델 내부 계산**을 다룬다.

## 1. Query, key, value

입력 representation `X`에서 projection을 만든다.

```text
Q = XW_Q
K = XW_K
V = XW_V
```

Shape 예:

```text
X: (B, T, D_model)
Q, K: (B, T, D_k)
V: (B, T, D_v)
```

Query는 무엇을 찾는지, key는 어떤 조건으로 비교되는지, value는 선택 뒤 전달할 내용을 표현한다는 직관을 사용할 수 있다. 실제 의미는 학습된다.

## 2. Scaled dot-product attention

```text
scores = QK^T / sqrt(D_k)
weights = softmax(scores + mask)
output = weights V
```

Shape:

```text
scores:  (B, T_query, T_key)
weights: (B, T_query, T_key)
output:  (B, T_query, D_v)
```

`sqrt(D_k)` scaling은 dimension이 커질 때 dot product magnitude가 커져 softmax가 포화되는 문제를 완화한다.

## 3. Mask

### Padding mask

실제 token이 아닌 padding을 key로 선택하지 않게 한다.

### Causal mask

Position `t`가 미래 position을 보지 못하게 한다. Autoregressive next-token training에서 필요하다.

### Task mask

특정 segment·graph 관계만 허용할 수 있다.

Mask polarity와 broadcast axis는 framework마다 다를 수 있다. 작은 score matrix로 허용·차단 position을 검사한다.

## 4. Multi-head attention

여러 projection subspace에서 attention을 병렬 수행한다.

```text
head_i = Attention(XW_Qi, XW_Ki, XW_Vi)
output = Concat(head_1 ... head_h) W_O
```

`D_model`이 head 수로 나누어지는지, head axis 변환과 transpose를 확인한다.

Head마다 독립적인 인간 개념을 배운다고 보장하지 않는다. Attention weight 해석은 제한적이다.

## 5. Self-attention과 cross-attention

### Self-attention

Q, K, V가 같은 sequence에서 나온다. Sequence 내부 position이 상호작용한다.

### Cross-attention

Query는 한 sequence, key/value는 다른 representation에서 나온다. Encoder-decoder 모델에서 decoder가 encoder output을 읽을 수 있다.

## 6. Position

Self-attention 자체는 입력 순열에 대한 순서 정보를 갖지 않는다. Position encoding·embedding 또는 relative position bias가 필요하다.

검토:

- maximum length
- train보다 긴 sequence extrapolation
- padding position
- relative distance
- position interpolation·scaling

## 7. Transformer block

일반적인 구성:

```text
attention
→ residual connection
→ normalization
→ feed-forward network
→ residual connection
→ normalization
```

Pre-norm과 post-norm은 normalization 위치가 다르고 optimization 특성이 다를 수 있다. Diagram과 실제 코드 순서를 일치시킨다.

Feed-forward는 각 position에 같은 MLP를 적용한다. Attention이 position 사이 정보를 섞고, FFN이 position별 representation을 변환한다.

## 8. Encoder, decoder와 decoder-only

### Encoder

모든 입력 position을 양방향으로 볼 수 있다. Classification·representation task에 사용한다.

### Encoder-decoder

Encoder가 입력을 표현하고 decoder가 autoregressive output을 생성하며 cross-attention을 사용한다.

### Decoder-only

Causal self-attention으로 이전 token만 보고 다음 token을 예측한다. Prompt와 generated token이 하나의 sequence state를 이룬다.

Architecture 이름보다 mask와 training objective를 확인한다.

## 9. Complexity

Dense self-attention의 score matrix는 sequence length `T`에 대해 대략 `O(T²)` memory·compute를 사용한다. Model dimension과 batch도 비용에 영향을 준다.

긴 sequence에서는 다음 선택이 있다.

- truncation·chunking
- sparse/local attention
- recurrence·state compression
- retrieval 또는 hierarchical model
- efficient kernel

긴 context 지원 숫자만 보고 실제 memory·latency와 quality를 가정하지 않는다.

## 10. Caching during generation

Autoregressive generation에서 이전 key/value를 cache해 매 step 전체 prefix를 다시 계산하지 않는다.

Cache 계약:

- layer·head·position shape
- model·tokenizer version
- batch reorder
- maximum length
- memory lifetime

Training과 inference code path 차이를 golden fixture로 확인한다.

## 11. Attention weight 해석의 한계

높은 weight가 model decision의 인과적 중요도를 뜻하지 않을 수 있다.

- value projection과 이후 layer가 결과를 바꿈
- 여러 head·layer 상호작용
- alternative attention pattern이 같은 output 가능
- residual path가 attention을 우회

Attention visualization은 diagnostic 중 하나이지 완전한 explanation이 아니다.

## 12. Transformer training objective

### Masked prediction

일부 token을 가리고 원래 token을 예측한다. 양방향 encoder representation에 사용된다.

### Causal next-token prediction

이전 token으로 다음 token likelihood를 최대화한다.

### Sequence-to-sequence

입력 sequence를 조건으로 target sequence를 생성한다.

Objective가 downstream instruction following, factuality 또는 safety를 직접 보장하지 않는다.

## 13. Scaling과 optimization

Transformer 학습은 다음에 민감하다.

- initialization
- normalization 위치
- learning-rate warmup
- sequence length·batch token 수
- gradient clipping
- mixed precision
- data mixture

작은 implementation에서는 shape·mask·tiny-batch overfit을 먼저 검증한다.

## 14. Transformer를 사용하지 않아도 되는 경우

- 작은 tabular dataset
- simple linear·tree baseline이 충분
- latency·memory가 매우 제한적
- sequence 관계가 짧고 명시적 규칙으로 처리 가능
- pretrained model 이득이 검증되지 않음

Architecture 유행이 problem contract를 대체하지 않는다.

## 15. 대표적인 실패

### Mask 방향 반전

Causal model이 미래 token을 보거나 모든 token이 차단된다.

### Softmax axis 오류

Key position이 아니라 head·feature axis에서 normalize한다.

### Position 누락

Token set만 보고 order가 필요한 task를 학습하려 한다.

### Padding loss 포함

길이가 긴 sample과 padding pattern이 metric을 왜곡한다.

### Attention = explanation

Weight heatmap을 model 판단의 완전한 이유로 제시한다.

### Context length = useful memory

지원 가능한 token 수를 모든 position의 동일한 활용 품질로 해석한다.

## 16. 작은 검증 순서

1. 한 batch·한 head·짧은 sequence로 shape를 적는다.
2. QK score를 손계산한다.
3. Mask 전후 score를 확인한다.
4. Softmax가 key axis에서 1이 되는지 본다.
5. 동일 value에서 expected weighted sum을 확인한다.
6. Causal input을 한 token 바꿔 미래 output만 달라지는지 본다.
7. Padding token 변화가 valid output을 바꾸지 않는지 본다.
8. Tiny sequence를 overfit한다.

## 17. 리뷰 질문

- Q·K·V와 score·output의 shape·axis가 명확한가?
- Scale과 softmax axis가 맞는가?
- Padding·causal mask polarity를 fixture로 검사했는가?
- Position encoding과 maximum length가 artifact에 포함되는가?
- Encoder·decoder 구분을 mask와 objective로 설명할 수 있는가?
- Dense attention의 sequence-length 비용을 측정했는가?
- Cache와 non-cache inference가 같은 logits를 만드는가?
- Attention visualization의 한계를 기록하는가?

## 선택 실습

작은 tensor library 또는 PyTorch로 single-head attention을 구현하고 4-token fixture에서 score, mask, weight와 output을 출력한다. 성능 최적화나 대형 transformer 학습은 요구하지 않는다.

## 참고

Transformer 원형의 수식과 구조는 [Attention Is All You Need](https://arxiv.org/abs/1706.03762)에서 확인할 수 있다. 논문의 benchmark 결과를 현재 모든 transformer의 일반적 특성으로 확대하지 않는다.
