# Clustering, anomaly detection과 차원 축소

Unsupervised learning은 label이 없다는 이유로 자유로운 탐색이 아니다. 정답이 직접 주어지지 않으므로 **목적, representation, distance와 평가 기준을 더 명확히 정의해야 한다.**

## 1. 목적을 먼저 정한다

“데이터를 clustering한다”는 목표가 아니다.

가능한 목적:

- 사람 검토를 위한 유사 사례 묶기
- dataset coverage와 source 차이 조사
- 검색·추천용 representation 압축
- 비정상 후보 우선순위화
- downstream supervised model의 feature 생성
- 시각화와 가설 생성

같은 algorithm 결과도 목적에 따라 좋은지 나쁜지가 달라진다.

## 2. Representation과 distance

Clustering은 raw object가 아니라 선택한 representation에서 수행된다.

```text
원본 객체
→ feature/embedding
→ scaling·normalization
→ distance/similarity
→ cluster
```

Representation이 바뀌면 cluster 의미도 바뀐다. Category를 숫자로 encoding해 Euclidean distance를 사용하면 가짜 순서가 생길 수 있다.

## 3. K-means

각 point를 가장 가까운 centroid에 할당하고 within-cluster squared distance를 줄인다.

가정과 특성:

- Euclidean geometry
- 대략 구형이고 비슷한 scale의 cluster에 유리
- `k`를 외부에서 정함
- initialization과 scaling에 민감
- outlier 영향

`k`는 elbow plot만으로 자동 결정하지 않는다. Downstream use, stability와 domain interpretability를 함께 본다.

## 4. Hierarchical clustering

Point 또는 cluster를 가까운 순서로 합치거나 나눈다. Dendrogram으로 여러 resolution을 볼 수 있다.

Linkage 선택이 결과를 바꾼다.

- single linkage: chain에 민감
- complete linkage: compact cluster 선호
- average linkage: 평균 거리
- Ward: squared variance 증가 최소화

큰 dataset에서는 계산·메모리 비용을 확인한다.

## 5. Density-based clustering

밀도가 높은 영역을 cluster로 보고 sparse 영역을 noise로 처리한다.

장점:

- 비구형 cluster 가능
- noise point 표시

한계:

- density scale hyperparameter
- density가 다른 cluster를 동시에 처리하기 어려움
- 고차원 distance 문제

## 6. Clustering 평가

### Internal metric

Silhouette, within-cluster distance처럼 representation과 cluster 구조만 본다. 높은 값이 업무상 유용성을 보장하지 않는다.

### External label

알려진 category와 비교할 수 있지만 cluster가 그 label을 복제해야 한다는 가정을 내포한다.

### Stability

Seed·sample·기간을 바꿔 cluster assignment와 prototype이 유지되는지 본다.

### Downstream utility

검색 품질, 사람 review 시간, supervised model 개선처럼 실제 사용 결과를 평가한다.

### Qualitative review

대표 sample과 경계 sample을 domain 전문가가 검토한다. 예쁜 2D plot만으로 의미를 주장하지 않는다.

## 7. Principal Component Analysis

PCA는 분산을 많이 보존하는 직교 방향으로 data를 투영한다.

주의:

- scaling에 민감
- 큰 분산이 중요한 정보라는 가정
- linear transformation
- component 부호는 임의적일 수 있음
- explained variance가 prediction utility와 같지 않음

PCA를 visualization에 사용한 2D 구조를 원래 고차원 distance의 증거로 해석하지 않는다.

## 8. Nonlinear visualization

t-SNE, UMAP 같은 방법은 local neighborhood 시각화에 유용할 수 있다. Parameter와 seed에 따라 plot이 크게 변할 수 있고 global distance와 cluster size를 보존하지 않을 수 있다.

다음 주장을 피한다.

```text
2D plot에서 떨어져 있으므로 실제로 완전히 다른 집단이다.
```

원래 representation에서의 metric과 독립 검사를 함께 사용한다.

## 9. Anomaly detection

Anomaly는 “드문 것”과 같지 않다. 업무상 중요한 이상 상태를 정의한다.

- point anomaly
- contextual anomaly
- collective anomaly
- novelty detection

Label이 적으면 precision을 추정하기 어렵다. 사람 review capacity와 false alarm 비용을 중심으로 평가한다.

## 10. Density와 outlier score

- distance to neighbors
- isolation-based score
- one-class boundary
- reconstruction error

각 score는 다른 정상성 가정을 가진다. High-dimensional data에서 distance와 density가 불안정할 수 있다.

## 11. Autoencoder와 reconstruction

신경망이 입력을 압축·복원하도록 학습하고 reconstruction error를 anomaly score로 쓸 수 있다.

한계:

- anomaly도 잘 복원할 수 있음
- 정상 data의 rare pattern을 anomaly로 표시
- loss가 업무상 중요한 feature를 적절히 가중하지 않음
- architecture와 training이 복잡함

고전적 baseline과 사람 review 결과 없이 autoencoder를 기본 선택하지 않는다.

## 12. Leakage와 contamination

Unsupervised preprocessing도 전체 dataset에서 fit하면 leakage가 될 수 있다.

- PCA를 전체 data에 fit
- vocabulary를 test 포함 전체 corpus에서 생성
- clustering prototype을 test 포함 data로 학습
- anomaly threshold를 test에 맞춤

Downstream 평가가 있다면 train 안에서 fit하고 validation/test를 transform한다.

## 13. Cluster를 label로 고정할 때

Cluster ID는 algorithm·seed·data version에 따라 바뀔 수 있다. 운영 feature나 사용자 segment로 사용하려면 다음을 고정한다.

- model version
- preprocessing
- cluster matching·migration
- unknown·new data 처리
- 의미 있는 이름과 owner
- 재학습 시 downstream 영향

`cluster_3` 자체는 안정적인 업무 개념이 아니다.

## 14. 대표적인 실패

### Plot-driven storytelling

2D visualization에서 보이는 모양에 사후 설명을 붙인다.

### K를 metric 하나로 결정

Silhouette 최고값을 실제 segment 수로 본다.

### Scaling 누락

단위가 큰 feature가 모든 distance와 component를 지배한다.

### Anomaly score = fraud

Rare pattern을 실제 위험 label로 해석한다.

### Test 포함 representation

Unsupervised이므로 test를 사용해도 된다고 생각한다.

## 15. 리뷰 질문

- Unsupervised 결과가 어떤 후속 action을 돕는가?
- Representation과 distance가 domain 의미를 갖는가?
- Scaling·missing·category 처리가 일관적인가?
- Internal metric 외에 stability·downstream·human review가 있는가?
- Visualization이 보존하지 않는 구조를 알고 있는가?
- Anomaly threshold가 review capacity와 연결되는가?
- Cluster version 변화가 downstream 사용자에게 어떻게 전달되는가?
- Evaluation test를 representation 학습에 섞지 않았는가?

## 선택 실습

합성 dataset의 numeric feature를 standardize한 뒤 PCA 또는 clustering을 적용하고, split·seed 변화에서 결과 안정성을 기록한다. 이 결과를 label prediction의 증거로 사용하지 않고 dataset 탐색 보고서로 분리한다.
