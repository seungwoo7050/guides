# 실험, 재현성과 model artifact

모델 개발에서 “재현된다”는 말은 같은 notebook을 다시 실행했다는 뜻이 아니다. **어떤 입력과 코드, 환경, 설정으로 어떤 artifact와 평가 결과가 만들어졌는지 추적하고, 다른 사람이 같은 주장을 다시 검사할 수 있다**는 뜻이다.

모델 점수는 실행 결과 중 하나일 뿐이다. 재현 가능한 실험은 다음 관계를 보존한다.

```text
문제·dataset·split 계약
+ code revision
+ preprocessing·model 설정
+ 실행 환경과 seed
+ 학습 trace
→ model artifact
→ 고정된 evaluation report
→ 사용 범위와 한계
```

## 1. 실험의 단위

### 실험은 “모델 이름”이 아니다

`random forest`, `MLP`, `transformer`는 실험을 식별하지 못한다. 같은 모델 계열이라도 다음이 달라지면 서로 다른 실험이다.

- dataset version과 포함 기준
- split manifest
- feature schema와 preprocessing
- loss와 class weight
- hyperparameter
- random seed
- library·hardware·precision
- early stopping 기준
- checkpoint 선택 규칙
- 평가 코드와 threshold

실험 단위는 최소한 다음 질문에 답해야 한다.

1. 무엇을 예측하려 했는가?
2. 어떤 row를 어떤 split에 넣었는가?
3. 어떤 변환과 모델을 학습했는가?
4. 어떤 checkpoint를 선택했는가?
5. 어떤 metric과 slice에서 평가했는가?
6. 어떤 artifact가 이 결과를 생성했는가?

### run과 experiment를 구분한다

조직과 도구에 따라 이름은 다르지만 의미는 분리하는 편이 좋다.

```text
experiment
같은 가설과 평가 계약 아래 비교하는 실행 묶음

run
한 번의 구체적인 학습·평가 실행
```

예를 들어 “지원 이력 feature가 churn recall을 높이는가”가 experiment이고, seed와 hyperparameter가 정해진 각 실행이 run이다.

## 2. 실험 identity

실험 ID는 사람이 알아보기 쉬운 이름만으로 정하지 않는다. 다음 입력에서 안정적인 digest를 만들 수 있다.

```text
dataset digest
split manifest digest
feature schema version
training config
code revision
runtime environment
```

단, digest가 같다고 실행 결과가 bit-for-bit 동일하다는 뜻은 아니다. GPU kernel, 병렬 reduction, library 구현과 hardware 차이가 수치 결과를 바꿀 수 있다. identity는 **입력 계약을 가리키는 키**이고, 결과 동일성은 별도로 확인한다.

권장 metadata 예시는 다음과 같다.

```json
{
  "run_id": "run-2026-08-09-001",
  "problem_contract": "churn-v1",
  "dataset_sha256": "...",
  "split_sha256": "...",
  "feature_schema": "features-v3",
  "code_revision": "git-commit-or-source-digest",
  "config": {
    "model": "logistic-regression",
    "regularization": 0.1,
    "class_weight": "balanced"
  },
  "seed": 7050,
  "runtime": {
    "python": "3.x",
    "library_versions": {}
  }
}
```

## 3. 재현성의 여러 수준

### 분석 재현

같은 예측과 label을 이용해 metric·slice·plot을 다시 만들 수 있다.

이 단계에서 필요한 것은 다음이다.

- 예측 파일 또는 model artifact
- row identity
- label과 split
- metric 코드
- threshold와 slice 정의

### 학습 재현

같은 dataset과 설정으로 비슷한 품질의 모델을 다시 학습할 수 있다.

필요한 정보:

- raw 또는 versioned dataset
- split manifest
- preprocessing 구현
- 학습 코드와 config
- seed와 library version
- checkpoint 선택 규칙

### 결과 반복성

같은 환경에서 같은 실행이 허용 오차 안의 결과를 만든다. bit-for-bit 일치가 필요한지, metric 범위만 유지하면 되는지 먼저 정한다.

### 독립 재현

다른 개발자가 문서와 공개 artifact만으로 핵심 주장을 다시 검사한다. 가장 강한 형태지만 모든 프로젝트에서 완전하게 달성되지는 않는다. 데이터 접근 제한, hardware 비용과 비결정적 연산은 한계로 기록한다.

## 4. seed가 보장하지 않는 것

seed는 난수 흐름을 통제하는 입력 중 하나다. 다음을 자동으로 보장하지 않는다.

- dataset iteration 순서 전체
- 여러 worker의 scheduling
- GPU kernel의 결정성
- floating-point reduction 순서
- library version 간 구현 동일성
- 외부 서비스가 반환하는 데이터
- 파일 목록이나 hash map iteration의 안정성

따라서 “seed를 설정했다” 대신 다음을 기록한다.

```text
어떤 난수 생성기에 seed를 넣었는가
결정적 실행 옵션을 켰는가
허용 오차는 얼마인가
반복 실행 분산은 얼마인가
어떤 경로는 비결정적인가
```

점수 차이가 seed 변동 범위보다 작은데 우수한 모델이라고 단정하지 않는다. 여러 seed를 사용한다면 평균만 보고하지 않고 분포와 최악 사례를 함께 본다.

## 5. dataset과 split은 artifact다

모델 파일만 보존하고 학습 row를 복원하지 못하면 실험을 재현할 수 없다.

최소한 다음을 고정한다.

- dataset 생성 코드 또는 immutable snapshot
- source identifier와 추출 시각
- row inclusion·exclusion 규칙
- label 생성 version
- feature availability cutoff
- split manifest
- dataset·manifest digest

Dataset 전체를 저장할 수 없다면 다음을 남긴다.

- 재생성 가능한 query와 parameter
- source table·partition version
- privacy 때문에 제거한 field
- 삭제 또는 보존 정책
- 재생성 결과가 달라질 수 있는 이유

`latest.csv` 같은 이동하는 이름은 provenance가 아니다.

## 6. config와 code를 연결한다

### config는 실행 입력이다

학습 설정을 코드 안에 흩어 놓으면 비교가 어렵다. 다음을 한 구조화된 config로 수집한다.

- model architecture 또는 estimator
- feature와 preprocessing
- loss와 optimizer
- batch size·epoch·learning rate
- regularization
- class weighting·sampling
- seed
- early stopping과 checkpoint 선택
- evaluation threshold

config를 기록해도 코드가 그 값을 실제 사용하지 않으면 의미가 없다. 테스트에서 config parsing과 실행 경로를 연결한다.

### code revision만으로 부족한 경우

Git commit은 중요한 근거지만 다음은 별도 기록이 필요하다.

- uncommitted diff
- 생성된 feature code
- notebook의 실행 순서
- 외부 package와 native library
- container image 또는 lock file
- 환경 변수와 hardware capability

학습 실행 중 source를 수정하지 않는다. 긴 실행은 시작 시점의 source snapshot 또는 immutable image를 사용한다.

## 7. checkpoint 선택은 평가 계약이다

여러 epoch·checkpoint를 만들었다면 어떤 것을 release candidate로 정했는지 기록한다.

잘못된 예:

```text
테스트 점수가 가장 좋은 checkpoint를 선택했다.
```

이는 test set을 model selection에 사용한다.

올바른 흐름:

```text
training data로 parameter 학습
→ validation metric과 사전 정의한 규칙으로 checkpoint 선택
→ 선택을 고정
→ final test를 한 번 평가
```

checkpoint metadata에는 다음을 넣는다.

- epoch·step
- validation metric
- 선택 규칙
- optimizer state 보존 여부
- 학습 재개 가능 여부
- model weight digest

inference artifact와 training checkpoint는 같지 않을 수 있다. optimizer state와 gradient buffer는 재학습에는 필요하지만 serving에는 불필요하다.

## 8. model artifact bundle

모델 파일 하나는 완전한 release unit이 아니다. 다음을 하나의 bundle로 관리한다.

```text
model-bundle/
├── manifest.json
├── model.bin 또는 model-specific file
├── input-schema.json
├── preprocessing.json 또는 code reference
├── label-map.json
├── decision-policy.json
├── environment.json
├── evaluation.json
├── model-card.md
└── checksums.json
```

### manifest가 답해야 하는 질문

- bundle format version은 무엇인가?
- model과 preprocessing version은 무엇인가?
- 어떤 input schema를 기대하는가?
- 출력의 의미와 class order는 무엇인가?
- 어떤 threshold가 어떤 action에 연결되는가?
- 어떤 evaluation report와 dataset에서 승인됐는가?
- 이전 version과 호환되는가?

### serialization은 경계다

모델 serialization 형식 중에는 load 과정에서 코드를 실행할 수 있는 것이 있다. 신뢰할 수 없는 artifact를 그대로 load하지 않는다. artifact source, digest, signature, 허용 형식과 실행 격리를 운영 계약으로 둔다. 이 문서는 일반 위험을 지적하며 상세 공급망·sandbox 설계는 `cybersecurity`와 `platform-engineering`의 소유다.

## 9. 실험 비교

### 한 번에 여러 변수를 바꾸지 않는다

모델 구조, feature, split과 metric을 동시에 바꾸면 개선 원인을 알 수 없다. 실험 표에 다음을 둔다.

| run | 변경 가설 | 고정한 입력 | 변경한 입력 | validation 결과 | 실패·해석 |
|---|---|---|---|---|---|
| A | baseline | split·metric | 없음 | ... | ... |
| B | regularization | A와 동일 | penalty | ... | ... |
| C | feature set | A와 동일 | feature schema | ... | ... |

### 최고 점수만 보존하지 않는다

실패한 실험도 다음 이유로 가치가 있다.

- 이미 시도한 경로를 반복하지 않는다.
- data·model bug를 나중에 추적한다.
- 결과가 우연인지 비교한다.
- 선택하지 않은 대안의 근거를 남긴다.

모든 임시 로그를 영구 보존할 필요는 없다. 의사결정에 영향을 준 run, 대표 실패와 release candidate는 보존 정책을 정한다.

### 반복 비교의 위험

validation set을 수십 번 보며 선택하면 validation에도 과적합한다. 다음을 사용한다.

- 탐색 예산과 종료 조건
- nested validation 또는 별도 holdout
- 실험 family와 비교 횟수 기록
- 사후 가설과 사전 가설 구분
- 작은 차이보다 안정성·복잡도·비용 고려

## 10. notebook의 위치

notebook은 탐색과 시각화에 유용하지만 실행 순서와 숨은 상태가 재현성을 약하게 만들 수 있다.

권장 경계:

```text
notebook
- 질문 탐색
- 표와 plot 확인
- 오류 사례 조사

module·CLI
- dataset 생성
- preprocessing
- training
- evaluation
- artifact export
```

notebook이 release 결과를 만든다면 clean kernel에서 처음부터 실행하고, 핵심 로직은 import 가능한 module로 이동한다.

## 11. 실패 패턴

### 결과 파일만 있고 입력이 없다

점수를 다시 계산하거나 data drift와 비교할 수 없다.

### config는 저장했지만 기본값이 변한다

실행 당시 확정된 resolved config를 저장한다.

### best checkpoint가 test에 의해 선택됐다

final test의 독립성이 사라진다.

### preprocessing code와 model이 따로 version된다

offline training과 inference 입력이 달라진다.

### artifact 이름을 덮어쓴다

과거 report가 어떤 model을 가리키는지 잃는다. content digest 또는 immutable version을 사용한다.

### log에 민감한 row를 그대로 기록한다

재현성과 개인정보 보호를 함께 설계해야 한다. row ID, 통계와 접근 제한을 사용한다.

## 12. 검토 체크리스트

### 실행 전

- [ ] problem·dataset·split version이 고정됐다.
- [ ] test set을 selection에 사용하지 않는다.
- [ ] config와 seed가 구조화돼 있다.
- [ ] 실행 환경과 code revision을 기록한다.
- [ ] checkpoint 선택 규칙이 사전에 정해졌다.

### 실행 후

- [ ] prediction과 row identity를 연결할 수 있다.
- [ ] metric과 slice를 다시 계산할 수 있다.
- [ ] 선택한 artifact digest가 report에 있다.
- [ ] 실패 run과 선택하지 않은 대안의 이유가 남아 있다.
- [ ] bundle에 schema·preprocessing·label map·decision policy가 포함됐다.

### release 전

- [ ] 새 환경에서 bundle을 load하고 smoke inference를 수행했다.
- [ ] training pipeline 없이도 inference contract를 검사할 수 있다.
- [ ] model card와 monitoring plan이 해당 artifact version을 가리킨다.
- [ ] 이전 version과 rollback 경로가 있다.

## 누적 실습 연결

4·6단계의 experiment report는 같은 `dataset_sha256`, `split_sha256`, feature schema와 evaluation contract를 참조해야 한다. 7단계에서는 선택한 run을 [`model-bundle`](../../exercises/model-lifecycle/templates/model-bundle-manifest.json) 형식으로 묶는다. 구조 검사기는 digest 형식과 필수 metadata를 확인하지만 실제 학습 재현성은 학습자가 실행 기록으로 증명해야 한다.
