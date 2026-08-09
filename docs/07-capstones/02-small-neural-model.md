# Capstone B: 작은 신경망과 학습 진단

이 capstone은 신경망 API를 호출하는 능력보다 **tensor shape, gradient, training state와 generalization evidence를 연결하는 능력**을 검증한다. 같은 합성 churn 문제 또는 별도의 작은 분류 dataset을 사용할 수 있다.

고전적 baseline을 먼저 만든 뒤 진행한다. 신경망이 baseline을 이기지 못해도 학습 계약과 실패 분석이 정확하면 capstone은 유효하다.

## 1. 목표

작은 multi-layer perceptron을 학습하고 다음을 설명한다.

```text
input tensor와 feature order
→ affine layer와 activation
→ logit·probability
→ loss
→ backward gradient
→ optimizer update
→ validation과 checkpoint 선택
```

## 2. 제약

- CPU에서 짧게 실행 가능해야 한다.
- hidden layer는 1~3개로 제한한다.
- parameter 수와 input dimension을 보고한다.
- train·validation·test 경계는 Capstone A와 동일하게 유지한다.
- training trace를 구조화된 JSON으로 남긴다.
- seed 하나의 최고 점수만으로 결론내리지 않는다.
- 고전적 baseline과 같은 metric·threshold 계약에서 비교한다.

PyTorch를 사용할 수 있으나 필수는 아니다. NumPy 또는 작은 직접 구현도 가능하다. Framework를 사용한다면 자동 미분과 optimizer가 어떤 state를 소유하는지 설명한다.

## 3. 구현 전 손검사

작은 fixture에서 다음을 확인한다.

- batch·feature·hidden·output shape
- binary classification의 logit shape
- loss가 scalar가 되는 reduction
- parameter와 gradient shape 일치
- finite difference와 analytic gradient의 근사 일치

[`examples/gradient_check.py`](../../examples/gradient_check.py)를 참고할 수 있다.

## 4. training loop 계약

Pseudo-code:

```text
initialize model and optimizer
for epoch:
    set training mode
    for batch from training split:
        clear gradients
        forward
        compute loss
        backward
        inspect or clip gradients when configured
        optimizer step

    set evaluation mode
    compute validation metrics without update
    record trace
    update checkpoint according to fixed rule
load selected checkpoint
run final test once
```

명시할 state:

- model parameter
- optimizer momentum·adaptive state
- random generator
- batch order
- training/evaluation mode
- checkpoint와 best validation value
- early stopping counter

## 5. 최소 실험

### A. 의도적으로 overfit하는 작은 batch

아주 작은 training sample에서 loss가 충분히 내려가는지 확인한다. 내려가지 않으면 model capacity보다 구현·data·loss bug를 먼저 의심한다.

### B. learning rate 비교

최소 세 범위를 비교한다.

- 너무 작아 거의 학습하지 않음
- 안정적으로 감소
- 너무 커서 진동·발산

절대 값은 model과 scaling에 따라 다르다. Curve와 gradient norm으로 해석한다.

### C. regularization 또는 capacity 비교

한 변수만 바꾼다.

- hidden width
- weight decay
- dropout
- early stopping

Training loss와 validation gap을 함께 본다.

### D. seed 반복

선택한 config를 여러 seed로 실행해 variation을 기록한다. 평균, 범위와 실패 run을 보고한다.

## 6. 기록할 trace

```json
{
  "run_id": "mlp-001",
  "seed": 7050,
  "parameter_count": 321,
  "optimizer": {"name": "adam", "learning_rate": 0.001},
  "checkpoint_rule": "minimum validation log loss",
  "epochs": [
    {
      "epoch": 1,
      "train_loss": 0.67,
      "validation_loss": 0.65,
      "gradient_norm": 0.42,
      "learning_rate": 0.001
    }
  ],
  "selected_epoch": 7,
  "test": {},
  "diagnosis": []
}
```

실제 값이 아니라 구조 예시다.

## 7. 실패 주입

다음 중 최소 세 개를 의도적으로 만들고 진단한다.

- label과 output shape mismatch
- `sigmoid`와 binary cross-entropy의 중복 적용
- evaluation 중 dropout 활성
- gradient zeroing 누락
- learning rate 과대
- input scaling 누락
- train/validation mode 혼동
- batch에 한 class만 반복
- NaN 입력
- checkpoint를 마지막 epoch로 잘못 선택

각 실패에 대해 다음을 기록한다.

```text
증상
가능한 가설
확인한 tensor·metric·trace
원인
수정
수정 뒤 검사
```

## 8. 비교와 결론

고전적 baseline과 비교할 때 다음을 함께 본다.

- validation·test metric
- calibration
- seed variance
- training·inference cost
- artifact 크기
- preprocessing 복잡도
- 오류 slice
- 해석과 운영 난이도

신경망이 점수에서 조금 앞서도 비용과 안정성 때문에 선택하지 않을 수 있다. 선택하지 않은 결론도 근거가 있으면 유효하다.

## 9. 완료 기준

- [ ] shape table과 forward path를 설명한다.
- [ ] 작은 batch overfit 검사를 수행했다.
- [ ] gradient 또는 parameter update가 실제 발생함을 확인했다.
- [ ] training·evaluation mode를 분리했다.
- [ ] checkpoint 선택에 test를 사용하지 않았다.
- [ ] learning rate와 regularization 실패를 trace로 분석했다.
- [ ] 여러 seed의 변동을 기록했다.
- [ ] 고전적 baseline과 같은 평가 계약에서 비교했다.
- [ ] artifact·input schema·preprocessing을 함께 version했다.

## 10. 범위 밖

- 대규모 hyperparameter search
- multi-GPU·distributed training
- custom CUDA kernel
- foundation model pretraining
- production inference cluster

이들은 작은 training loop의 상태와 평가 계약을 이해한 뒤 후속 프로젝트에서 다룬다.
