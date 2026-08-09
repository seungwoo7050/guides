# `machine-learning` 계약 추적 지도

이 문서는 최신 `main`의 `machine-learning` 완성 목표 계약을 실제 학습 근거에 대응한다. 파일 존재나 자동 검사 통과만으로 교육적 완성을 주장하지 않으며, 마지막 열의 사람 검토 질문까지 확인한다.

| 소유 범위 | 개념 설명 | 단계 실습과 대표 실패 | 누적 종료 과제 | 종료 능력 | 사람 검토 한계 |
|---|---|---|---|---|---|
| 데이터 분리와 평가 | 문제·dataset·split·baseline 문서, validation·uncertainty 문서 | model lifecycle 1~5단계; entity overlap, future feature, test 재사용, threshold 오답 | Capstone A와 C | 데이터와 baseline을 정의한다; 작은 모델을 평가·개선한다 | split이 실제 배포 population과 action을 모사하는지는 도메인 검토가 필요하다. |
| 손실·최적화·일반화 | 학습·risk·bias/variance 문서, training loop·debugging 문서 | lifecycle 4~6단계와 gradient check; 학습률 발산, mode 혼동, last checkpoint 오답 | Capstone B | 작은 모델을 학습·평가·개선한다 | 작은 합성 데이터의 수치 결과를 실제 dataset이나 hardware로 일반화할 수 없다. |
| 신경망·attention·transformer | neural network 4개 문서와 modern model의 embedding·attention 문서 | lifecycle 6단계와 modern model release 1~2단계; mask 방향, softmax axis, padding·tokenizer 불일치 | Capstone B와 D | 작은 모델을 학습·평가·개선한다 | 작은 CPU attention fixture는 대형 transformer의 품질·비용·최적화를 증명하지 않는다. |
| fine-tuning과 모델 artifact | transfer·fine-tuning 문서와 experiment·artifact 문서 | modern model release 3~4단계 및 lifecycle 7단계; test 기반 선택, base identity 없는 delta, regression 누락 | Capstone C와 D | 작은 모델을 개선한다; 재현 가능한 모델 artifact를 제공한다 | toy partial fine-tuning은 foundation model의 license·compute·behavior 위험을 대신 검증하지 않는다. |
| 재현 가능한 inference와 모델 카드 | inference·monitoring·risk 문서 | lifecycle 7~8단계와 modern release 4단계; digest 불일치, invalid-input coercion, rollback 누락 | Capstone A, C와 D | 재현 가능한 모델 artifact와 추론 인터페이스를 제공한다 | clean-process smoke와 golden fixture는 실제 서비스의 latency·보안·운영 가능성을 증명하지 않는다. |

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
