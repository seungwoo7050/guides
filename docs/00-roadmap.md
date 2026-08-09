# Machine Learning 학습 지도

이 가이드는 모델 API를 순서대로 호출하는 과정이 아니다. **어떤 관측으로 어떤 미래 결과를 예측하며, 그 예측이 어떤 의사결정을 바꾸고, 데이터와 평가가 그 주장을 어디까지 지지하는지**를 연결하는 과정이다.

## 대상 독자

다음 중 하나에 해당하면 적합하다.

- Python으로 프로그램은 작성하지만 dataset split, baseline, metric과 data leakage를 체계적으로 설명하기 어렵다.
- scikit-learn이나 PyTorch 예제를 실행해 봤지만 모델 선택 근거와 실패 분석이 약하다.
- 신경망·attention·transformer 용어를 알고 있으나 tensor shape, 학습 objective와 평가 경계를 연결하지 못한다.
- 모델 파일을 만들 수는 있지만 preprocessing, artifact version, model card와 monitoring까지 전달해 본 적이 없다.
- 에이전트나 AI 제품을 만들기 전에 모델 자체가 어떻게 학습되고 평가되는지 이해하고 싶다.

## 선행지식

### 필수

- [`python`](https://github.com/seungwoo7050/guides/tree/python)의 종료 능력 또는 동등한 경험
  - 함수·모듈·예외와 타입 경계를 읽는다.
  - CSV·JSON 파일과 CLI를 다룬다.
  - 작은 테스트를 실행하고 실패를 해석한다.

### 권장

- [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms)의 계약·복잡도·검증 사고방식
- 중학교 수준의 대수와 함수 그래프
- 평균·분산·확률이라는 용어에 대한 기초 경험

미적분, 선형대수와 확률론 전체를 먼저 완료할 필요는 없다. [필요한 수학과 수치 계약](01-framing-and-data/05-math-and-numerical-contracts.md)에서 모델 구현을 읽는 데 필요한 범위만 제공한다. 증명 중심 수학이나 통계 추론 전문 과정은 이 브랜치의 범위가 아니다.

## 학습 목표

필수 경로를 완료하면 다음 반복을 스스로 수행할 수 있어야 한다.

```text
업무 문제와 action을 정의한다
→ 관측 단위·시점·label window를 고정한다
→ dataset provenance와 제한을 기록한다
→ 누출 없는 split과 baseline을 만든다
→ 모델·hyperparameter를 validation에서 비교한다
→ final test와 slice에서 주장을 제한한다
→ artifact·inference·monitoring 계약을 전달한다
```

## 이 가이드가 소유하는 범위

```text
데이터 분리와 평가
손실·최적화·일반화
신경망·attention·transformer
fine-tuning과 모델 artifact
재현 가능한 inference와 모델 카드
```

문제 framing, dataset·label, baseline·metric·threshold, 고전적 모델과 monitoring은 위 책임을 종단 간 모델 개발 흐름으로 연결하는 구성 요소다. [`계약 추적 지도`](../reference/contract-traceability.md)는 각 소유 범위를 개념 문서, 실습, 대표 실패, capstone과 종료 능력에 대응한다.

## 다른 브랜치가 소유하는 범위

- Python 언어·일반 패키징·프로세스·테스트: [`python`](https://github.com/seungwoo7050/guides/tree/python)
- 알고리즘의 정확성·복잡도와 일반 설계 기법: [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms)
- 대규모 데이터 파이프라인, CDC, event time, backfill, replay와 lineage 운영: [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)
- 모델을 API·retrieval·tool·memory·workflow에 연결하고 도구를 실행하는 시스템: [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)
- GPU·SIMD·메모리 계층의 하드웨어 원리: [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)
- 분산 GPU 학습 시스템 전체, 대규모 inference cluster와 조직 공용 실행 경로: [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering) 및 현재 카탈로그 밖의 외부 전문 자료
- UI·인증·업무 흐름을 포함한 제품 웹 개발: [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app)
- 게임 loop·상태·자산에 모델 결과를 연결하는 제품 개발: [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)
- prompt injection, model extraction, poisoning과 AI 공격·방어의 전문 과정: [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity)와 후속 교차 프로젝트

겹치는 용어가 있어도 책임은 다르다. 예를 들어 이 브랜치의 data drift는 모델 가정과 평가 집합의 변화에 초점을 두고, `data-engineering`의 freshness는 pipeline이 정해진 시간 안에 데이터를 전달했는지에 초점을 둔다.

## 카탈로그 관계와 트랙 위치

| 관계 | 브랜치 |
|---|---|
| 종류 | `field-entry` |
| 필수 | `python` |
| 권장 | `algorithms` |
| 협업 접점 | `data-engineering`, `agentic-systems`, `computer-architecture`, `platform-engineering`, `game-development` |
| 일반 후속 | `data-engineering` |

`machine-learning` 트랙의 기본 선형 경로는 `git → python → algorithms → machine-learning`이다. `game-data-ml` 트랙에서는 `git → python → algorithms → game-development → database-systems → data-engineering → machine-learning` 순서로 모델 개발을 게임 데이터 의사결정에 연결한다.

다른 트랙에서 이 브랜치는 다음처럼 사용된다.

- `agentic-systems`: 권장 인접 기반
- `data-engineering`: 핵심 트랙 뒤 advanced
- `game-client-gameplay`: 선택 advanced
- `game-data-ml`: 필수이며 선형 경로의 종료 지점

트랙의 `recommended`·`advanced` 표기는 이 브랜치의 직접 필수 조건을 늘리지 않는다.

## 필수 학습 지도

### 1부: 문제와 데이터

| 순서 | 문서 | 연결 실습 |
|---:|---|---:|
| 1 | [모델이 아니라 의사결정 문제부터 정의하기](01-framing-and-data/01-ml-system-and-problem-framing.md) | 1단계 |
| 2 | [Dataset 계약과 문서화](01-framing-and-data/02-dataset-contracts-and-documentation.md) | 1·2단계 |
| 3 | [Split, sampling과 데이터 누출](01-framing-and-data/03-splits-leakage-and-sampling.md) | 2단계 |
| 4 | [Baseline, metric과 decision rule](01-framing-and-data/04-baselines-metrics-and-decision-rules.md) | 3·5단계 |
| 5 | [필요한 수학과 수치 계약](01-framing-and-data/05-math-and-numerical-contracts.md) | 3·6단계 |

### 2부: 학습과 일반화

| 순서 | 문서 | 연결 실습 |
|---:|---|---:|
| 6 | [Loss, risk와 학습](02-learning-and-generalization/01-loss-risk-and-learning.md) | 3·4·6단계 |
| 7 | [Generalization, bias·variance와 regularization](02-learning-and-generalization/02-generalization-bias-variance-and-regularization.md) | 4·6단계 |
| 8 | [Validation, model selection과 uncertainty](02-learning-and-generalization/03-validation-model-selection-and-uncertainty.md) | 4·5단계 |
| 9 | [인과, 분포 변화와 예측의 한계](02-learning-and-generalization/04-causality-shift-and-prediction-limits.md) | 5·8단계 |

### 3부: 고전적 머신러닝

| 순서 | 문서 | 연결 실습 |
|---:|---|---:|
| 10 | [선형 모델](03-classical-models/01-linear-models.md) | 4단계 |
| 11 | [Tree, ensemble과 nearest neighbors](03-classical-models/02-trees-ensembles-and-neighbors.md) | 4단계 |
| 12 | [Clustering, anomaly detection과 차원 축소](03-classical-models/03-unsupervised-learning-and-dimensionality.md) | 선택 |
| 13 | [Preprocessing pipeline과 해석](03-classical-models/04-preprocessing-pipelines-and-interpretation.md) | 4·5단계 |

### 4부: 신경망

| 순서 | 문서 | 연결 실습 |
|---:|---|---:|
| 14 | [Tensor, autodiff와 계산 그래프](04-neural-networks/01-tensors-autodiff-and-computation-graphs.md) | 6단계 |
| 15 | [신경망과 표현 학습](04-neural-networks/02-neural-networks-and-representations.md) | 6단계 |
| 16 | [Training loop와 최적화](04-neural-networks/03-training-loop-and-optimization.md) | 6단계 |
| 17 | [학습 실패 디버깅](04-neural-networks/04-debugging-neural-training.md) | 6단계 |

### 5부: 현대 모델

| 순서 | 문서 | 연결 실습 |
|---:|---|---:|
| 18 | [Embedding과 tokenization](05-modern-models/01-embeddings-and-tokenization.md) | 현대 모델 1단계 |
| 19 | [Attention과 transformer](05-modern-models/02-attention-and-transformers.md) | 현대 모델 2단계 |
| 20 | [Pretraining, transfer와 fine-tuning](05-modern-models/03-pretraining-transfer-and-fine-tuning.md) | 현대 모델 3단계 |
| 21 | [생성 모델과 평가](05-modern-models/04-generative-models-and-evaluation.md) | 선택 |

### 6부: 모델 수명 주기

| 순서 | 문서 | 연결 실습 |
|---:|---|---:|
| 22 | [실험, 재현성과 artifact](06-model-lifecycle/01-experiments-reproducibility-and-artifacts.md) | 전 단계 |
| 23 | [Inference 계약과 전달 경계](06-model-lifecycle/02-inference-contracts-and-delivery.md) | 7단계 |
| 24 | [Monitoring, drift와 retraining](06-model-lifecycle/03-monitoring-drift-and-retraining.md) | 8단계 |
| 25 | [위험 관리와 model card](06-model-lifecycle/04-risk-documentation-and-model-cards.md) | 8단계 |

마지막에는 [시스템 종합 검토](90-system-review.md)로 문제·데이터·학습·평가·전달의 근거를 다시 연결한다.

## 권장 경로

### 애플리케이션 개발자가 모델을 올바르게 사용하려는 경우

```text
문제 framing
→ dataset 계약
→ split·leakage
→ baseline·metric·threshold
→ validation·model selection
→ preprocessing pipeline
→ inference contract
→ monitoring·model card
```

신경망 내부 구현은 뒤로 미뤄도 된다. 모델 API를 호출하는 것보다 입력 schema, 평가 집합, threshold와 artifact compatibility를 먼저 이해한다.

### 모델 개발 입문 경로

필수 학습 지도 전체를 순서대로 진행한다. 고전적 모델에서 baseline과 split 계약을 익힌 뒤 신경망으로 이동한다. 작은 tabular dataset에 transformer를 적용해 점수를 높이는 것이 목표가 아니다.

### 현대 언어 모델 구조를 이해하려는 경우

```text
필요한 수학과 수치 계약
→ loss·optimization
→ tensor·autodiff
→ 신경망과 training loop
→ embedding·tokenization
→ attention·transformer
→ pretraining·fine-tuning
→ 생성 모델 평가
```

이 경로를 완료해도 agent loop, tool permission과 RAG 시스템 운영은 다루지 않는다. 그 범위는 [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)로 이동한다.

### 실무 모델 release를 검토하려는 경우

```text
문제 framing
→ split·leakage
→ baseline·metric·threshold
→ validation·uncertainty
→ experiment·artifact
→ inference contract
→ monitoring·model card
→ model release review capstone
```

## Capstone 선택

### A. 재현 가능한 분류기

[재현 가능한 분류기](07-capstones/01-reproducible-classifier.md)는 모든 독자에게 권장한다. 합성 dataset에서 group split, baseline, preprocessing, classical model, threshold와 slice evaluation을 하나의 평가 계약으로 만든다.

### B. 작은 신경망

[작은 신경망](07-capstones/02-small-neural-model.md)은 neural track을 완료한 독자에게 권장한다. 같은 문제에서 고전적 baseline을 이겼다는 주장보다 training trace와 실패 진단을 더 중요하게 평가한다.

### C. 모델 release review

[모델 release review](07-capstones/03-model-release-review.md)는 모델 파일, preprocessing, schema, model card, monitoring과 rollback이 하나의 release unit인지 검토한다. 실제 모델 serving platform 구현은 요구하지 않는다.

### D. Modern-model transfer와 release

[Modern-model transfer와 release](07-capstones/04-modern-model-transfer-release.md)는 tokenizer/base identity, causal attention, frozen·partial fine-tuning 비교, base regression과 adapter bundle을 하나의 근거 사슬로 묶는다. 실제 foundation model의 성능이나 대규모 GPU 운영 적합성은 자동 판정하지 않는다.

누적 구현 계약은 [`exercises/model-lifecycle`](../exercises/model-lifecycle/README.md)과 [`exercises/modern-model-release`](../exercises/modern-model-release/README.md)에 있다.

## 실행 계약

```sh
make prepare
make check
make quality-check
make verify
make clean
```

- `make prepare`: Python 환경과 source fingerprint를 기록한다.
- `make check`: 문서·예제·fixture·exercise 계약을 네트워크 없이 검사한다.
- `make quality-check`: 잘못된 split·dataset 변조·계약 누락뿐 아니라 두 실습의 starter와 9개 known-bad를 검사기가 실제로 거부하는지 확인한다.
- `make verify`: 저장소 밖 격리 복사본에서 전체 검사를 실행하고 source 무변경을 확인한다.
- `make clean`: `.guide/`와 저장소가 만든 cache만 지우며 learner workspace는 보존한다.

## 실습 방법

```text
문서에서 계약과 대표 오답을 읽는다
→ skeleton을 workspace로 복사한다
→ 현재 단계의 산출물만 만든다
→ 구조 검사와 자신의 모델 검사를 실행한다
→ 실패 원인을 보고서에 기록한다
→ 다음 단계에서 이전 판단을 재사용하거나 수정한다
```

작업 공간:

```sh
./scripts/new-workspace.sh
```

단계별 구조 검사:

```sh
python3 scripts/check-submission.py \
  --workspace exercises/model-lifecycle/workspace \
  --stage 4
```

검사기는 보고서가 존재하고 JSON이 기본 schema를 만족하는지 확인한다. model quality, metric 선택의 타당성, leakage 부재와 오류 해석을 자동으로 완전히 증명하지 않는다. 학습자는 실행 기록과 검토 문서를 함께 남겨야 한다.

## 자동화의 한계

- 합성 dataset 검사는 이 저장소의 fixture 계약만 증명한다. 실제 dataset의 대표성·동의·법적 사용 가능성을 증명하지 않는다.
- 동일 seed라도 library release, 장치와 병렬 연산에 따라 수치가 달라질 수 있다.
- 작은 CPU 실습의 성능과 메모리 결과를 대규모 GPU 학습에 일반화할 수 없다.
- model card template 작성은 실제 위험 관리, 도메인 전문가 검토와 사용자 영향 평가를 대신하지 않는다.
- reference 문서와 구조 검사 통과는 모델 선택 근거와 실패 분석의 질을 대신하지 않는다.
