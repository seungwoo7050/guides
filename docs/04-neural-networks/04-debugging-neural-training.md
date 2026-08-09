# 학습 실패 디버깅

신경망이 학습되지 않을 때 architecture를 바꾸기 전에 **data·label·shape·loss·gradient·optimization·evaluation** 순서로 원인을 좁힌다. 복잡한 모델은 많은 오류를 흡수한 채 그럴듯한 loss를 만들 수 있다.

## 1. 실패를 구체화한다

“성능이 안 나온다”를 다음 상태로 분해한다.

- 실행 오류
- NaN·inf
- loss가 변하지 않음
- train loss는 감소하지만 metric이 변하지 않음
- train은 좋고 validation은 나쁨
- seed마다 결과가 크게 다름
- throughput·memory 문제
- offline은 좋지만 inference가 다름

각 실패는 다른 증거가 필요하다.

## 2. Tiny batch overfit

아주 작은 sample 집합에 training loss를 거의 0으로 만들 수 있는지 본다.

목적:

- model에 최소 표현력이 있는가
- label과 output shape가 맞는가
- gradient가 흐르는가
- optimizer step이 parameter를 바꾸는가
- loss 구현이 맞는가

Tiny batch도 못 맞추면 regularization, augmentation, dropout을 끄고 pipeline을 단순화한다. Tiny batch 성공은 generalization 증거가 아니다.

## 3. Data와 label 검사

첫 batch를 사람이 읽을 수 있는 형태로 본다.

- sample ID와 split
- raw input과 transformed input
- label과 class mapping
- missing·padding
- min/max/mean·category count
- input-label alignment

Shuffle 때문에 input과 label order가 어긋나는 오류, off-by-one sequence target, stale cache를 찾는다.

## 4. Baseline과 constant prediction

학습 model prediction distribution을 본다.

- 모든 score가 같은가
- 한 class만 예측하는가
- class prior와 비슷한가
- logits가 극단적인가

Dummy baseline보다 나쁜 경우 metric·label mapping·threshold 구현부터 확인한다.

## 5. Loss sanity check

- 무작위 prediction의 예상 loss
- 완벽한 prediction의 loss
- label permutation 시 성능
- batch 크기와 reduction 변화
- class weight 적용 전후

Binary label이 `{-1,1}`인데 `{0,1}`용 loss를 쓰는 등 계약 오류를 찾는다.

## 6. Gradient 검사

Layer별로 확인한다.

- gradient가 `None`인가
- norm이 0에 가까운가
- 폭발하는가
- parameter update가 실제로 발생하는가
- frozen layer가 의도와 같은가

Custom loss·operation은 finite difference로 검사한다. 큰 model에서 모든 gradient를 출력하지 않고 summary와 anomaly hook을 사용한다.

## 7. Activation 검사

Forward hook 또는 작은 debug path에서 다음을 본다.

- mean·variance
- zero 비율
- saturation
- NaN·inf
- layer별 scale

ReLU unit 대부분이 0이거나 sigmoid가 포화되면 initialization, input scaling과 learning rate를 확인한다.

## 8. Learning rate 탐색

여러 order의 learning rate에서 짧게 학습한다.

- loss가 즉시 폭발: 너무 큼, scale 오류 가능
- 거의 변하지 않음: 너무 작음 또는 gradient 없음
- 감소 후 진동: schedule·batch·normalization 확인

최적값을 test에 맞추지 않는다. 동일 initial state와 budget에서 validation한다.

## 9. Train·validation curve

### 둘 다 개선 없음

- data/label bug
- optimization failure
- model capacity 부족
- feature 정보 부족

### Train만 개선

- overfitting
- split shift
- leakage 반대 방향의 pipeline mismatch
- train augmentation/validation processing 차이

### Validation이 갑자기 악화

- learning rate change
- normalization state
- checkpoint bug
- small validation variance

Curve를 smoothing한 값만 보지 않고 raw event와 step를 보존한다.

## 10. Metric 구현 검사

- class index와 positive label
- threshold 방향
- padding·ignored label
- sample weight
- batch aggregation
- multi-class average
- duplicate prediction

작은 손계산 fixture와 [`examples/metrics.py`](../../examples/metrics.py)를 기준으로 검증한다.

## 11. Evaluation mismatch

- `model.eval()` 누락
- no-grad 누락
- validation에 train augmentation
- different tokenizer·vocabulary
- checkpoint load 실패
- model과 preprocessing version 불일치
- feature order 차이

Train notebook과 release path를 같은 golden fixture로 비교한다.

## 12. NaN·inf

조치 순서:

1. 최초 비정상 step을 찾는다.
2. input·label의 finite 여부를 검사한다.
3. loss 전 logits와 intermediate를 검사한다.
4. learning rate·gradient norm을 확인한다.
5. unstable operation과 dtype를 확인한다.
6. anomaly를 숨기는 clipping·replacement를 제거한다.

NaN을 `nan_to_num`으로 바꾸고 계속 학습하는 것은 원인 해결이 아니다.

## 13. Memory 문제

- batch size
- sequence length
- activation 저장
- gradient accumulation
- evaluation graph
- logging tensor reference
- optimizer state
- unused output 보존

Memory leak과 정상 peak를 구분한다. Iteration마다 memory가 증가하는지, 특정 batch에서만 peak가 생기는지 측정한다.

## 14. 성능 문제

Profile 전에 추측하지 않는다.

- data loading
- Python overhead
- device transfer
- synchronization
- small operation 다수
- padding waste
- evaluation·logging

Throughput을 sample/s 또는 token/s로 정의하고 batch·device·dtype를 함께 기록한다. 필수 가이드는 성능 최적화보다 정확성 검증을 우선한다.

## 15. Seed instability

가능한 원인:

- 작은 dataset
- unstable split
- 높은 learning rate
- strong regularization·early stopping 경계
- rare class batch
- nondeterministic operation

여러 seed의 분포를 보고 near-best model들의 error가 비슷한지 확인한다. 좋은 seed 하나를 선택해 안정성 문제를 숨기지 않는다.

## 16. 데이터가 문제일 때

- label noise
- duplicate·contamination
- missing pattern
- source mismatch
- feature availability 오류
- class prevalence 변화

Architecture search보다 dataset review와 error sample 검토가 더 큰 개선을 만들 수 있다.

## 17. 디버깅 순서

```text
1. 작은 fixture와 baseline
2. 첫 batch raw/transformed/label 확인
3. tiny batch overfit
4. loss·metric 손계산
5. gradient·parameter update
6. train curve
7. validation pipeline
8. seed·split 반복
9. architecture·regularization 변경
10. 성능 최적화
```

한 번에 여러 항목을 바꾸지 않는다. 각 실험은 하나의 가설을 판별해야 한다.

## 18. 대표적인 실패

### Architecture 변경으로 시작

Data mapping 오류를 layer 추가로 가린다.

### Tiny batch에 augmentation 유지

의도적으로 매번 바뀌는 input을 완벽히 맞추지 못한다고 model을 의심한다.

### Metric library 맹신

Positive label과 averaging default를 확인하지 않는다.

### Logging이 graph를 보존

Loss tensor를 detach하지 않고 list에 쌓아 memory가 증가한다.

### Best seed 선택

불안정한 training을 좋은 run 하나로 보고한다.

## 19. 리뷰 질문

- 실패를 관측 가능한 상태로 구체화했는가?
- Tiny batch를 regularization 없이 맞출 수 있는가?
- 첫 batch의 raw input·transform·label을 직접 확인했는가?
- Loss와 metric을 작은 손계산 fixture로 검증했는가?
- Gradient·activation·parameter update가 예상 scale인가?
- Train과 validation pipeline 차이를 나열할 수 있는가?
- NaN의 최초 발생 경계를 찾았는가?
- Seed·split 변동을 model 품질에 포함했는가?
- 한 실험이 하나의 가설을 판별하는가?

## 실습 연결

누적 실습 6단계의 완료 조건에는 tiny-batch overfit, gradient norm 기록, train·validation curve, NaN 검사와 두 seed 이상 비교가 포함된다. 최종 test 점수만 제출해서는 완료하지 못한다.
