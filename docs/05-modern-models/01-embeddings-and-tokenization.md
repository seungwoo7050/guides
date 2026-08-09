# Embedding과 tokenization

현대 모델은 문자열·category·item ID 같은 이산 객체를 직접 계산하지 않는다. Token 또는 ID로 바꾸고, 학습 가능한 dense vector인 embedding으로 변환한다. **Tokenizer와 vocabulary는 model 앞의 전처리가 아니라 model 의미와 호환성을 정하는 artifact**다.

## 1. Discrete ID와 embedding

Vocabulary 크기가 `V`, embedding dimension이 `D`라면 weight는 다음 shape다.

```text
E: (V, D)
input_ids: (B, T)
output: (B, T, D)
```

각 ID는 `E`의 한 row를 조회한다. Backward에서 사용된 row 중심으로 gradient가 계산된다.

Embedding distance가 의미 있으려면 학습 objective와 data가 그 관계를 유도해야 한다. Dense vector라는 이유만으로 semantic truth를 담는 것은 아니다.

## 2. Vocabulary contract

다음을 versioning한다.

- token → ID mapping
- special token ID
- normalization
- unknown 처리
- maximum length
- truncation 방향
- padding 방향과 ID
- vocabulary 생성 corpus·algorithm

Model weight만 바꾸지 않아도 tokenizer mapping이 달라지면 prediction이 완전히 달라진다.

## 3. Word-level tokenization

공백·문장부호 기준으로 word를 나눈다.

장점:

- 사람이 읽기 쉬움
- sequence가 비교적 짧음

한계:

- vocabulary가 큼
- 오탈자·형태 변화·새 단어 OOV
- 언어별 word boundary 차이

## 4. Character·byte tokenization

작은 vocabulary로 모든 문자열을 표현할 수 있다.

비용:

- sequence가 길어짐
- 긴 dependency 학습 부담
- 같은 의미가 많은 step으로 분산

Byte는 encoding coverage가 좋지만 user-visible character와 경계가 다를 수 있다.

## 5. Subword tokenization

빈번한 조각은 하나의 token, 드문 단어는 여러 조각으로 나눈다.

목표:

- 제한된 vocabulary
- OOV 감소
- word·character 장점 절충

주의:

- tokenizer training corpus의 편향
- 언어·script별 token 수 차이
- whitespace·normalization 정책
- 동일 문자열의 context·prefix 표현
- version 변경 시 model incompatibility

Algorithm 이름보다 실제 encode/decode fixture를 고정한다.

## 6. Normalization

Tokenizer 전에 다음 변환이 있을 수 있다.

- Unicode normalization
- case folding
- whitespace 처리
- accent 제거
- control character
- punctuation mapping

Normalization은 정보를 제거하거나 서로 다른 문자열을 합칠 수 있다. 식별자, 코드, 이름과 다국어 텍스트에서는 영향이 크다.

## 7. Special token

- padding
- unknown
- begin/end
- separator
- mask
- task-specific control

각 token의 ID와 loss 포함 여부를 고정한다. Padding token이 attention이나 loss에 들어가면 length pattern을 학습하거나 metric이 왜곡될 수 있다.

## 8. Truncation과 chunking

Maximum sequence length를 넘는 입력을 처리한다.

### Truncation

앞·뒤·중간 중 무엇을 버리는지 task에 따라 다르다. 중요한 정보가 체계적으로 잘릴 수 있다.

### Chunking

긴 문서를 여러 window로 나눈다.

검토:

- overlap
- 원본 document group split
- chunk prediction aggregation
- label이 document·chunk 중 어디에 속하는가
- duplicate context와 evaluation contamination

Chunk를 독립 sample로 random split하지 않는다.

## 9. Positional information

Embedding lookup만으로는 token 순서를 표현하지 못한다. Position embedding 또는 relative position mechanism을 추가한다.

Absolute position table은 maximum length와 호환성이 있고, relative scheme은 distance 관계를 다른 방식으로 표현한다. Position 처리도 model artifact 일부다.

## 10. Pretrained embedding

외부 corpus에서 학습한 representation을 사용할 수 있다.

검토:

- corpus·language·domain
- vocabulary coverage
- license와 배포 조건
- sensitive data·memorization 위험
- frozen 또는 fine-tune
- downstream baseline 대비 이득

Pretrained라는 이유로 현재 problem에 적합한 것은 아니다.

## 11. Similarity

Embedding에서 cosine similarity나 dot product를 사용할 수 있다.

- normalization 여부
- vector norm의 의미
- index와 model version 호환
- threshold calibration
- hard negative

가까운 vector가 업무상 같은 범주나 관련성을 의미하는지 별도 평가한다.

## 12. Contrastive learning

Positive pair는 가깝게, negative pair는 멀게 학습한다.

성공은 pair 생성 계약에 달려 있다.

- 무엇이 같은 의미인가
- false negative 가능성
- easy·hard negative
- batch composition
- temperature
- collapse 방지

Dataset 생성 과정이 model objective 일부가 된다.

## 13. Embedding evaluation

### Intrinsic

Similarity·analogy·clustering 같은 representation 자체 검사. 실제 downstream 품질과 다를 수 있다.

### Downstream

분류·검색·ranking 등 실제 task에서 평가한다.

### Slice

언어, 길이, script, rare token, domain별 coverage와 품질을 본다.

### Stability

Model/tokenizer version 변화 시 nearest neighbor와 threshold가 얼마나 달라지는지 본다.

## 14. Vocabulary와 privacy

Vocabulary에 rare 이름·식별 문자열이 직접 포함될 수 있다. Model embedding도 민감 pattern을 담을 수 있다.

- 최소 빈도
- 개인정보 filtering
- tokenizer artifact 접근 제어
- deletion과 retraining 정책
- 외부 공개 여부

## 15. 대표적인 실패

### Tokenizer mismatch

Train tokenizer와 serving tokenizer의 mapping이 다르지만 model shape는 같아 조용히 잘못된다.

### Decode round-trip을 의미 보존으로 오인

문자열이 복원돼도 normalization·truncation과 model input 의미가 같다는 보장은 없다.

### Chunk leakage

같은 문서의 chunk가 train과 test에 들어간다.

### Embedding plot storytelling

2D projection에서 보이는 군집을 의미 구조로 확정한다.

### Language cost 무시

같은 내용이 언어별로 token 수와 truncation 확률이 크게 다르다.

## 16. 리뷰 질문

- Tokenizer·vocabulary·special ID를 model과 함께 versioning하는가?
- Normalization이 제거하는 정보를 알고 있는가?
- Unknown·padding·truncation을 운영 입력에서 검증하는가?
- Chunk는 원본 document group을 보존하는가?
- Embedding distance가 실제 downstream 목적과 연결되는가?
- 언어·길이·rare token slice를 평가하는가?
- Pretrained corpus·license·privacy 한계를 기록하는가?
- Model/tokenizer 업데이트가 index와 threshold에 미치는 영향을 관리하는가?

## 선택 실습

작은 문자열 집합에 character, word, subword-like 규칙을 각각 적용해 sequence length와 unknown rate를 비교한다. 현대 tokenizer library를 구현하는 것이 아니라 normalization·ID·padding·truncation 계약을 fixture로 고정하는 것이 목표다.
