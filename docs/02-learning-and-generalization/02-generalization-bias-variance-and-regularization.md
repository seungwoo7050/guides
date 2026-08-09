# Generalization, bias·variance와 regularization

모델 개발의 핵심은 train data를 잘 맞추는 것이 아니라 **학습에 사용하지 않은 미래 입력에서 필요한 품질을 유지하는 것**이다. Generalization은 모델 크기 하나로 결정되지 않고 data, model family, optimization, selection과 배포 환경의 관계에서 나온다.

## 1. Train error와 generalization error

```text
train error
validation/test error
generalization gap = evaluation error - train error
```

Train error가 낮고 evaluation error가 높으면 overfitting 가능성이 있다. 그러나 gap만으로 원인을 확정하지 않는다.

- train과 evaluation distribution이 다른가
- label quality가 다른가
- preprocessing이 달라졌는가
- metric의 sample variance가 큰가
- optimization이 train도 충분히 맞추지 못했는가

## 2. Underfitting과 overfitting

### Underfitting

Train과 validation 모두 나쁘다.

가능한 원인:

- feature에 필요한 정보가 없다.
- model family가 너무 제한적이다.
- optimization이 실패했다.
- label이 심하게 noisy하거나 잘못됐다.
- regularization이 지나치다.

### Overfitting

Train은 매우 좋지만 validation이 나쁘다.

가능한 원인:

- model capacity가 sample에 비해 크다.
- feature leakage 또는 identity memorization이 있다.
- validation이 작은데 반복 선택했다.
- train distribution만 반영한다.
- noisy label을 외운다.

“모델이 크다” 하나로 결론내리지 않는다.

## 3. Bias와 variance의 직관

### Bias

모델의 구조적 가정 때문에 실제 패턴을 충분히 표현하지 못하는 경향이다.

### Variance

학습 sample이 조금 바뀔 때 fitted model과 prediction이 크게 달라지는 경향이다.

단순 모델은 높은 bias·낮은 variance, 복잡한 모델은 낮은 bias·높은 variance라는 고전적 직관이 있다. 실제 현대 모델에서는 optimization, pretraining, augmentation과 implicit regularization이 함께 작용하므로 단순한 크기 축으로만 해석하지 않는다.

## 4. Learning curve

Train sample 수를 늘리며 train·validation 성능을 본다.

- 둘 다 낮고 가까움: feature·model·optimization 부족 가능성
- train 높고 validation 낮으며 gap 큼: 더 많은 data·regularization·단순화 고려
- validation이 계속 개선: 추가 data 가치가 있을 수 있음
- plateau: label·feature·metric·분포 경계 재검토

Learning curve는 같은 split policy와 training budget에서 비교한다. 작은 dataset subset이 class·time·group 구조를 보존하는지 확인한다.

## 5. Regularization

### L2

큰 weight를 제곱 penalty로 제한한다. 여러 correlated feature에 weight를 분산할 수 있다.

### L1

절대값 penalty를 사용한다. 일부 coefficient를 0으로 만들 수 있으나 선택 안정성과 해석을 별도로 검토한다.

### Tree regularization

- max depth
- minimum samples per leaf
- pruning
- learning rate와 tree 수

### Neural regularization

- weight decay
- dropout
- data augmentation
- label smoothing
- early stopping
- normalization과 architecture bias

각 regularizer는 validation에서 선택하며 final test에 맞춰 조정하지 않는다.

## 6. Early stopping

Validation metric이 개선되지 않을 때 학습을 중단하고 좋은 checkpoint를 선택한다.

계약:

- 어떤 metric을 감시하는가
- maximize/minimize 방향
- patience와 minimum improvement
- 평가 주기
- best checkpoint와 last checkpoint 차이
- validation을 얼마나 자주 봤는가

Early stopping은 validation에 기반한 model selection이다. 반복 실험과 함께 사용하면 validation adaptation이 커질 수 있다.

## 7. Data augmentation

Label을 보존한다고 믿는 변환으로 train distribution을 넓힌다.

예:

- 이미지 crop·flip
- 음성 noise
- 텍스트의 제한적 변형
- tabular measurement noise

핵심 질문:

```text
이 변환 뒤에도 label 의미가 유지되는가?
운영 환경에서 실제로 발생할 변화인가?
특정 집단에만 더 큰 왜곡을 만들지 않는가?
```

Augmentation은 train에만 적용하고 validation/test의 원래 입력을 보존한다. Test-time augmentation은 별도 inference 정책이다.

## 8. Feature selection

Feature 수를 줄이면 variance, 비용과 leakage surface를 줄일 수 있다. 그러나 selection 자체도 학습 과정이다.

- train fold 안에서 선택
- validation으로 selection rule 평가
- final test에는 fixed feature set 적용
- correlated feature와 selection stability 확인

전체 dataset에서 상관계수를 보고 feature를 고르면 test 정보가 유출된다.

## 9. Ensemble

여러 model의 prediction을 평균·vote·stacking한다.

장점:

- 독립적인 error가 일부 상쇄될 수 있다.
- variance를 줄일 수 있다.

비용:

- inference latency와 memory
- artifact와 rollback 복잡도
- calibration 변화
- error 원인 설명 어려움

Stacking의 meta-model은 base model의 out-of-fold prediction으로 학습해야 한다. 같은 train prediction을 사용하면 과적합될 수 있다.

## 10. Pretraining과 regularization

Pretrained representation은 적은 downstream data에서 strong prior를 제공한다. 그러나 다음을 확인한다.

- pretraining data contamination
- domain mismatch
- tokenizer·vocabulary mismatch
- license와 privacy
- frozen feature와 fine-tuning 비교
- 작은 baseline 대비 실제 이득

큰 pretrained model이 항상 낮은 variance나 좋은 generalization을 보장하지 않는다.

## 11. Distribution-specific generalization

“새 data에 일반화한다”는 표현은 불충분하다.

```text
같은 기간의 새 row
새로운 entity
미래 기간
새 지역
새 장치 version
정책 변경 뒤 data
```

각각 다른 generalization claim이다. Split과 slice가 주장을 구체화한다.

## 12. Shortcut learning

모델이 의도한 개념 대신 쉽게 이용 가능한 proxy를 학습한다.

예:

- 병원 이미지의 장비 표식으로 질환 예측
- 문서 source 이름으로 label 예측
- 배경 색이나 timestamp로 class 구분
- 특정 operator ID로 결과 추정

높은 test score도 test에 같은 shortcut이 존재하면 문제를 발견하지 못한다. Counterfactual 또는 source-shift slice, feature ablation과 domain review가 필요하다.

## 13. Robustness

작은 입력 변화, missing feature, category 추가와 measurement noise에서 성능을 확인한다.

Robustness test는 실제 운영 변화를 반영해야 한다. 임의 noise를 넣고 “robust”라고 부르지 않는다.

- 허용 범위 경계
- missing·default value
- unit·scale 변경
- image compression
- text encoding·길이
- category unknown
- 시간 지연

## 14. 대표적인 실패

### Train score를 숨김

Evaluation score만 보고 underfitting인지 overfitting인지 구분하지 못한다.

### Regularization search on test

Test 결과를 보고 depth, dropout, weight decay를 조정한다.

### More data라는 결론

Learning curve와 label quality를 보지 않고 모든 문제를 data 부족으로 설명한다.

### Augmentation assumption 미검증

변환이 label을 바꾸는데 train sample을 늘렸다고 생각한다.

### Shortcut을 explanation으로 오인

Feature importance가 높은 proxy를 실제 원인으로 해석한다.

## 15. 리뷰 질문

- Train과 validation curve가 어떤 실패 형태를 보이는가?
- Model capacity, optimization, data quality를 어떻게 구분했는가?
- Regularization과 early stopping은 어느 data로 선택했는가?
- Learning curve가 추가 data의 가치를 지지하는가?
- Augmentation이 label을 보존한다는 근거가 있는가?
- 다른 source·시간·group에서 shortcut이 깨지는지 확인했는가?
- Robustness input이 실제 운영 변화와 연결되는가?

## 실습 연결

누적 실습 4·6단계에서는 train·validation metric과 learning trace를 함께 기록한다. 가장 높은 validation score만 저장하지 않고 model complexity, sample size와 seed 변화에 따른 변동을 비교한다.
