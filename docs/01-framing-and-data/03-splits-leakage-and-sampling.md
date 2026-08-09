# Split, sampling과 데이터 누출

평가 점수는 모델만의 속성이 아니다. **어떤 표본을 어떤 규칙으로 분리했고, 학습 과정에서 어느 정보가 사용됐는지**의 결과다. 잘못된 split은 실제로 일반화하지 못하는 모델을 좋은 모델처럼 보이게 만든다.

## 1. Train, validation, test의 역할

### Train

모델 parameter와 preprocessing 통계를 학습한다.

### Validation

모델 family, feature, hyperparameter, threshold와 중단 시점을 선택한다. 반복해서 보면 validation에도 적응한다.

### Test

선택이 끝난 뒤 최종 주장을 확인한다. test 결과를 보고 모델이나 threshold를 바꾸면 더 이상 final test가 아니다.

```text
train: 학습
validation: 선택
test: 최종 주장
```

세 파일로 나뉘어 있다는 사실보다 **정보 흐름이 분리돼 있는지**가 중요하다.

## 2. 무엇을 일반화하려는가

Split은 미래 사용 환경을 모사해야 한다.

- 새로운 row인가
- 새로운 사람·계정·장치인가
- 미래 시간대인가
- 새로운 지역·기관인가
- 새로운 문서 source인가
- 새로운 제품 version인가

이 질문에 따라 random, group, time, spatial split이 달라진다.

## 3. Random split의 가정

독립적이고 동일한 분포에서 뽑힌 row라면 random split이 적절할 수 있다. 실제 dataset은 자주 이 가정을 위반한다.

- 같은 사용자의 여러 observation
- 같은 환자의 여러 이미지
- 같은 원문에서 잘라낸 여러 chunk
- 같은 장치의 반복 센서 기록
- 연속된 시간 window
- 복제·증강된 sample

이들이 split 사이에 들어가면 모델이 대상 고유 신호를 기억하거나 거의 같은 입력을 다시 볼 수 있다.

## 4. Group-aware split

같은 entity 또는 source에서 나온 row를 같은 split에 둔다.

```text
group key 예:
user_id
patient_id
device_id
document_id
session_id
site_id
```

Group split을 사용할 때도 다음을 확인한다.

- group 크기가 매우 다르지 않은가
- label이 특정 group에만 몰리지 않는가
- 작은 class가 validation/test에서 사라지지 않는가
- 운영에서는 기존 entity의 미래를 예측하는지, 완전히 새로운 entity를 예측하는지

운영 목표가 “기존 사용자 다음 주 행동”이라면 entity 전체를 분리하는 것보다 시간 기준 분리가 더 현실적일 수 있다. split은 정답 하나가 아니라 generalization claim의 일부다.

## 5. Time split

미래를 예측한다면 학습보다 평가가 뒤 시간에 있어야 한다.

```text
train period < validation period < test period
```

주의할 점:

- label이 확정될 outcome window만큼 gap이 필요한가
- 집계 feature의 window가 split 경계를 넘어가는가
- 늦게 도착한 event가 과거 snapshot을 수정하는가
- 계절·정책·제품 version 변화가 포함되는가
- 같은 entity의 과거와 미래 row를 허용할 것인가

시간 split은 미래 환경에 더 가깝지만 sample 수가 적고 변동성이 클 수 있다. 그것이 불편하다는 이유로 random split으로 바꾸지 않는다.

## 6. Stratification

Class 비율을 split마다 비슷하게 유지하는 기법이다. 작은 불균형 dataset에서 유용하지만 다음을 해결하지 않는다.

- entity 중복
- 시간 누출
- source contamination
- rare subgroup 누락
- distribution shift

먼저 group와 time 경계를 지킨 뒤 가능한 범위에서 stratification을 적용한다.

## 7. 데이터 누출의 종류

### Target leakage

label 또는 label 이후 사건이 feature에 직접·간접 포함된다.

예:

- 해지 완료 뒤 생성되는 상태 code
- fraud 조사 결과가 반영된 manual flag
- 시험 정답을 포함하는 문서 metadata

### Train-test contamination

평가 sample이나 그 파생 정보가 학습에 들어간다.

- 같은 sample의 duplicate
- augmentation 원본과 파생본 분리
- 문서 chunk가 서로 다른 split에 위치
- 공개 benchmark test를 pretraining에서 학습

### Preprocessing leakage

전체 dataset으로 preprocessing을 fit한다.

- 전체 평균·분산으로 scaling
- 전체 vocabulary·category 집합 생성
- 전체 dataset으로 imputation
- 전체 데이터에서 feature selection
- split 전에 oversampling

`fit`은 train에만, `transform`은 validation/test에 적용한다. Pipeline을 사용하는 이유는 이 순서를 코드 구조로 고정하기 위해서다.

### Selection leakage

Test 결과를 보고 model·feature·threshold를 반복 선택한다. 파일은 분리돼 있어도 사람이 정보를 전달한다.

### Temporal leakage

예측 시점 이후 정보, 수정된 snapshot, 미래 집계가 들어간다.

### Identity leakage

직접 식별자 또는 거의 유일한 proxy를 통해 entity를 기억한다. ID column을 제거해도 rare combination, timestamp와 free text가 같은 역할을 할 수 있다.

## 8. Sampling과 prevalence

학습 효율을 위해 class를 oversample하거나 undersample할 수 있다. 그러나 sample prevalence가 실제 환경과 달라지면 다음이 바뀐다.

- raw probability의 calibration
- precision과 positive predictive value
- threshold별 workload
- expected cost

Sampling은 train에만 적용하고 validation/test는 목표 환경의 비율을 유지한다. 모델이 score ranking을 잘하더라도 실제 prevalence에서 probability를 다시 검토해야 한다.

## 9. Cross-validation

Dataset이 작을 때 여러 split에서 성능 변동을 추정한다. 그러나 random K-fold가 항상 정답은 아니다.

- group가 있으면 GroupKFold 계열
- 시간 순서가 있으면 forward/rolling split
- hyperparameter 선택과 최종 성능 추정을 모두 할 때 nested CV 고려
- preprocessing은 각 fold의 train에서 fit

Fold 점수의 평균만 보고 끝내지 않는다. 분산, 최저 성능, group 구성과 실패 slice를 확인한다.

## 10. Test set governance

Final test는 제한된 자원으로 다룬다.

- 접근 권한과 사용 횟수 기록
- label과 feature inspection 범위 제한
- test 결과 뒤 변경 시 새 validation 또는 새 test 준비
- benchmark 제출 반복도 test adaptation으로 간주
- dataset contamination 가능성 기록

Test set을 영원히 완전히 숨기는 것이 목적이 아니다. 어떤 의사결정이 test를 사용했는지 추적해 주장 강도를 제한하는 것이 목적이다.

## 11. Split manifest

Row 자체에 `split` column을 직접 저장하거나 별도 manifest를 사용한다. manifest에는 다음을 포함한다.

```text
observation_id
entity_id 또는 group_id
split
split_policy_version
optional reason 또는 fold
```

Split을 매 실행마다 무작위 생성하지 않는다. 실험 비교를 위해 manifest와 seed, algorithm version을 고정한다. 새로운 split을 만들면 별도 version으로 취급한다.

## 12. 자동 검사

- 모든 observation이 정확히 한 split에 존재
- 알 수 없는 split name 없음
- split별 최소 row와 class 존재
- group disjointness
- time ordering과 gap
- duplicate content hash
- label prevalence와 missing rate report
- train-only transform 여부를 pipeline test로 확인

자동 검사가 누출이 없음을 완전히 증명하지는 않는다. feature provenance와 업무 시간 경계는 사람 review가 필요하다.

## 13. 대표적인 실패

### Split 후 feature 생성

원본 row는 분리했지만 전체 source table에서 미래 집계를 다시 계산해 test 정보를 가져온다.

### Duplicate를 ID로만 검사

텍스트·이미지·record가 다른 ID로 복제돼 있다. normalized content hash나 source lineage가 필요하다.

### Validation leaderboard

수백 번 실험해 validation 최고값만 선택하고 그 변동성을 보고하지 않는다.

### Test를 diagnostic으로 사용

Test slice가 나쁜 이유를 분석하고 feature를 수정한 뒤 같은 test에 다시 보고한다. 이 데이터는 사실상 validation으로 전환됐다.

## 14. 리뷰 질문

- 배포 시 generalization 대상은 새 row, 새 entity, 미래 시간 중 무엇인가?
- 같은 source에서 나온 파생 sample이 split 사이에 존재하는가?
- preprocessing·feature selection·sampling이 train 안에서만 fit되는가?
- label window와 feature window가 split 경계를 넘지 않는가?
- validation을 몇 번 사용했고 어떤 선택이 영향을 받았는가?
- final test를 본 뒤 변경한 항목이 있는가?
- 실제 prevalence와 평가 prevalence가 같은가?
- split manifest를 다시 생성하지 않고 같은 실험을 재현할 수 있는가?

## 실습 연결

누적 실습의 `split_manifest.csv`는 `entity_id`를 기준으로 train·validation·test를 분리한다. [`verify-fixtures.py`](../../scripts/verify-fixtures.py)는 row 누락, split 중복, 알 수 없는 split과 entity overlap을 거부한다. 학습자는 이 정책이 “새 entity 일반화”를 모사한다는 점과 실제 서비스에서 적합하지 않을 수 있는 이유를 보고서에 기록한다.
