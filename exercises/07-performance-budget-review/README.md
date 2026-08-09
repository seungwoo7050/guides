# 07. 성능 예산 검토

## 목표

target device의 frame·memory·loading profile을 읽고 평균 FPS가 아니라 critical path, percentile, hitch, resident/peak와 representative workload로 병목과 품질 단계를 결정한다.

## 입력

- [`inputs/target-profile.json`](inputs/target-profile.json)
- [`inputs/frame-samples.csv`](inputs/frame-samples.csv)
- [`inputs/memory-samples.csv`](inputs/memory-samples.csv)
- [`inputs/load-samples.csv`](inputs/load-samples.csv)

## 제출

- [`template/performance-review.md`](template/performance-review.md)
- [`template/budget-decision.csv`](template/budget-decision.csv)

## 대표 오답

- editor/development machine 결과를 target 결과로 사용한다.
- FPS 평균 하나만 보고 p95/p99 hitch를 숨긴다.
- CPU와 GPU 시간을 더해 frame time을 계산한다.
- resident memory와 transient peak를 구분하지 않는다.
- 품질 저하를 subsystem별 독립 toggle로 만들어 조합 폭발을 만든다.

## 사람 검토 질문

1. workload가 실제 player path와 worst representative case를 포함하는가?
2. CPU/GPU 중 누가 critical path인지 evidence가 있는가?
3. thermal/warm-state 결과를 cold-start와 구분했는가?
4. load spike와 gameplay steady-state를 구분했는가?
5. quality tier가 접근성·gameplay rule을 깨지 않는가?

## 완료 기준

- frame p50/p95/p99와 hitch를 산출한다.
- memory resident/peak와 loading p95를 budget과 비교한다.
- 최소 두 개의 변경 가설과 반증 profile을 작성한다.
- low/medium/high scalability 계약을 제출한다.
