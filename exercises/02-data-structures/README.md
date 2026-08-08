# 02. 자료구조

## 목표

구간·순서·tree의 공개 계약을 불변식과 독립 기준 계산으로 구현한다.

## 구현 대상

[capstone skeleton](../07-verified-algorithms-capstone/skeleton/algorithms.py)의 다음 함수를 구현한다.

- `prefix_sums`
- `range_sum`
- `lower_bound`
- `red_black_height`

## 계약

### Prefix sum

- 결과 길이는 입력 길이보다 1 크다.
- 첫 값은 0이다.
- `range_sum(prefix, start, stop)`은 반열린 구간을 사용한다.
- `0 <= start <= stop < len(prefix)`를 벗어나면 `ValueError`다.

### Lower bound

- 입력은 호출자가 정렬을 보장한다.
- 첫 `value >= target` 위치를 반환한다.
- 모든 값이 작으면 `len(values)`다.

### Red-black validation

- 빈 tree의 black height는 1이다.
- 비어 있는 leaf를 black으로 센다.
- root black, BST strict order, red-red 금지, 동일 black height를 검증한다.
- 위반하면 `ValueError`다.

## 실행

```sh
cd exercises/07-verified-algorithms-capstone
python3 check.py --impl workspace --stage data-structures --expect pass
```

## 구현 뒤 설명

- lower bound의 세 불변식을 적는다.
- red-black 검증 함수가 subtree에서 반환해야 하는 정보를 적는다.
- prefix sum 전처리가 유리해지는 질의 수 조건을 설명한다.

## 완료 기준

- prefix sum과 range sum이 빈 구간·전체 구간·범위 오류 사례를 통과한다.
- lower bound가 빈 수열, 중복, 양끝 target에서 `bisect_left`와 일치한다.
- 레드블랙 검증기가 BST·root 색·red-red·black-height 결함을 각각 거부한다.

## 자기 설명

- lower bound의 세 구간은 반복 경계에서 어떤 원소 조건을 보장하는가?
- 레드블랙 subtree 검증이 key 범위와 black height를 함께 반환해야 하는 이유는 무엇인가?

## 검증

안전한 workspace를 만든 뒤 해당 stage만 실행한다.

```sh
scripts/new-workspace.sh exercises/07-verified-algorithms-capstone
cd exercises/07-verified-algorithms-capstone
python3 check.py --impl workspace --stage data-structures --expect pass
```
