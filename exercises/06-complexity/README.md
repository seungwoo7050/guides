# 06. 복잡도와 환원

## 목표

입력 표현 길이를 기준으로 하한·certificate·환원 방향을 검토 가능한 증명으로 작성한다.

## 문제 A — 비교 정렬 하한

서로 다른 `n`개 원소의 모든 순열을 comparison decision tree가 구분해야 한다는 사실에서 최악 비교 횟수 `Ω(n log n)`을 설명한다.

검토 항목:

```text
[ ] leaf가 최소 n!개 필요한 이유
[ ] 높이 h의 이진 tree leaf 상한
[ ] log(n!) = Ω(n log n)의 근거
[ ] counting/radix sort에 그대로 적용되지 않는 이유
```

## 문제 B — NP membership

Hamiltonian Cycle decision problem의 certificate와 verifier를 정의한다.

```text
[ ] certificate 크기가 입력에 대한 다항식
[ ] verifier가 모든 정점을 정확히 한 번 확인
[ ] 인접 edge와 cycle closure 확인
[ ] verifier 시간이 다항식
```

## 문제 C — 환원 방향

알려진 NP-complete 문제 `A`를 새 문제 `B`로 환원해 `B`의 NP-hardness를 보이려 한다.

```text
[ ] A <=p B 방향
[ ] 변환 시간과 결과 크기
[ ] yes iff yes 양방향
[ ] B가 NP-complete라면 B ∈ NP도 별도 증명
```

자동 채점은 하지 않는다. 환원은 코드 출력 형식보다 변환의 의미 보존과 방향을 사람이 검토해야 한다.

## 완료 기준

- comparison tree leaf 수에서 최악 `Ω(n log n)` 비교 하한을 단계별로 유도한다.
- Hamiltonian Cycle certificate의 크기와 verifier 연산 수를 입력 크기의 다항식으로 제한한다.
- `A ≤p B`의 변환 시간·결과 크기·양방향 의미 보존을 모두 제출한다.

## 자기 설명

- counting sort가 comparison sorting 하한의 모순이 아닌 이유는 무엇인가?
- 새 문제 `B`의 어려움을 보이려면 환원 화살표가 알려진 문제 `A`에서 출발해야 하는 이유는 무엇인가?

## 검증

짝 검토자는 각 check box를 단순 표시하지 말고 대응하는 증명 문장을 가리킨다. 문서 링크와 rubric 구조는 루트에서 확인한다.

```sh
make docs-check
```
