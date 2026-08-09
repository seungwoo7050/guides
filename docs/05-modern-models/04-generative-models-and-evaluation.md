# 생성 모델과 평가

생성 모델은 입력 조건에서 가능한 output의 분포를 모델링하고 sample을 만든다. 한 개의 정답 label이 없는 경우가 많아 evaluation이 어렵다. Fluency나 그럴듯함을 correctness와 혼동하지 않는다.

## 1. Autoregressive generation

Sequence probability를 token별 조건부 확률로 분해한다.

```text
P(x_1, ..., x_T) = Π_t P(x_t | x_<t)
```

Training은 teacher forcing으로 실제 이전 token을 조건으로 next-token loss를 줄일 수 있다. Inference에서는 model이 생성한 token을 다시 입력하므로 error가 누적될 수 있다.

## 2. Decoding

### Greedy

매 step 가장 높은 probability token을 선택한다. Deterministic하지만 global best sequence와 다를 수 있고 반복·단조로울 수 있다.

### Beam search

여러 후보 prefix를 유지한다. Beam size, length penalty와 종료 조건이 output을 바꾼다.

### Sampling

Probability에서 token을 sample한다.

- temperature
- top-k
- top-p
- repetition constraint
- seed

Decoding configuration은 model artifact와 별도 versioned policy다.

## 3. Likelihood와 generation quality

낮은 validation loss나 perplexity는 data distribution 예측을 나타내지만 다음을 직접 보장하지 않는다.

- 사실성
- instruction 준수
- 유해성 감소
- 장문 일관성
- 특정 업무 utility
- calibration of claims

Task-specific evaluation이 필요하다.

## 4. Diffusion의 개념

Diffusion model은 data에 noise를 점진적으로 추가하는 forward process와 noise를 제거하는 reverse process를 학습한다.

핵심 상태:

- noise schedule
- timestep conditioning
- denoising objective
- sampler와 step 수
- guidance

이 가이드는 diffusion 구현을 필수로 요구하지 않는다. 생성 model family가 objective와 sampling procedure를 분리한다는 점을 이해한다.

## 5. Evaluation taxonomy

### Exact·reference-based

- exact match
- edit distance
- BLEU·ROUGE류

Reference와 표면 일치를 측정한다. 올바른 표현이 여러 개인 task에서 한계가 있다.

### Semantic·model-based

Embedding similarity, classifier 또는 judge model을 사용한다.

위험:

- evaluator bias와 blind spot
- 동일 model family 선호
- prompt·position sensitivity
- judge contamination
- 불명확한 calibration

### Human evaluation

사람이 correctness, relevance, style, harm 등을 평가한다.

필요 요소:

- 명확한 rubric
- blind/randomized presentation
- annotator training
- disagreement
- sample size
- 개인정보·안전

### Task execution

생성 결과가 실제 checker·compiler·simulator·database query 등 외부 verifier를 통과하는지 본다. 가능한 경우 모델 자기평가보다 강한 근거다.

## 6. Evaluation dataset

- 실제 use case를 대표하는 input
- 쉬운 사례와 경계·실패 사례
- 언어·길이·domain slice
- adversarial 또는 stress input
- time-based fresh set
- contamination 가능성 낮은 private set

Public benchmark만으로 제품 품질을 주장하지 않는다.

## 7. Factuality와 grounding

Model이 fluent하게 잘못된 내용을 생성할 수 있다.

평가:

- atomic claim 분해
- source-supported 여부
- citation 정확성
- 답할 수 없는 질문에서 abstention
- time-sensitive fact

Retrieval·tool 사용 시스템은 `agentic-systems`의 범위다. 이 문서는 모델 output 자체의 evaluation contract만 다룬다.

## 8. Structured output

JSON·schema·grammar를 요구할 수 있다.

검사:

- syntax parse
- schema validation
- enum·range
- semantic invariant
- refusal·error representation
- partial output

Valid JSON은 올바른 내용의 증거가 아니다. Domain verifier가 필요하다.

## 9. Safety evaluation

사용 환경에 따라 다음을 검토한다.

- harmful content
- privacy leakage
- memorized data
- bias·stereotype
- misuse enablement
- refusal overreach
- prompt sensitivity

이 브랜치에서는 평가와 문서화의 기준선을 다룬다. 공격 기법과 방어 시스템의 전문 과정은 `cybersecurity`와 후속 AI 보안 프로젝트가 소유한다.

## 10. Diversity와 mode collapse

여러 valid output이 필요한 task에서 같은 output만 반복할 수 있다. Diversity metric은 quality와 trade-off가 있다.

- unique n-gram
- semantic coverage
- pairwise distance
- task-specific option coverage

무작위성만 높여 다양성을 만든 결과가 유용한지 확인한다.

## 11. Human preference

사람 선호 data로 model을 조정하거나 평가할 수 있다.

주의:

- annotator 모집과 문화적 차이
- rubric와 order effect
- verbosity·style 선호가 correctness를 압도
- reward model gaming
- minority preference 소실

Preference는 객관적 truth가 아니라 특정 절차에서 수집된 signal이다.

## 12. Evaluation reproducibility

기록:

```text
model·tokenizer version
decoding configuration
prompt/template version
evaluation dataset version
judge model·prompt version
random seed와 sample 수
human rubric와 annotator process
aggregation code
```

Temperature가 0이어도 serving stack과 model release에 따라 output이 달라질 수 있다.

## 13. Cost·latency·quality

생성 모델은 output length와 decoding step이 비용에 직접 영향을 준다.

- input/output token
- time to first token
- tokens per second
- total latency
- batch behavior
- early stop
- retry·regeneration

Quality metric과 함께 budget을 보고한다.

## 14. Contamination과 benchmark gaming

Public evaluation example이 pretraining·fine-tuning·prompt development에 노출될 수 있다. 높은 benchmark score가 memorization인지 generalization인지 구분하기 어렵다.

- fresh private set
- generated-but-reviewed variants
- temporal cutoff
- near-duplicate search
- hidden executable tests

## 15. 대표적인 실패

### Judge model 단일 점수

Judge의 bias·variance·failure를 검증하지 않고 ground truth처럼 사용한다.

### Fluency = correctness

읽기 좋은 output을 사실적·안전하다고 평가한다.

### JSON validity = task success

Schema만 맞고 semantic invariant가 틀린 output을 통과시킨다.

### Public benchmark 반복

Prompt·decoding을 benchmark에 맞추고 독립 test 없이 일반화 주장한다.

### Decoding policy 미기록

같은 model 이름인데 temperature·top-p·max length가 달라 비교가 불가능하다.

## 16. 리뷰 질문

- Training objective가 평가하려는 behavior와 어떻게 다른가?
- Decoding policy를 model과 별도로 versioning하는가?
- Reference, model judge, human, executable evaluation의 역할을 구분하는가?
- Judge 자체를 calibration·agreement로 검증했는가?
- Structured output에 semantic verifier가 있는가?
- Fresh·private·slice evaluation이 있는가?
- Factuality·abstention·safety를 사용 환경에 맞게 검사하는가?
- Quality와 latency·cost·output length를 함께 보고하는가?
- Public benchmark contamination 가능성을 기록하는가?

## 선택 capstone 연결

[작은 신경망 capstone](../07-capstones/02-small-neural-model.md)을 sequence task로 확장한다면 next-token loss와 생성 평가를 분리한다. 필수 누적 실습은 tabular 분류 문제이므로 생성 모델 구현을 요구하지 않는다.
