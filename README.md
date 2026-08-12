# 알고리즘 설계와 검증 가이드

이 저장소는 알고리즘 이름을 외우는 대신 문제를 계약으로 바꾸고, 정확성을 증명하며, 입력 규모에 맞는 비용을 계산하고, 작은 독립 기준 구현으로 후보 구현을 검증하는 방법을 다룬다. 검증 도구의 기준 환경은 Python 3.12 이상이며 외부 Python 패키지는 필요하지 않다.

핵심 문서는 특정 언어에 종속되지 않는다. 의사코드와 상태·불변식을 중심으로 설명한다. 저장소가 바로 실행할 수 있는 capstone과 checker는 [Python 프로필](docs/90-implementation-profiles/python.md)을 기준으로 하며, [C++20 프로필](docs/90-implementation-profiles/cpp20.md)은 같은 계약을 별도 harness로 옮길 때의 경계를 설명한다.

## 시작

1. 저장소 루트에서 최종 구조와 실행 환경을 준비한다.

   ```sh
   ./prepare.sh
   ```

2. [학습 로드맵](docs/00-roadmap.md)을 읽는다.
3. 아래 단계별 학습 지도에 따라 관련 문서와 exercise를 번갈아 진행한다.
4. 저장소 전체를 검사한다.

   ```sh
   ./verify.sh
   ```

빠른 로컬 검사에서는 공개 Make target을 사용할 수 있다.

```sh
make check
```

`prepare.sh`는 source를 생성·삭제하지 않고 현재 HEAD·Git index·source fingerprint를 `.guide/algorithms/prepared.json`에 기록한다. `verify.sh`는 저장소 밖 임시 사본과 로그에서 검사하며 source 입력을 바꾸면 실패한다.

## 학습 경로

```text
문제 계약·반례
→ 점근 분석·점화식·정확성
→ 자료구조
→ 설계 기법
→ 그래프·문자열
→ 복잡도와 환원
→ 혼합 문제와 검증 capstone
```

[exercise 안내](exercises/README.md)는 구현 단계와 서술형 검토 항목을 함께 제시한다. 구현 검사는 고정 시드, 단순 기준 계산, 최소 실패 조건을 사용하므로 같은 오류를 반복해서 재현할 수 있다. 핵심 경로를 마친 뒤에는 [확장 문제와 검증 설계](docs/80-extended-practice.md)에서 선별한 고급 문제를 진행한다.

## 작업과 검증의 경계

- 이 branch에는 별도 `examples/`가 없다. 문서 안의 작은 trace와 의사코드는 개념을 관찰하는 설명이며 exercise 답안이 아니다.
- `skeleton/`은 공개 API와 미완성 경계를 보존하는 read-only 시작점이다. 생성 도구로 복사한 `exercises/07-verified-algorithms-capstone/workspace/algorithms.py`만 직접 수정한다.
- Part 1과 Part 6의 서술 답안은 저장소 밖 개인 학습 노트에 기록한다. rubric과 짝 검토가 의미 검증이며 `make docs-check`는 repository 문서·학습·source 계약을 검사하지만 개인 노트의 수학적 타당성을 채점하지 않는다.
- `data-structures`, `design-techniques`, `graphs`, `strings` checker stage는 해당 함수군만 검사하지만 learner artifact는 같은 `workspace/algorithms.py`에 누적된다. 마지막 `all` 검사가 전체 회귀를 확인한다.
- 자신의 workspace가 `all` 검사를 통과하기 전에는 `reference/`를 열지 않는다. 이후 기준 구현의 선택과 자신의 불변식·실패 처리를 비교한다.
- `make check`와 `./verify.sh`는 repository-owned reference, skeleton, known-bad fixture와 검증 도구의 건강성을 검사한다. 두 명령은 ignored learner workspace의 완료 판정을 대신하지 않는다.

## 단계별 학습 지도

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 0 | [학습 로드맵](docs/00-roadmap.md) | — | 필수·선택 경로와 지원 환경 확인 | 수정하지 않음 | `make docs-check` | Part 1로 이동 |
| 1 | [문제 계약과 반례](docs/01-foundations/01-problem-contracts-and-counterexamples.md) → [점근 분석](docs/01-foundations/02-asymptotic-analysis.md) → [점화식과 분할 정복](docs/01-foundations/03-recurrences-and-divide-and-conquer.md) → [정확성, 불변식과 종료](docs/01-foundations/04-correctness-and-invariants.md) | — | [분석과 반례](exercises/01-analysis-and-counterexamples/README.md)의 공통 기록과 A·B·C 초안 작성 | 저장소 밖 개인 학습 노트 | 수동 rubric·짝 검토; `make docs-check`는 repository 계약만 검사 | Part 2 뒤 A, Part 3 뒤 B, Part 4 뒤 C를 보완하며 Part 2로 이동 |
| 2 | [선형 구조, 구간과 해시](docs/02-data-structures/01-linear-structures-ranges-and-hashing.md) → [순서, 탐색, 힙과 우선순위](docs/02-data-structures/02-order-search-heaps-and-priority.md) → [트리와 균형 탐색 트리](docs/02-data-structures/03-trees-and-balanced-search-trees.md) → [분리 집합과 상각 분석](docs/02-data-structures/04-disjoint-sets-and-amortized-analysis.md) | — | 저장소 루트에서 `scripts/new-workspace.sh exercises/07-verified-algorithms-capstone`로 workspace 생성. [자료구조](exercises/02-data-structures/README.md): prefix/range/lower-bound/red-black 구현, DSU trace 기록 | `exercises/07-verified-algorithms-capstone/workspace/algorithms.py`와 개인 학습 노트 | `make stage-check STAGE=data-structures` | reference는 아직 보지 않고 Part 1의 A를 보완한 뒤 Part 3으로 이동 |
| 3 | [완전탐색과 백트래킹](docs/03-design-techniques/01-brute-force-and-backtracking.md) → [그리디 설계](docs/03-design-techniques/02-greedy-methods.md) → [동적 계획법](docs/03-design-techniques/03-dynamic-programming.md) | — | [설계 기법](exercises/03-design-techniques/README.md): knapsack/interval/LCS 구현과 DP 갱신 순서 반례 기록 | 같은 `workspace/algorithms.py`와 개인 학습 노트 | `make stage-check STAGE=design-techniques` | reference는 아직 보지 않고 Part 1의 B를 보완한 뒤 Part 4로 이동 |
| 4 | [그래프 표현, 순회와 위상 순서](docs/04-graph-algorithms/01-traversal-and-topological-order.md) → [최소 스패닝 트리](docs/04-graph-algorithms/02-minimum-spanning-trees.md) → [최단 경로](docs/04-graph-algorithms/03-shortest-paths.md) → [네트워크 유량과 이분 매칭](docs/04-graph-algorithms/04-network-flow-and-matching.md) | — | [그래프](exercises/04-graphs/README.md): BFS/Dijkstra/Kruskal/Bellman–Ford/max-flow 구현; 위상 순서·SCC·matching은 서술 trace/certificate 기록 | 같은 `workspace/algorithms.py`와 개인 학습 노트 | `make stage-check STAGE=graphs` | reference는 아직 보지 않고 Part 1의 C를 보완한 뒤 Part 5로 이동 |
| 5 | [문자열 매칭과 전처리](docs/05-string-algorithms/01-string-matching-and-preprocessing.md) | — | [문자열](exercises/05-strings/README.md): KMP 구현, Rabin–Karp 충돌 trace 기록; Z-box trace는 선택 | 같은 `workspace/algorithms.py`와 개인 학습 노트 | `make stage-check STAGE=strings` | reference는 아직 보지 않고 Part 6으로 이동 |
| 6 | [정렬, 안정성과 비교 하한](docs/06-complexity/01-sorting-stability-and-lower-bounds.md) → [복잡도 클래스와 다항식 환원](docs/06-complexity/02-complexity-classes-and-reductions.md) | — | [복잡도와 환원](exercises/06-complexity/README.md)의 하한·안정성·certificate·reduction 증거 작성 | 저장소 밖 개인 학습 노트 | 수동 rubric·짝 검토; `make docs-check`는 repository 계약만 검사 | Part 7로 이동 |
| 7 | [혼합 문제와 검증 capstone](docs/07-mixed-review-and-capstone.md) | — | [검증 capstone](exercises/07-verified-algorithms-capstone/README.md)의 누적 workspace 전체 완성과 실패·회귀 증거 기록 | 같은 `workspace/algorithms.py`와 저장소 밖 개인 학습 노트 | `make stage-check STAGE=all` | 통과 뒤 `reference/`의 권장 구현 순서와 비교하고 skeleton·known-bad 거부를 확인한 뒤 선택 확장으로 이동 |
| 8 | [확장 문제와 검증 설계](docs/80-extended-practice.md) | — | 서로 다른 영역의 문제 세 개를 disposable 실험으로 검증 | 저장소 밖 개인 학습 노트와 disposable 작업 경로 | 문서의 완료 기준과 manual review rubric | 필수 경로와 선택 확장 종료 |
