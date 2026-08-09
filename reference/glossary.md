# 용어

이 문서는 가이드에서 반복 사용하는 용어의 **현재 브랜치 내 의미**를 고정한다. 프로젝트와 분야에 따라 더 엄밀하거나 다른 정의를 사용할 수 있다.

## 문제·데이터

### prediction subject

예측이 가리키는 사람·객체·사건이다. 한 row와 같을 수도 있지만 sequence나 group일 수도 있다.

### observation unit

Dataset row 하나가 나타내는 관측 단위다. `customer-month`, `transaction`, `document`처럼 시간과 entity를 함께 포함할 수 있다.

### observation time

예측에 사용할 수 있는 정보의 cutoff다. 이 시점 이후 정보가 feature에 들어가면 미래 누출이 된다.

### label window

Observation time 이후 outcome을 관찰하는 기간이다. `다음 30일 내 churn`처럼 정의한다.

### provenance

Data가 어디서 어떤 query·규칙·시점으로 만들어졌는지 추적할 수 있는 정보다.

### sampling frame

Dataset 후보가 될 수 있는 population과 관측 절차다. 실제 목표 population과 다르면 selection bias가 생긴다.

### leakage

실제 prediction 시점에 사용할 수 없는 정보 또는 validation·test의 정보가 training·selection에 들어가는 상태다.

### split manifest

각 row 또는 entity가 train·validation·test 중 어디에 속하는지 명시한 versioned 목록이다.

## 학습과 평가

### baseline

새 model이 최소한 비교해야 하는 단순·기존 방법이다. 상수, 업무 rule, 기존 model과 간단한 선형 model이 포함될 수 있다.

### loss

Parameter 학습 과정에서 최소화하는 목적 함수다. 실제 업무 비용이나 최종 평가 metric과 같지 않을 수 있다.

### metric

Prediction과 label을 비교해 특정 품질 측면을 수치화한 함수다. 하나의 metric이 모든 오류와 사용자 영향을 대표하지 않는다.

### decision threshold

Score 또는 probability를 action class로 바꾸는 경계다. Model parameter가 아니라 별도 policy일 수 있다.

### calibration

예측 probability와 실제 outcome 빈도가 일치하는 정도다. Ranking이 좋아도 calibration은 나쁠 수 있다.

### validation set

Model·feature·hyperparameter·checkpoint·threshold를 선택하는 데 사용하는 held-out data다.

### test set

선택을 고정한 뒤 최종 주장을 검사하는 data다. 반복 선택에 사용하면 독립성을 잃는다.

### generalization

Training sample을 외우는 것을 넘어 목표 distribution의 새로운 관측에서 성능을 유지하는 성질이다.

### regularization

학습 가능한 해를 제한하거나 단순한 해를 선호하게 해 generalization을 개선하려는 방법이다.

### distribution shift

Training·평가와 실제 사용 시점 사이에 input, label 비율 또는 input-label 관계가 달라지는 상태다.

## 모델

### parameter

학습으로 갱신되는 model state다. Weight와 bias가 대표적이다.

### hyperparameter

학습 전에 정하거나 validation으로 선택하는 설정이다. Learning rate, tree depth와 regularization strength 등이 있다.

### logit

Probability 변환 전의 비정규화 score다. Binary sigmoid나 multiclass softmax의 입력이 된다.

### embedding

Discrete object나 입력을 연속 vector 공간의 표현으로 매핑한 값이다.

### tokenization

Text 또는 sequence를 model이 처리하는 discrete unit과 ID로 변환하는 규칙이다.

### attention

Query와 key의 관계로 value의 가중 결합을 만드는 연산 계열이다. Transformer의 핵심 구성 요소지만 attention 자체가 전체 model은 아니다.

### checkpoint

특정 training step의 parameter와 필요에 따라 optimizer·scheduler·random state를 저장한 상태다.

## 수명 주기

### experiment

하나의 가설과 평가 계약 아래 여러 run을 비교하는 작업 단위다.

### run

Dataset·config·code·environment가 구체적으로 정해진 한 번의 학습·평가 실행이다.

### artifact

실행 결과로 보존·전달하는 model weight, preprocessing state, schema, report 등의 파일이다.

### model bundle

Inference에 필요한 model·preprocessing·schema·label map·decision policy·metadata를 함께 version한 release 단위다.

### inference contract

새 입력을 validate·transform·예측·postprocess해 어떤 의미의 결과 또는 오류를 반환하는지 정의한 계약이다.

### monitoring baseline

운영 상태를 비교하는 reference distribution·period·model version·metric 묶음이다.

### drift

Reference와 현재 data·prediction·outcome 관계 사이의 변화다. 변화가 자동으로 품질 저하나 재학습 필요를 뜻하지 않는다.

### model card

Model의 intended use, data·평가 근거, limitation, risk와 운영 통제를 version별로 기록한 문서다.

### abstention

Model 또는 policy가 충분한 근거가 없다고 판단해 자동 prediction/action을 보류하는 결과다.
