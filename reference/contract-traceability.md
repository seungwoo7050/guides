# `machine-learning` 계약 추적 지도

이 문서는 최신 `main`의 `machine-learning` 완성 목표 계약을 실제 학습 근거에 대응한다. 파일 존재나 자동 검사 통과만으로 교육적 완성을 주장하지 않으며, 마지막 열의 사람 검토 질문까지 확인한다.

| 소유 범위 | 개념 설명 | 단계 실습과 대표 실패 | 누적 종료 과제 | 종료 능력 | 사람 검토 한계 |
|---|---|---|---|---|---|
| 데이터 분리와 평가 | [Split·leakage](../docs/01-framing-and-data/03-splits-leakage-and-sampling.md), [baseline·metric](../docs/01-framing-and-data/04-baselines-metrics-and-decision-rules.md), [validation](../docs/02-learning-and-generalization/03-validation-model-selection-and-uncertainty.md) | [Lifecycle 1~5단계](../exercises/model-lifecycle/README.md), [split audit](../exercises/model-lifecycle/reference/reports/split-audit.json), [평가 trace](../exercises/model-lifecycle/reference/reports/evaluation.json); entity overlap, future feature, test 재사용 | [Capstone A](../docs/07-capstones/01-reproducible-classifier.md), [C](../docs/07-capstones/03-model-release-review.md) | 데이터와 baseline을 정의한다; 작은 모델을 평가·개선한다 | split이 실제 배포 population과 action을 모사하는지는 도메인 검토가 필요하다. |
| 손실·최적화·일반화 | [Loss·risk](../docs/02-learning-and-generalization/01-loss-risk-and-learning.md), [generalization](../docs/02-learning-and-generalization/02-generalization-bias-variance-and-regularization.md), [training loop](../docs/04-neural-networks/03-training-loop-and-optimization.md) | [Lifecycle 4~6단계](../exercises/model-lifecycle/README.md), [neural trace와 실패 진단](../exercises/model-lifecycle/reference/reports/neural-experiment.json); 학습률 발산, mode 혼동, last checkpoint | [Capstone B](../docs/07-capstones/02-small-neural-model.md) | 작은 모델을 학습·평가·개선한다 | 작은 합성 데이터의 수치 결과를 실제 dataset이나 hardware로 일반화할 수 없다. |
| 신경망·attention·transformer | [신경망](../docs/04-neural-networks/02-neural-networks-and-representations.md), [embedding](../docs/05-modern-models/01-embeddings-and-tokenization.md), [attention](../docs/05-modern-models/02-attention-and-transformers.md) | [Lifecycle 6단계](../exercises/model-lifecycle/README.md), [Modern 1~2단계](../exercises/modern-model-release/README.md), [attention 불변식](../exercises/modern-model-release/reference/reports/02-attention-invariants.json); mask 방향, softmax axis, tokenizer 불일치 | [Capstone B](../docs/07-capstones/02-small-neural-model.md), [D](../docs/07-capstones/04-modern-model-transfer-release.md) | 작은 모델을 학습·평가·개선한다 | 작은 CPU attention fixture는 대형 transformer의 품질·비용·최적화를 증명하지 않는다. |
| fine-tuning과 모델 artifact | [Transfer·fine-tuning](../docs/05-modern-models/03-pretraining-transfer-and-fine-tuning.md), [experiment·artifact](../docs/06-model-lifecycle/01-experiments-reproducibility-and-artifacts.md) | [Modern 3~4단계](../exercises/modern-model-release/README.md), [transfer 비교](../exercises/modern-model-release/reference/reports/03-transfer-comparison.json), [adapter manifest](../exercises/modern-model-release/reference/artifacts/bundle/manifest.json); test 기반 선택, base identity 누락, regression 실패 | [Capstone C](../docs/07-capstones/03-model-release-review.md), [D](../docs/07-capstones/04-modern-model-transfer-release.md) | 작은 모델을 개선한다; 재현 가능한 모델 artifact를 제공한다 | toy partial fine-tuning은 foundation model의 license·compute·behavior 위험을 대신 검증하지 않는다. |
| 재현 가능한 inference와 모델 카드 | [Inference 계약](../docs/06-model-lifecycle/02-inference-contracts-and-delivery.md), [monitoring](../docs/06-model-lifecycle/03-monitoring-drift-and-retraining.md), [model card](../docs/06-model-lifecycle/04-risk-documentation-and-model-cards.md) | [Lifecycle 7~8단계](../exercises/model-lifecycle/README.md), [bundle manifest](../exercises/model-lifecycle/reference/artifacts/model-bundle/manifest.json), [reproduction evidence](../exercises/model-lifecycle/reference/artifacts/model-bundle/reproduction.json); checksum 불일치, invalid-input coercion, compatibility 실패 | [Capstone A](../docs/07-capstones/01-reproducible-classifier.md), [C](../docs/07-capstones/03-model-release-review.md), [D](../docs/07-capstones/04-modern-model-transfer-release.md) | 재현 가능한 모델 artifact와 추론 인터페이스를 제공한다 | clean-process smoke와 golden fixture는 실제 서비스의 latency·보안·운영 가능성을 증명하지 않는다. |

## 종료 증거 규칙

각 완료 주장은 다음 identity를 따라야 한다.

```text
dataset·split
→ source revision·configuration·seed
→ experiment run과 선택 근거
→ final evaluation
→ model·preprocessing·schema·policy digest
→ golden inference와 model card
```

자동 검사는 공개 구조, 결정적 fixture와 대표 오답을 확인한다. Metric 선택, 오류 분석, 사용 제한과 release 판단의 타당성은 [`시스템 종합 검토`](../docs/90-system-review.md)와 [`검토 체크리스트`](review-checklists.md)로 사람이 판단한다.
