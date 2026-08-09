# Machine Learning 시스템 종합 검토

이 문서는 개별 모델 지식을 다시 요약하지 않는다. 하나의 model release를 검토할 때 문제·데이터·학습·평가·artifact·운영이 같은 주장을 지지하는지 확인한다.

## 1. 한 문장으로 주장 제한하기

다음 형식으로 시작한다.

```text
[어떤 population]의 [어떤 observation time]에 उपलब्ध한 입력으로
[어떤 horizon의 outcome]을 예측해
[어떤 사용자]의 [어떤 action]을 지원하며,
[어떤 dataset·metric·slice]에서 [어떤 범위]까지 검증했다.
```

문장을 채울 수 없다면 model 구조보다 problem framing을 먼저 수정한다.

## 2. 종단 간 상태 지도

```text
현실의 사건
→ data collection
→ row·label 생성
→ inclusion·sampling
→ split manifest
→ preprocessing fit
→ parameter training
→ validation selection
→ frozen candidate
→ final test
→ artifact bundle
→ inference input
→ probability·score
→ decision policy
→ action
→ delayed outcome
→ monitoring·retraining
```

각 화살표마다 다음을 묻는다.

- 입력과 출력은 무엇인가?
- 상태 소유자는 누구인가?
- version은 무엇인가?
- 실패하면 무엇이 남는가?
- 어떤 evidence로 올바름을 검사하는가?

## 3. 문제 framing review

- prediction이 실제 decision을 바꾸는가?
- heuristic이나 업무 rule로 충분하지 않은가?
- observation unit과 action unit이 같은가?
- label horizon이 action 시간과 맞는가?
- model 없이도 측정 가능한 success metric이 있는가?
- false positive·negative·abstention의 비용은 무엇인가?
- prediction이 새로운 위험이나 feedback loop를 만드는가?

## 4. dataset review

- source와 수집 목적은 무엇인가?
- row inclusion·exclusion이 population을 어떻게 바꾸는가?
- label은 누가 어떤 과정으로 만들었는가?
- prediction time 이후 정보가 들어갔는가?
- missing은 무작위인가, 업무 과정의 신호인가?
- 같은 entity·group·time가 split을 가로지르는가?
- 실제 deployment에서 생길 category·범위가 평가에 있는가?
- data 사용·retention·privacy 제약이 있는가?

## 5. baseline·metric review

- constant·rule·incumbent baseline이 있는가?
- metric이 base rate 변화에 어떻게 반응하는가?
- probability quality와 ranking quality를 구분하는가?
- threshold가 action capacity와 비용에 연결되는가?
- 전체 평균과 중요한 slice를 함께 보는가?
- sample size와 uncertainty를 기록하는가?
- 여러 실험을 본 뒤 validation에 과적합하지 않았는가?

## 6. model·training review

### 고전적 model

- scaling·encoding·imputation이 training에만 fit됐는가?
- regularization과 complexity를 validation에서 선택했는가?
- feature importance를 causal effect로 해석하지 않는가?
- tree·ensemble의 calibration과 stability를 확인했는가?

### 신경망

- tensor shape와 loss contract가 맞는가?
- 작은 batch를 overfit할 수 있는가?
- gradient가 finite하고 update가 실제 일어나는가?
- training·evaluation mode가 분리되는가?
- checkpoint 선택이 validation에 고정됐는가?
- seed·learning curve·failure trace가 있는가?

### 현대 model

- tokenization·vocabulary·context limit이 version되는가?
- attention mask와 position contract가 맞는가?
- pretrained model의 source·license·revision이 기록되는가?
- fine-tuning evaluation이 memorization과 contamination을 고려하는가?
- 생성 평가가 단일 자동 score에 의존하지 않는가?

## 7. final evaluation review

- model·feature·threshold 선택을 모두 고정했는가?
- test를 몇 번 확인했는가?
- prediction file과 row identity를 보존했는가?
- 오류 사례를 false positive·negative로 조사했는가?
- slice·calibration·shift 조건을 봤는가?
- 주장하지 못하는 환경을 명시했는가?
- test 결과와 artifact digest가 연결되는가?

## 8. artifact·inference review

- input schema와 feature order가 있는가?
- fitted preprocessing state가 model과 함께 있는가?
- output class·score·probability 의미가 명확한가?
- model과 decision policy version이 분리되는가?
- clean environment에서 load·smoke가 가능한가?
- invalid input·timeout·fallback·partial failure가 정의되는가?
- old client·schema와 compatibility를 검사하는가?
- rollback할 이전 bundle과 traffic 절차가 있는가?

## 9. monitoring·retraining review

- service·data·prediction·outcome metric을 분리하는가?
- reference period와 sample count가 있는가?
- delayed label의 maturity cutoff가 있는가?
- calibration과 threshold 주변 변화를 보는가?
- 중요한 slice와 privacy 정책이 있는가?
- alert에 owner·evidence·action이 있는가?
- retraining trigger와 release approval이 분리되는가?
- incumbent를 새 dataset에서 다시 평가하는가?
- bad action과 batch output을 rollback 뒤 처리할 수 있는가?

## 10. 문서·위험 review

- model card가 실제 artifact version을 가리키는가?
- intended use·out-of-scope use가 구체적인가?
- limitation이 관측 가능한 조건과 control로 연결되는가?
- human review가 실제 시간·정보·권한을 갖는가?
- privacy·fairness·security·misuse와 feedback loop를 검토했는가?
- incident와 model change에서 문서를 갱신할 owner가 있는가?

## 11. 장애 시나리오

### 시나리오 A: validation은 좋아졌지만 test는 baseline과 같다

확인 순서:

1. 반복 model selection과 validation overfitting
2. seed variation
3. split population 차이
4. preprocessing·feature leak
5. 작은 효과와 sample uncertainty

Model을 즉시 더 복잡하게 만들지 않는다.

### 시나리오 B: 배포 뒤 positive rate가 두 배가 됐다

가능한 원인:

- input population 변화
- schema default·missing 처리
- preprocessing mismatch
- model version 오류
- threshold·policy 변경
- 실제 base rate 변화

Model retraining 전에 version과 pipeline evidence를 수집한다.

### 시나리오 C: 전체 metric은 유지되지만 신규 사용자 recall이 하락했다

- slice count와 label maturity 확인
- training coverage와 feature availability 확인
- 새로운 product flow·policy 변경 조사
- 해당 slice 자동 action 제한 검토
- data 보강·model 또는 threshold 변경을 독립 평가

### 시나리오 D: artifact는 load되지만 prediction이 과거와 다르다

- feature order
- scaler·vocabulary
- library·precision
- evaluation mode
- label map·postprocessing
- schema adapter
- model digest

### 시나리오 E: 정기 재학습 model이 갑자기 매우 좋아졌다

- label query·cutoff 변경
- future information
- duplicate·entity overlap
- test reuse
- sample composition
- monitoring·metric code 변경

큰 개선일수록 먼저 누출과 계약 변경을 의심한다.

## 12. 최종 제출 패키지

완성된 학습 결과는 다음 구조를 권장한다.

```text
release-review/
├── problem-contract.md
├── dataset-card.md
├── split-audit.json
├── baseline.json
├── experiments.jsonl
├── evaluation.json
├── artifacts/
│   └── model-bundle/
├── model-card.md
├── monitoring-plan.md
├── release-decision.md
└── reproduction.md
```

`reproduction.md`에는 다음을 적는다.

- 필요한 입력과 접근 조건
- environment setup
- training·evaluation·bundle 명령
- 예상 생성물
- 결정적이지 않은 구간
- 비용·시간·hardware 한계

## 13. 종료 능력 판정

다음 질문에 근거와 함께 답할 수 있으면 이 가이드의 진입 목표를 달성한 것이다.

1. 왜 이 prediction이 필요한가?
2. 어떤 row와 label이 실제 future decision을 모사하는가?
3. 어떻게 누출 없는 split과 baseline을 만들었는가?
4. 왜 이 metric·threshold·model을 선택했는가?
5. 어디서 실패하며 어떤 집단에는 근거가 약한가?
6. 어떤 artifact가 평가 결과와 일치하는가?
7. 새로운 입력을 어떤 schema와 preprocessing으로 처리하는가?
8. 품질 변화와 incident를 어떻게 발견·제한·복구하는가?
9. 어떤 변경이 전체 재평가를 요구하는가?
10. 실제 프로젝트에서 다음으로 조사할 전문 영역은 무엇인가?

모든 질문에 완벽한 답을 갖는 것이 아니라, 부족한 근거를 숨기지 않고 다음 검증을 설계할 수 있어야 한다.
