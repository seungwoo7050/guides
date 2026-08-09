# 인과, 분포 변화와 예측의 한계

예측 모델은 관측 데이터에서 `X`와 `Y`의 관계를 학습한다. 이 관계만으로 “X를 바꾸면 Y가 바뀐다”는 인과 결론을 얻을 수 없다. 또한 배포 이후 정책과 사용자가 변하면 학습 당시 관계가 유지되지 않을 수 있다.

## 1. Prediction과 intervention

Prediction 질문:

```text
현재 관측 x를 가진 대상의 y는 무엇일 가능성이 큰가?
```

Causal 질문:

```text
같은 대상에게 action A를 했을 때와 하지 않았을 때 y가 어떻게 달라지는가?
```

둘은 다르다. 이탈 가능성이 높은 사용자가 할인에 반응한다는 보장은 없다. 이미 떠나기로 결정했거나 할인 비용만 늘어날 수 있다.

## 2. Confounding

관측되지 않거나 통제되지 않은 변수 `Z`가 `X`와 `Y` 모두에 영향을 줄 수 있다.

예:

```text
지원 요청 횟수 X
이탈 Y
서비스 장애 Z
```

지원 요청이 이탈의 원인처럼 보이지만 실제로는 장애가 둘 다 증가시킬 수 있다. Feature importance나 coefficient로 인과를 주장하지 않는다.

## 3. Post-treatment variable

Action 이후 생긴 정보를 feature로 사용한다.

```text
할인 제공 A
상담 완료 X
이탈 Y
```

상담 완료는 action의 결과다. 이를 통제하거나 예측 feature로 사용하면 실제 효과를 왜곡하거나 시간 누출을 만든다.

## 4. Selection bias

Dataset에 포함될 확률이 outcome과 관련돼 있다.

- 승인된 대출만 상환 label이 있음
- 검사받은 사람만 질병 label이 있음
- 신고된 fraud만 positive로 확인됨
- 앱을 계속 사용하는 사람만 장기 outcome이 있음

관측된 label만으로 전체 모집단에 일반화하면 기존 선택 정책을 재생산할 수 있다.

## 5. Randomized experiment

Action의 인과 효과를 확인하는 강력한 방법은 적절한 무작위 실험이다.

필요 요소:

- 대상과 exclusion 기준
- treatment와 control
- 사전 정의한 outcome
- sample size와 종료 규칙
- interference와 spillover 고려
- 안전·윤리·법적 검토

모든 상황에서 실험이 가능하거나 허용되는 것은 아니다. Observational causal inference는 별도 전문 영역이며 강한 가정이 필요하다.

## 6. Distribution shift

### Covariate shift

`P(X)`가 바뀌지만 `P(Y|X)`는 대략 유지된다.

예: 사용자 지역 비율 변화.

### Label shift

Class prevalence `P(Y)`가 바뀐다.

예: fraud rate 증가.

### Concept shift

`P(Y|X)` 자체가 바뀐다.

예: 정책·사용자 행동·공격 전략 변화.

### Measurement shift

같은 개념을 측정하는 장치·logging·schema가 바뀐다.

예: 센서 calibration, 새로운 이벤트 집계 코드.

실제 변화는 여러 종류가 섞인다. 통계 검정 하나로 원인을 확정하지 않는다.

## 7. Temporal shift

미래 data는 과거와 다르다.

- 계절성
- 제품 release
- 가격·정책 변경
- 경제 상황
- 새로운 사용자 유입
- 경쟁자 행동
- 데이터 수집 시스템 변경

Time-based evaluation과 rolling backtest로 확인한다. Random split의 높은 score가 미래 성능을 보장하지 않는다.

## 8. Feedback loop

모델 action이 다음 학습 data를 바꾼다.

### Exposure bias

추천된 item만 클릭 기회가 생겨 추천 모델이 자신의 선택을 정답으로 강화한다.

### Selective labels

High-risk 대상으로만 조사하면 조사하지 않은 대상의 실제 label을 모른다.

### Resource allocation

모델이 특정 집단에 지원을 집중해 outcome 분포를 바꾼다.

### Strategic response

사용자나 공격자가 모델 정책을 학습해 행동을 바꾼다.

Feedback를 추적하려면 model version, score, action, override와 outcome을 연결해 기록한다.

## 9. Target drift와 label definition change

업무 목표가 바뀔 수 있다.

- “30일 내 해지”에서 “60일 내 해지”로 변경
- fraud 조사 기준 변경
- 정책상 positive class 재정의
- annotation guideline 수정

이것은 단순 data drift가 아니다. 다른 target을 학습하는 새 problem version이다. 이전 model과 metric의 비교 가능성을 검토한다.

## 10. Out-of-distribution 입력

학습 지원 범위 밖의 입력을 탐지하거나 처리해야 한다.

- unknown category
- 극단적인 numeric range
- 새로운 언어·device·site
- image·text 형식 변경
- missing feature 조합

OOD score는 완벽한 안전 장치가 아니다. Schema validation, explicit allowlist, abstention과 사람 review를 함께 사용한다.

## 11. Counterfactual과 sensitivity

입력을 조금 바꿔 prediction이 어떻게 변하는지 관찰할 수 있다. 그러나 counterfactual explanation이 실제로 가능한 action이나 인과 효과를 뜻하지 않는다.

검토:

- 바꿀 수 없는 feature를 수정하지 않는가
- feature 사이 현실적 제약을 지키는가
- model boundary의 불안정성만 보여 주는가
- action을 취했을 때 outcome이 바뀐다고 오해할 수 있는가

## 12. Fairness와 historical pattern

과거 outcome은 과거 정책·접근성·측정 편향을 포함한다. 모델이 잘 예측한다는 것은 그 패턴을 정확히 재현한다는 뜻일 수 있다.

- label이 공정한 목표인가
- 오류 비용이 집단마다 다른가
- protected attribute를 제거해도 proxy가 남는가
- action이 불평등을 확대하는가
- 집단별 metric을 계산할 sample과 정당한 사용 근거가 있는가

Fairness metric 하나로 사회적·법적 판단을 끝내지 않는다.

## 13. Monitoring으로 알 수 있는 것과 없는 것

Input distribution, missing rate와 score distribution 변화는 **무언가 달라졌다는 신호**다. Label이 늦게 도착하면 실제 model quality 저하를 바로 알 수 없다.

Drift detector가 알려 주지 못하는 것:

- 변화가 해로운지
- causal 원인이 무엇인지
- 재학습이 해결책인지
- 새 label이 더 정확한지
- 사용자 영향이 허용 가능한지

Alert 뒤 조사·fallback·rollback 절차가 필요하다.

## 14. Model update가 항상 답은 아니다

성능 저하 원인이 다음이라면 재학습보다 다른 조치가 필요할 수 있다.

- upstream schema bug → data pipeline 수정
- label 정의 변경 → problem contract와 평가 재설계
- policy feedback → experiment 또는 logging 개선
- class prevalence 변화 → threshold·calibration 조정
- 새로운 비범위 입력 → routing·abstention
- 제품 action 실패 → workflow 개선

자동 재학습은 문제를 빠르게 반복할 수도 있다.

## 15. 주장 수준

### 강하게 말할 수 있는 것

```text
고정된 split과 evaluation code에서
모델 A가 baseline B보다 metric M에서 이 범위만큼 높았다.
```

### 추가 근거가 필요한 것

```text
미래 사용자에서 같은 품질을 유지한다.
이 action이 outcome을 개선한다.
모든 집단에 공정하다.
안전하게 자동화할 수 있다.
```

문서에서 관측 사실, 추론과 가정을 구분한다.

## 16. 대표적인 실패

### Feature importance → 원인

높은 importance를 원인 또는 intervention 대상으로 해석한다.

### Drift → retrain

Distribution metric이 바뀌면 자동으로 최신 data에 재학습한다.

### Historical label → objective truth

과거 정책에서 생성된 label을 중립적 현실로 본다.

### Offline evaluation → product impact

예측 성능으로 action의 효과를 주장한다.

## 17. 리뷰 질문

- 질문은 예측인가 intervention 효과인가?
- Label과 feature가 기존 정책의 선택을 어떻게 반영하는가?
- 배포 action이 다음 dataset을 어떻게 바꾸는가?
- 어떤 shift를 split과 monitoring이 모사하는가?
- Target definition이 바뀌면 새 problem version으로 관리하는가?
- OOD·unknown input에서 보류하거나 fallback하는가?
- Drift alert 뒤 원인을 조사할 증거가 있는가?
- 모델 평가가 지지하는 주장보다 더 넓게 말하고 있지 않은가?

## 실습 연결

누적 실습 8단계에서는 합성 dataset의 group split이 미래 시간 변화를 직접 검증하지 못한다는 한계를 model card에 기록한다. Monitoring plan에는 label delay, input shift와 action feedback를 서로 다른 신호로 구분한다.
