# 04. 자산 loading 계획

## 목표

logical asset, source file, imported artifact, cooked package, load group과 runtime resident state를 구분하고 target device budget 안에서 arena 진입 경로를 설계한다.

## 입력

- [`inputs/asset-manifest.json`](inputs/asset-manifest.json)
- [`inputs/load-scenarios.json`](inputs/load-scenarios.json)
- [`inputs/memory-budgets.json`](inputs/memory-budgets.json)

## 제출

- [`template/loading-plan.md`](template/loading-plan.md)
- [`template/budget-review.csv`](template/budget-review.csv)

## 대표 오답

- source file path를 persistent gameplay id로 사용한다.
- hard reference 하나로 optional cosmetic bundle 전체를 control-ready 전에 load한다.
- async request 완료 시 owner/generation을 확인하지 않는다.
- unload 요청 뒤 GPU/audio resource가 즉시 해제됐다고 가정한다.
- editor memory를 target device resident memory로 해석한다.

## 사람 검토 질문

1. control-ready와 cosmetic-ready가 분리되는가?
2. critical asset 누락과 optional asset 누락의 fallback이 다른가?
3. dependency cycle과 bundle duplication을 찾았는가?
4. preload·stream·evict 결정이 실제 workload와 budget에 연결되는가?
5. content version과 stable asset id가 save/replay/network와 호환되는가?

## 완료 기준

- arena 진입의 load graph와 gate를 작성한다.
- target device별 resident·transient budget을 계산한다.
- missing/stale/cancelled asset의 fallback과 cleanup을 정의한다.
