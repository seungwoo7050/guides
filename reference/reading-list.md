# 참고 자료

필수 문서는 이 저장소 안에서 완결되도록 작성했다. 아래 자료는 원리·API·위험 관리의 원문을 더 깊게 확인할 때 사용한다. 버전이 있는 library 문서는 자신의 환경과 맞는 판본을 선택한다.

## 기계학습과 평가

- scikit-learn User Guide: supervised learning, model selection, metrics, preprocessing과 common pitfalls
  - <https://scikit-learn.org/stable/user_guide.html>
- scikit-learn `Common pitfalls and recommended practices`
  - <https://scikit-learn.org/stable/common_pitfalls.html>
- scikit-learn model evaluation
  - <https://scikit-learn.org/stable/modules/model_evaluation.html>

## 신경망과 자동 미분

- PyTorch documentation
  - <https://docs.pytorch.org/docs/stable/index.html>
- PyTorch autograd mechanics
  - <https://docs.pytorch.org/docs/stable/notes/autograd.html>
- PyTorch reproducibility notes
  - <https://docs.pytorch.org/docs/stable/notes/randomness.html>

## Transformer와 현대 모델

- *Attention Is All You Need*
  - <https://arxiv.org/abs/1706.03762>
- *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding*
  - <https://arxiv.org/abs/1810.04805>

논문 구조를 그대로 제품 설계로 일반화하지 않는다. Objective·dataset·compute·evaluation이 현재 문제와 어떻게 다른지 함께 기록한다.

## 데이터·모델 문서화

- *Datasheets for Datasets*
  - <https://arxiv.org/abs/1803.09010>
- *Model Cards for Model Reporting*
  - <https://arxiv.org/abs/1810.03993>
- *Hidden Technical Debt in Machine Learning Systems*
  - <https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems>

## 위험 관리

- NIST AI Risk Management Framework
  - <https://www.nist.gov/itl/ai-risk-management-framework>
- NIST AI RMF Playbook
  - <https://airc.nist.gov/airmf-resources/playbook/>

이 자료는 법률 자문이나 특정 산업 승인 기준을 대신하지 않는다. 실제 프로젝트는 해당 조직·국가·도메인의 정책과 전문가 검토를 따른다.

## 읽는 방법

새 자료를 읽을 때 다음을 기록한다.

1. 어떤 문제와 population을 전제로 하는가?
2. 어떤 data와 split을 사용하는가?
3. loss와 evaluation metric은 무엇인가?
4. 비교 baseline과 ablation은 충분한가?
5. 결과가 어떤 환경까지 일반화되는가?
6. 재현에 필요한 code·artifact·compute가 공개돼 있는가?
7. 현재 프로젝트에 옮기면 달라지는 계약은 무엇인가?
