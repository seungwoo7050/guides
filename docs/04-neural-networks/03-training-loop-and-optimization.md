# Training loop와 최적화

Training loop는 `forward → backward → step` 세 줄이 아니다. Data 순서, mode, loss reduction, gradient, checkpoint와 validation을 연결하는 상태 기계다.

## 1. 기본 상태 전이

```text
initialize model·optimizer
for epoch:
    set train mode
    for batch:
        load and validate batch
        zero gradients
        forward
        compute loss
        backward
        optional gradient transform
        optimizer step
        record trace
    set eval mode
    evaluate validation without gradient
    update best checkpoint or stopping state
```

각 단계가 어떤 state를 읽고 쓰는지 명시한다.

## 2. Data loader

Data loader는 다음을 결정한다.

- sample order
- batch composition
- shuffle seed
- drop-last 여부
- class/group sampling
- augmentation
- worker process와 prefetch
- collate와 padding

같은 dataset과 model도 batch order와 sampling에 따라 다른 결과를 낼 수 있다.

## 3. Batch size

영향:

- gradient noise
- memory
- throughput
- normalization behavior
- update 횟수
- learning rate와 loss scale

Batch size를 바꾸면 한 epoch의 step 수와 total optimization budget이 달라진다. Epoch 수만 같게 두고 공정한 비교라 말하지 않는다.

## 4. Optimizer

### SGD

현재 gradient 방향으로 update한다. Momentum은 이전 update 방향을 누적한다.

### Adaptive optimizer

Parameter별 gradient 통계로 update scale을 조절한다. 초기 학습이 쉬울 수 있지만 weight decay 의미와 generalization을 별도 검토한다.

Optimizer 이름보다 기록할 것:

- hyperparameter
- parameter group
- weight decay 적용 제외 대상
- state size
- checkpoint 포함 여부

## 5. Learning-rate schedule

- constant
- step·exponential decay
- cosine decay
- warmup
- plateau 기반

Schedule은 total step과 연결된다. Resume할 때 scheduler state를 복원하지 않으면 learning rate가 달라진다.

## 6. Gradient clipping

Gradient norm 또는 value를 제한한다. Exploding gradient의 완화 수단이지 원인 분석 대체가 아니다.

기록:

- clip 전 norm
- clip threshold
- clip 발생 비율
- optimizer step 전 적용 위치

항상 clip된다면 learning rate, loss scale, sequence length와 architecture를 조사한다.

## 7. Mixed precision

낮은 precision으로 연산해 memory와 throughput을 개선할 수 있다.

위험:

- underflow·overflow
- 일부 operation의 precision 요구
- loss scaling state
- CPU·accelerator 차이

정확한 float32 CPU 기준선을 먼저 만든 뒤 적용한다. 필수 가이드 실습은 mixed precision을 요구하지 않는다.

## 8. Train과 evaluation mode

Evaluation procedure:

```text
model.eval()
no gradient
fixed preprocessing
no train augmentation
all predictions accumulated
metric computed once from complete set
```

Batch별 metric 평균은 전체 confusion matrix에서 계산한 metric과 다를 수 있다. 특히 batch 크기와 class 비율이 다를 때 주의한다.

## 9. Checkpoint

최소 state:

- model parameter
- optimizer state
- scheduler state
- current step·epoch
- random generator state 가능 범위
- best metric과 early-stopping state
- configuration·code·dataset reference

Inference artifact와 training resume checkpoint는 목적이 다르다. Resume state에는 optimizer가 필요하지만 release artifact에는 필요하지 않을 수 있다.

## 10. Resume semantics

“같은 위치에서 이어간다”는 다음을 의미한다.

- 같은 model·optimizer·scheduler state
- 같은 data order 또는 허용된 차이
- 같은 mixed-precision state
- 같은 step count와 logging
- checkpoint 직전/직후 update 중복 없음

중간 batch에서 crash한 경우 exactly-once training step을 보장하기 어렵다. 허용 범위를 기록한다.

## 11. Early stopping

Validation metric과 checkpoint selection을 연결한다.

- primary metric
- evaluation interval
- patience
- minimum delta
- tie-break
- warmup period
- best와 last 저장

Test metric으로 early stopping하지 않는다.

## 12. Reproducibility

Seed를 고정하고 deterministic option을 사용할 수 있지만 다음은 남는다.

- library release 차이
- device·kernel 차이
- parallel reduction 순서
- worker scheduling
- nondeterministic operation

목표는 모든 환경에서 bitwise 동일함이 아니라, 입력·환경·randomness를 기록하고 허용 오차 안에서 결과와 결론을 재현하는 것이다.

## 13. Logging

최소 trace:

```text
step·epoch
learning rate
train loss
validation primary metric
secondary metric
gradient norm
throughput·latency
checkpoint event
NaN·skip·clip event
```

너무 자주 large tensor를 logging하면 학습 성능과 storage에 영향을 준다. 개인정보와 민감 input을 log하지 않는다.

## 14. Training budget

후보 model을 비교할 때 budget을 정의한다.

- total step
- processed sample/token
- wall-clock
- accelerator hour
- energy·cost 필요 시
- hyperparameter trial 수

한 model은 충분히 학습하고 다른 model은 조기 종료한 비교를 피한다. 동일 budget이 항상 공정한 것도 아니므로 선택 근거를 기록한다.

## 15. Distributed training 경계

여러 device·node 학습은 다음 추가 문제를 가진다.

- data shard와 sampler
- gradient synchronization
- global batch size
- failure·restart
- checkpoint aggregation
- network와 storage bottleneck

이 브랜치는 개념만 인지하고 단일 process CPU training을 필수 기준으로 둔다. 분산 학습 구현은 후속 `ml-systems`의 범위다.

## 16. 평가 누출

Training loop 안에서 다음을 하지 않는다.

- validation batch로 gradient update
- validation statistics로 normalization update
- test metric을 매 epoch 확인
- validation error example을 train data에 즉시 추가하고 같은 score 보고
- best seed만 남기기

## 17. 대표적인 실패

### zero-grad 위치 오류

Gradient accumulation을 의도하지 않았는데 여러 batch가 누적된다.

### Batch metric 평균

각 batch F1 평균을 전체 F1로 보고한다.

### Best checkpoint 미복원

Early stopping은 best를 기록했지만 마지막 model을 평가·배포한다.

### Resume 후 schedule reset

Optimizer는 복원했지만 scheduler·step가 초기화된다.

### Train augmentation in validation

Validation 결과가 random transform에 따라 흔들린다.

## 18. 리뷰 질문

- Data order·sampling·augmentation state가 기록되는가?
- Loss reduction과 effective batch size가 명확한가?
- Gradient zeroing·accumulation·clipping 순서가 맞는가?
- Evaluation이 train mode와 완전히 분리되는가?
- Metric을 complete dataset에서 계산하는가?
- Best·last·resume·release checkpoint를 구분하는가?
- Resume 뒤 optimizer·scheduler·step가 일관적인가?
- 비교 model의 compute budget을 설명할 수 있는가?

## 실습 연결

누적 실습 6단계는 단일 CPU process를 기준으로 한다. `neural-experiment.json`에는 batch size, step 수, optimizer, learning-rate schedule, best checkpoint 기준과 seed별 결과를 기록한다.
