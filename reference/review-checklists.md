# 검토 체크리스트

이 문서는 문서별 질문을 실제 프로젝트 review에 사용할 수 있도록 압축한 것이다. 체크 표시 자체보다 각 항목의 evidence 위치를 함께 기록한다.

## Problem

- [ ] Prediction subject, observation time과 label window가 있다.
- [ ] Prediction이 바꾸는 action과 owner가 있다.
- [ ] Model이 필요 없는 baseline·업무 rule을 검토했다.
- [ ] False positive·negative·abstention의 비용이 있다.
- [ ] 금지·비지원 사용이 구체적이다.

## Dataset

- [ ] Source·기간·inclusion·exclusion을 기록했다.
- [ ] Row identity와 duplicate policy가 있다.
- [ ] Label 생성·maturity·오류를 기록했다.
- [ ] Feature availability cutoff를 검사했다.
- [ ] Missing·unknown·measurement limitation이 있다.
- [ ] Privacy·retention·access 조건이 있다.

## Split

- [ ] Deployment 상황에 맞는 entity·group·time 경계를 사용한다.
- [ ] Train·validation·test overlap을 자동 검사한다.
- [ ] Preprocessing과 feature selection은 training에만 fit한다.
- [ ] Test는 selection에 사용하지 않는다.
- [ ] 여러 실험에 의한 validation overfitting을 고려한다.

## Baseline·metric

- [ ] Constant·rule·incumbent 중 적절한 baseline이 있다.
- [ ] Selection metric이 action 비용·capacity와 연결된다.
- [ ] Probability·ranking·decision metric을 구분한다.
- [ ] Threshold 선택 위치와 version이 있다.
- [ ] Calibration·slice·sample size를 본다.

## Training

- [ ] Config·seed·code·environment를 기록한다.
- [ ] Learning curve와 checkpoint rule이 있다.
- [ ] Neural model은 shape·gradient·mode를 검사한다.
- [ ] 여러 seed 또는 stability evidence가 있다.
- [ ] 실패한 run과 선택하지 않은 대안을 보존한다.

## Artifact·inference

- [ ] Model·preprocessing·schema·label map이 함께 version된다.
- [ ] Clean process load·smoke test가 있다.
- [ ] Output 의미와 policy version이 명확하다.
- [ ] Invalid input·timeout·fallback을 정의한다.
- [ ] Compatibility와 rollback을 검사한다.

## Monitoring·risk

- [ ] Service·data·prediction·outcome monitoring을 분리한다.
- [ ] Label maturity와 feedback loop를 고려한다.
- [ ] Alert에 owner와 action이 있다.
- [ ] Retraining trigger와 release approval이 분리된다.
- [ ] Model card가 실제 artifact를 가리킨다.
- [ ] Limitation에 control 또는 지원 범위 축소가 연결된다.
