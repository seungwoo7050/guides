# Pretraining, transfer와 fine-tuning

Pretraining은 큰 데이터와 일반 objective로 representation을 학습하고, downstream task에 transfer하는 전략이다. 이미 학습된 모델을 사용한다고 problem·dataset·evaluation 책임이 사라지지 않는다.

## 1. Pretraining objective

예:

- next-token prediction
- masked-token prediction
- contrastive representation
- image reconstruction
- multimodal alignment

Objective가 학습하는 것은 pretraining data와 target 생성 규칙에 유용한 패턴이다. Downstream accuracy, factuality, fairness와 안전성을 직접 최적화하지 않는다.

## 2. Transfer learning

Source task·domain에서 학습한 parameter나 representation을 target task에 재사용한다.

Transfer가 잘 되려면 다음이 관련된다.

- input modality와 representation
- source·target domain 유사성
- label과 objective 관계
- tokenizer·resolution·feature schema
- model capacity
- target data size

큰 source dataset이 항상 positive transfer를 보장하지 않는다. Negative transfer를 baseline으로 확인한다.

## 3. Feature extraction

Pretrained model을 frozen encoder로 사용하고 작은 task head만 학습한다.

장점:

- 적은 compute·memory
- 작은 data에서 안정적일 수 있음
- base model 재사용

한계:

- representation이 target에 맞지 않으면 개선 제한
- tokenizer·preprocessing 호환 필요
- base model artifact가 여전히 큼

## 4. Full fine-tuning

Base parameter 전체를 target data로 update한다.

장점:

- target task에 representation 조정

위험:

- compute·memory
- 작은 data overfitting
- catastrophic forgetting
- base model behavior 변화
- 여러 task별 model copy 관리

Learning rate, layer-wise update와 checkpoint selection을 기록한다.

## 5. Parameter-efficient fine-tuning

Base parameter 대부분을 고정하고 작은 adapter·low-rank parameter 등을 학습한다.

검토:

- base model과 adapter version 결합
- merge 여부
- inference runtime 지원
- adapter 간 호환
- full fine-tuning 대비 quality·latency·storage
- 여러 adapter의 access control

방법 이름보다 release unit과 rollback 경계를 명확히 한다.

## 6. Prompting과 in-context learning의 경계

Model parameter를 바꾸지 않고 입력 예시·instruction으로 behavior를 유도할 수 있다. 이는 model training과 다르지만 evaluation 대상이다.

이 브랜치에서는 다음만 다룬다.

- prompt가 model input distribution 일부라는 점
- few-shot example contamination과 order effect
- output evaluation과 versioning

Tool use, memory, agent loop와 RAG workflow는 `agentic-systems`의 범위다.

## 7. Data selection

Fine-tuning 품질은 sample 수보다 data 계약에 크게 좌우된다.

- target behavior를 대표하는가
- duplicate·template leakage가 있는가
- label guideline과 disagreement
- class·length·language·domain coverage
- negative example과 refusal boundary
- source license·privacy

Synthetic data는 generator model의 오류와 style을 반복할 수 있다. Human·real data와 별도 provenance를 기록한다.

## 8. Catastrophic forgetting

Target task에 맞추며 base capability가 저하될 수 있다.

검사:

- target metric
- base capability regression set
- safety·format·language regression
- representation drift
- parameter update 규모

Target score만 보고 release하지 않는다.

## 9. Continual learning

새 data가 계속 들어올 때 순차 update를 고려할 수 있다.

문제:

- 이전 task forgetting
- label definition 변화
- feedback loop
- evaluation set contamination
- artifact·data lineage

주기적 전체 재학습, replay, adapter 분리 등 전략은 운영 요구에 따라 선택한다. 자동 update는 별도 approval과 rollback이 필요하다.

## 10. Domain adaptation

Source와 target distribution 차이를 줄이려 한다.

- 추가 pretraining
- target-domain fine-tuning
- feature alignment
- importance weighting
- calibration·threshold 조정

Target label이 없으면 실제 품질을 직접 확인하기 어렵다. Proxy metric만으로 성공을 주장하지 않는다.

## 11. Evaluation

비교 대상:

1. no-ML 또는 rule baseline
2. task-specific classical model
3. frozen pretrained feature
4. parameter-efficient fine-tune
5. full fine-tune

같은 split·metric·latency 조건에서 비교한다. Pretraining data contamination 가능성이 있으면 benchmark를 독립된 일반화 근거로 약하게 해석한다.

## 12. Contamination

Pretraining corpus에 evaluation sample 또는 near-duplicate가 포함될 수 있다.

대응:

- source·timestamp가 새로운 evaluation
- canary·held-out private set
- near-duplicate search
- benchmark exposure 기록
- memorization probe

완전한 contamination 부재를 증명하기 어려울 수 있다. Model card에 제한을 기록한다.

## 13. License와 공급망

Pretrained artifact에는 다음을 확인한다.

- model license
- weight·code·tokenizer 각각의 license
- training data 공개 범위와 제한
- commercial·redistribution 조건
- remote custom code 실행 여부
- artifact digest와 source
- dependency vulnerability·serialization format

외부 model을 untrusted binary로 취급하고 load path를 격리한다.

## 14. Release unit

Fine-tuned model release는 다음의 조합이다.

```text
base model ID·digest
+ tokenizer·preprocessor
+ adapter 또는 merged weight
+ configuration
+ inference code/runtime
+ evaluation report
+ model card
```

Adapter 파일 하나만으로 재현 가능한 model이 아니다.

## 15. 비용과 latency

큰 pretrained model은 training cost를 줄여도 inference cost를 늘릴 수 있다.

- parameter memory
- activation·KV cache
- batch throughput
- cold start
- quantization impact
- device availability

작은 task-specific model과 비교한다.

## 16. 대표적인 실패

### Pretrained = evaluated

공개 benchmark 결과를 현재 dataset·언어·action에 그대로 적용한다.

### Fine-tune on test-like examples

평가 실패 사례를 반복 추가하고 같은 test score를 최종 주장으로 사용한다.

### Adapter only artifact

Base·tokenizer version 없이 adapter만 전달한다.

### Target metric만 확인

Base capability·safety·format regression을 보지 않는다.

### Remote code trust

Model load 과정에서 외부 custom code를 검토 없이 실행한다.

## 17. 리뷰 질문

- Pretraining objective와 downstream task가 어떻게 연결되는가?
- Frozen·PEFT·full fine-tuning을 같은 조건에서 비교했는가?
- Target data의 provenance·coverage·license가 명확한가?
- Contamination 가능성과 benchmark exposure를 기록했는가?
- Base capability와 중요한 behavior regression을 검사했는가?
- Base·tokenizer·adapter·runtime이 하나의 release unit인가?
- Inference cost가 작은 baseline보다 정당화되는가?
- 외부 artifact load를 신뢰 경계 안에서 수행하는가?

## 선택 실습

작은 pretrained encoder를 사용할 수 있는 환경이라면 frozen feature와 fine-tuning을 비교한다. 필수 완료 조건은 score가 아니라 data split, base artifact identity, training configuration, regression set와 release bundle을 재현하는 것이다.
