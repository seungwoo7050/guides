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

`template/` 파일은 의도적으로 빈 starter다. 원본을 직접 채우지 말고 자신의 작업 디렉터리에 복사한 뒤 모든 빈 cell과 항목을 근거로 완성한다. 제출 뒤에는 다음 예시 해설과 비교한다.

- [`reference/loading-plan.md`](reference/loading-plan.md)
- [`reference/budget-review.csv`](reference/budget-review.csv)

예시 해설은 복사할 유일 정답이 아니다. 다만 transitive dependency 합계, budget 초과와 fixture에 없는 측정값을 `unknown`으로 남기는 판단은 입력에서 결정되므로 일치해야 한다.

## 검증 근거

자동 검사 또는 계산 가능한 증거:

- asset id가 유일하고 dependency graph가 cycle 없이 모두 resolve된다.
- scene closure는 CPU/GPU `13/87 MiB`, player closure는 `31/14 MiB`, control-ready union은 `44/101 MiB`다.
- full cold-entry unique resident addition은 `142/177 MiB`다.
- desktop baseline 포함 full resident는 `332/247 MiB`, handheld는 `262/231 MiB`다.
- handheld control-ready도 baseline 포함 GPU `155 MiB > 128 MiB`이므로 optional cosmetic만 빼서 pass로 만들 수 없다.
- reference CSV는 target/scenario별 계산을 담고 transient/p95가 없는 행을 성공으로 표시하지 않는다.

사람이 검토할 rubric:

- control/agent/cosmetic gate가 player-visible behavior와 연결되는가?
- cancel과 stale completion이 owner generation, release fence와 기준선 측정을 포함하는가?
- critical miss와 optional miss의 fallback이 다른가?
- manifest에 없는 lower-tier asset이나 timing을 사실처럼 발명하지 않았는가?
- resident, transient와 loading latency 증거를 서로 대신 사용하지 않는가?

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
- 예시 해설의 결정 가능한 합계와 비교하고 차이가 있으면 dependency 중복 합산 여부를 설명한다.
