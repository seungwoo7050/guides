# 06. 복잡도와 환원

## 목표

입력 표현 길이를 기준으로 하한·certificate·환원 방향을 검토 가능한 증명으로 작성한다.

답은 저장소 밖 개인 학습 노트에 기록한다. 아래 check box는 자동 정답 형식이 아니라 짝 검토자가 대응하는 증명 문장과 반례를 찾기 위한 rubric이다.

## 문제 A — 비교 정렬 하한

서로 다른 `n`개 원소의 모든 순열을 comparison decision tree가 구분해야 한다는 사실에서 최악 비교 횟수 `Ω(n log n)`을 설명한다.

검토 항목:

```text
[ ] leaf가 최소 n!개 필요한 이유
[ ] 높이 h의 이진 tree leaf 상한
[ ] log(n!) = Ω(n log n)의 근거
[ ] counting/radix sort에 그대로 적용되지 않는 이유
[ ] 같은 key와 원래 record id를 가진 입력에서 안정 정렬의 상대 순서 보존
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

## 자가 검수 체크포인트

답을 먼저 작성한 뒤 다음 필수 연결이 실제 문장으로 증명됐는지 확인한다. 용어만
나열하거나 check box만 표시한 답은 통과로 보지 않는다. 독학 중이라면 틀린 항목을
고친 뒤 자기 설명 질문에 자료를 보지 않고 다시 답한다.

- 비교 정렬: decision tree가 서로 다른 `n!`개 순열을 구분하므로 leaf가 최소
  `n!`개이고, 높이 `h`인 이진 tree의 leaf가 최대 `2^h`개라서
  `h >= log2(n!) = Omega(n log n)`이다. 이 주장은 key를 비교해서만 정보를 얻는
  알고리즘에 한정되므로 counting/radix sort와 모순되지 않는다. 같은 key를 가진
  record에는 원래 id를 붙여 stable pass 전후 상대 순서가 보존되는지도 확인한다.
- NP membership: certificate는 모든 정점을 정확히 한 번 나열한 뒤 첫 정점으로
  돌아오는 순서다. 길이는 입력에 대해 다항식이고, 중복·누락과 연속 edge 및 마지막
  edge를 다항 시간에 검사해야 한다.
- 환원: 새 문제 `B`의 NP-hardness에는 알려진 어려운 문제에서 출발하는
  `A <=p B`가 필요하다. 변환 시간·출력 크기와 `x in A` iff `f(x) in B`를 모두
  보여야 하며, NP-complete 결론에는 별도로 `B in NP`도 필요하다.

## 완료 기준

- comparison tree leaf 수에서 최악 `Ω(n log n)` 비교 하한을 단계별로 유도한다.
- 같은 key의 record id로 안정성과 단순 정렬 결과의 차이를 검토한다.
- Hamiltonian Cycle certificate의 크기와 verifier 연산 수를 입력 크기의 다항식으로 제한한다.
- `A ≤p B`의 변환 시간·결과 크기·양방향 의미 보존을 모두 제출한다.

## 자기 설명

- counting sort가 comparison sorting 하한의 모순이 아닌 이유는 무엇인가?
- 새 문제 `B`의 어려움을 보이려면 환원 화살표가 알려진 문제 `A`에서 출발해야 하는 이유는 무엇인가?

## 검증

짝 검토자는 개인 학습 노트의 각 check box를 단순 표시하지 말고 대응하는 증명 문장을 가리킨다. 문서 링크와 rubric 구조는 루트에서 확인하지만 다음 명령은 노트의 수학적 타당성을 자동 채점하지 않는다.

```sh
make docs-check
```
