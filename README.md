# Machine Learning 모델 개발 가이드

데이터로 문제를 표현하고, 재현 가능한 baseline을 세우고, 고전적 모델과 신경망을 학습·평가한 뒤, 모델 artifact와 사용 한계를 전달하는 과정이다.

이 저장소는 수식 사전이나 프레임워크 API 목록이 아니다. 모델 하나의 점수를 높이는 것보다 다음 흐름을 끝까지 연결하는 데 초점을 둔다.

```text
문제와 의사결정을 정의한다
→ 데이터와 label의 생성 과정을 기록한다
→ 누출 없는 split과 baseline을 만든다
→ 모델을 학습하고 실패 사례를 분석한다
→ 독립된 평가와 사용 임계값을 정한다
→ 재현 가능한 artifact와 문서를 전달한다
→ 운영 중 품질 변화와 재학습 조건을 설계한다
```

## 이 브랜치의 위치

이 브랜치는 `field-entry`다. 필수 기반은 [`python`](https://github.com/seungwoo7050/guides/tree/python), 권장 기반은 [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms)다. Python 문법·패키징·일반 테스트와 알고리즘 정확성·복잡도는 여기서 다시 가르치지 않고 모델 개발 실패를 해석하는 데 필요한 접점만 사용한다.

인접 경로는 다음과 같이 구분한다.

- 장기간 데이터 수집·CDC·backfill·lineage: [`data-engineering`](https://github.com/seungwoo7050/guides/tree/data-engineering)
- 모델을 tool·memory·workflow에 연결하는 시스템: [`agentic-systems`](https://github.com/seungwoo7050/guides/tree/agentic-systems)
- GPU·SIMD·메모리 계층: [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)
- 여러 팀의 공용 ML 실행 경로: [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- 게임 상태·플레이 이벤트에 모델을 연결하는 프로젝트: [`game-development`](https://github.com/seungwoo7050/guides/tree/game-development)

일반적인 다음 심화 브랜치는 `data-engineering`이다. 위 `connects` 관계는 협업 접점이며 필수 선행이나 자동 후속 순서를 뜻하지 않는다.

이 브랜치는 **모델 개발**을 소유한다.

- 데이터 분리와 평가
- 손실·최적화·일반화
- 신경망·attention·transformer
- fine-tuning과 모델 artifact
- 재현 가능한 inference와 모델 카드

문제 정의, label 계약, 고전적 모델, calibration, monitoring 같은 세부 단원은 이 다섯 책임을 하나의 실험 흐름으로 연결한다. 반대로 대규모 데이터 파이프라인 운영, 에이전트 도구 실행, 분산 GPU 시스템 전체와 제품 웹 개발은 소유하지 않는다. 문서·실습·대표 실패·capstone·종료 능력의 대응은 [`계약 추적 지도`](reference/contract-traceability.md)에서 확인한다.

## 지원 환경

- 필수 문서·예제·검증: Python 3.11 이상, 외부 패키지와 네트워크 불필요
- 선택 구현 프로필: NumPy 2.x, scikit-learn 1.x, PyTorch 2.x
- GPU: 필요 없음. 모든 필수 과제는 CPU와 작은 합성 데이터로 설계한다.
- 운영체제: Linux 또는 macOS 권장. 문서와 Python 검사는 다른 환경에서도 실행할 수 있다.

선택 구현 패키지는 [`requirements-reference.txt`](requirements-reference.txt)에 범위만 기록한다. 저장소 검증은 이를 자동 설치하지 않는다. 패키지 설치와 CUDA 환경은 학습자의 실행 환경 책임이다.

## 시작

```sh
./prepare.sh
./verify.sh
```

또는 다음 명령을 사용한다.

```sh
make prepare
make check
make quality-check
make verify
```

`prepare.sh`는 source tree나 Git index를 바꾸지 않고 `.guide/machine-learning/prepared.json`에 HEAD·index·source·workspace fingerprint와 Python 판본을 기록한다. `verify.sh`는 저장소 밖 임시 복사본에서 문서 링크, 예제, 합성 dataset 재생성, split 불변식, 두 reference, starter·known-bad와 artifact mutation을 제한된 wall/CPU 시간으로 검사한다. 검사 로그는 새 `/tmp` 파일에 남고 기존 `VERIFY_LOG`는 덮어쓰지 않는다. 학습자의 `workspace/`는 만들거나 덮어쓰거나 삭제하지 않는다.

## 읽기 순서

전체 경로와 선택 경로는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에 있다.

### 1. 문제와 데이터

1. [모델이 아니라 의사결정 문제부터 정의하기](docs/01-framing-and-data/01-ml-system-and-problem-framing.md)
2. [Dataset 계약과 문서화](docs/01-framing-and-data/02-dataset-contracts-and-documentation.md)
3. [Split, sampling과 데이터 누출](docs/01-framing-and-data/03-splits-leakage-and-sampling.md)
4. [Baseline, metric과 decision rule](docs/01-framing-and-data/04-baselines-metrics-and-decision-rules.md)
5. [필요한 수학과 수치 계약](docs/01-framing-and-data/05-math-and-numerical-contracts.md)

### 2. 학습과 일반화

1. [Loss, risk와 학습](docs/02-learning-and-generalization/01-loss-risk-and-learning.md)
2. [Generalization, bias·variance와 regularization](docs/02-learning-and-generalization/02-generalization-bias-variance-and-regularization.md)
3. [Validation, model selection과 uncertainty](docs/02-learning-and-generalization/03-validation-model-selection-and-uncertainty.md)
4. [인과, 분포 변화와 예측의 한계](docs/02-learning-and-generalization/04-causality-shift-and-prediction-limits.md)

### 3. 고전적 머신러닝

1. [선형 모델](docs/03-classical-models/01-linear-models.md)
2. [Tree, ensemble과 nearest neighbors](docs/03-classical-models/02-trees-ensembles-and-neighbors.md)
3. [Clustering, anomaly detection과 차원 축소](docs/03-classical-models/03-unsupervised-learning-and-dimensionality.md)
4. [Preprocessing pipeline과 해석](docs/03-classical-models/04-preprocessing-pipelines-and-interpretation.md)

### 4. 신경망

1. [Tensor, autodiff와 계산 그래프](docs/04-neural-networks/01-tensors-autodiff-and-computation-graphs.md)
2. [신경망과 표현 학습](docs/04-neural-networks/02-neural-networks-and-representations.md)
3. [Training loop와 최적화](docs/04-neural-networks/03-training-loop-and-optimization.md)
4. [학습 실패 디버깅](docs/04-neural-networks/04-debugging-neural-training.md)

### 5. 현대 모델

1. [Embedding과 tokenization](docs/05-modern-models/01-embeddings-and-tokenization.md)
2. [Attention과 transformer](docs/05-modern-models/02-attention-and-transformers.md)
3. [Pretraining, transfer와 fine-tuning](docs/05-modern-models/03-pretraining-transfer-and-fine-tuning.md)
4. [생성 모델과 평가](docs/05-modern-models/04-generative-models-and-evaluation.md)

### 6. 모델 수명 주기

1. [실험, 재현성과 artifact](docs/06-model-lifecycle/01-experiments-reproducibility-and-artifacts.md)
2. [Inference 계약과 전달 경계](docs/06-model-lifecycle/02-inference-contracts-and-delivery.md)
3. [Monitoring, drift와 retraining](docs/06-model-lifecycle/03-monitoring-drift-and-retraining.md)
4. [위험 관리와 model card](docs/06-model-lifecycle/04-risk-documentation-and-model-cards.md)

## 누적 실습

[`exercises/model-lifecycle`](exercises/model-lifecycle/README.md)는 합성된 이탈 예측 문제를 사용한다. 미완성 starter와 단계별 산출물 계약, dataset·split fixture, 문서 template, 비교 가능한 CPU reference와 제출 검사기를 제공한다.

| 단계 | 핵심 책임 | 권장 산출물 |
|---:|---|---|
| 1 | 문제·관측 단위·결정 시점 고정 | `reports/problem-contract.md` |
| 2 | dataset card와 group-aware split 검증 | `reports/dataset-card.md`, `reports/split-audit.json` |
| 3 | dummy·rule baseline과 metric 계약 | `reports/baseline.json` |
| 4 | 누출 없는 preprocessing·고전적 모델 비교 | `reports/classical-experiments.jsonl` |
| 5 | threshold·calibration·slice 오류 분석 | `reports/evaluation.json` |
| 6 | 작은 신경망과 training trace | `reports/neural-experiment.json` |
| 7 | model bundle과 inference contract | `artifacts/model-bundle/` |
| 8 | model card·monitoring·rollback 계획 | `reports/model-card.md`, `reports/monitoring-plan.md` |

[`exercises/modern-model-release`](exercises/modern-model-release/README.md)는 현대 모델 단원의 핵심 경계를 네 단계로 누적한다. 로컬 toy base와 tokenizer로 attention 불변식을 관찰하고, frozen head와 partial fine-tuning을 같은 validation 계약에서 비교한 뒤 base identity·adapter·golden inference를 하나의 release bundle로 묶는다. 이 실습은 외부 model download나 GPU를 요구하지 않는다.

| 단계 | 핵심 책임 | 권장 산출물 |
|---:|---|---|
| 1 | tokenizer와 base의 version·digest 계약 | `reports/01-tokenizer-contract.json` |
| 2 | causal mask·shape·softmax axis 불변식 | `reports/02-attention-invariants.json` |
| 3 | frozen·partial transfer의 validation-only 선택 | `reports/03-transfer-comparison.json` |
| 4 | base regression·bundle·golden inference·model card | `artifacts/bundle/`, `reports/04-release-review.md` |

작업 공간 생성:

```sh
./scripts/new-workspace.sh
```

제출 구조 검사:

```sh
python3 scripts/check-submission.py --workspace exercises/model-lifecycle/workspace --stage 1
```

검사기는 파일 존재와 문서·JSON 계약을 확인할 뿐 모델 품질을 대신 판정하지 않는다. metric의 타당성, 오류 사례 해석과 모델 선택 근거는 리뷰 대상이다.

## 종료 능력

필수 경로와 누적 실습을 완료하면 다음을 할 수 있어야 한다.

- 예측 단위, 관측 시점, label window와 실제 decision을 분리한다.
- dataset의 출처·포함 기준·누락·대표성·사용 제한을 기록한다.
- entity·time·group 경계를 고려해 train·validation·test를 분리하고 누출을 조사한다.
- baseline과 비용 기반 metric을 세우고 확률 예측과 최종 action threshold를 구분한다.
- 고전적 모델과 작은 신경망을 같은 평가 계약에서 비교한다.
- training curve, gradient, 입력·label과 split을 근거로 학습 실패를 디버깅한다.
- embedding, self-attention과 transformer의 상태와 shape를 설명한다.
- 실험 입력, 코드, 환경, artifact와 평가 결과를 연결한다.
- 모델 파일만이 아니라 preprocessing·schema·version·model card·monitoring 계획을 함께 전달한다.

이 종료점은 대규모 모델 연구자, 분산 학습 플랫폼 운영자나 특정 산업의 모델 책임자를 완성한다는 뜻이 아니다. 실제 dataset과 프로젝트에서 반복적으로 가설을 검증하고 실패를 운영한 경험이 이후 전문성을 만든다.
