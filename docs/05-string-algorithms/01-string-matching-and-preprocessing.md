# 문자열 매칭과 전처리

## 학습 목표

- 문자, byte, Unicode code point와 grapheme cluster의 단위를 구분한다.
- 단순 검색의 중복 비교를 상태로 표현한다.
- KMP prefix function의 의미와 fallback 불변식을 설명한다.
- rolling hash의 충돌 가능성과 검증 방법을 명시한다.

## 선행 개념

[선형 구간](../02-data-structures/01-linear-structures-ranges-and-hashing.md), 반복 불변식과 문자열 인덱스 경계를 알고 있어야 한다.

## 핵심 모델

문자열 알고리즘을 시작하기 전에 인덱스 단위를 정한다.

```text
byte index인가?
Unicode code point index인가?
사용자가 보는 문자 단위인가?
대소문자·정규화 규칙이 있는가?
```

알고리즘이 선형이어도 문자 decoding이나 normalization 비용이 별도로 들 수 있다.

## 1. 단순 매칭

본문 `T`의 각 시작 위치에서 패턴 `P`를 앞부터 비교한다.

최악 비용은 `O((n-m+1)m)`, 보통 `O(nm)`으로 표현한다. 패턴이 짧거나 입력이 작으면 구현이 단순한 기준 풀이로 적합하다.

## 2. 실패 정보의 재사용

긴 접두사가 일치한 뒤 한 문자에서 실패했을 때, 이미 확인한 모든 문자를 다시 비교하지 않으려면 다음을 알아야 한다.

```text
현재까지 일치한 접두사 안에서,
동시에 suffix이기도 한 가장 긴 proper prefix 길이
```

이 정보가 KMP의 prefix function이다.

## 3. prefix function

`pi[i]`를 `P[0:i+1]`의 proper prefix이면서 suffix인 가장 긴 길이로 정의한다.

```text
j = pi[i-1]
while j > 0 and P[i] != P[j]:
    j = pi[j-1]
if P[i] == P[j]:
    j += 1
pi[i] = j
```

불변식:

```text
j는 P[0:i]에서 가능한 prefix-suffix 후보 길이다.
실패할 때 pi[j-1]로 이동해 이미 검증된 더 짧은 후보를 시도한다.
```

`j`는 증가하거나 더 작은 prefix로 fallback하며 전체 fallback 횟수가 선형으로 제한된다.

## 4. KMP 검색

본문을 한 번 왼쪽에서 오른쪽으로 읽으며 현재 일치 길이 `j`를 유지한다.

```text
for character in text:
    while j > 0 and character != pattern[j]:
        j = pi[j-1]
    if character == pattern[j]:
        j += 1
    if j == pattern_length:
        일치 위치 기록
        j = pi[j-1]  # 겹치는 일치를 계속 찾는 경우
```

첫 일치만 찾는 API인지 모든 일치를 찾는 API인지 계약을 분리한다. 빈 패턴의 결과도 정한다. 일반적인 `find` 계약에서는 빈 패턴이 위치 0에서 일치한다.

## 5. 반복 문자열 반례

KMP 결함은 다음 입력에서 잘 드러난다.

- 본문과 패턴이 같은 문자 반복
- 긴 접두사 뒤 마지막 문자만 다름
- 패턴이 본문보다 김
- 빈 본문·빈 패턴
- 겹치는 일치: `aaaa`에서 `aa`
- fallback이 여러 번 연속 발생: `abababac`

## 6. Rabin–Karp와 rolling hash

길이 `m` window의 hash를 이동하며 패턴 hash와 비교한다. 적절한 modular arithmetic으로 각 이동을 `O(1)`에 갱신할 수 있다.

그러나 hash가 같아도 문자열이 같다는 보장은 없다.

선택:

- hash 일치 시 실제 문자열 비교
- 서로 독립적인 여러 hash 사용
- 충돌 허용 확률을 계약에 명시

정확성이 필수인 API에서 hash만 비교해 반환하면 안 된다.

## 7. Z-function과 선택 기준

Z-function은 각 위치에서 전체 문자열 prefix와 일치하는 길이를 저장한다. `pattern + separator + text` 구조로 매칭에 사용할 수 있다.

- KMP: 패턴 상태 machine과 streaming 처리에 자연스러움
- Z: prefix 일치 길이 자체가 필요한 문제에 자연스러움
- rolling hash: substring equality 질의가 많을 때 유용하나 충돌 관리 필요
- suffix array/automaton: 많은 질의와 더 깊은 문자열 과정의 주제

## 8. 비용

KMP 전처리 `O(m)`, 검색 `O(n)`, 추가 공간 `O(m)`이다. 각 문자가 여러 fallback에 참여해도 `j`의 총 증가·감소 횟수로 선형임을 설명한다.

## 연결 실습

[문자열 exercise](../../exercises/05-strings/README.md)에서 KMP를 구현하고 빈 패턴·긴 접두사 실패·반복 문자 입력을 표준 검색과 고정 시드로 대조한다.

## 완료 기준

- prefix function 각 값의 의미를 proper prefix와 suffix 길이로 설명한다.
- mismatch fallback 뒤 현재 문자를 다시 처리하는 상태 변화를 trace한다.
- 빈 패턴과 Unicode 문자열에서 반환하는 index 단위를 API 계약으로 고정한다.

## 실패 조건

- byte index와 사용자 문자 index를 혼동한다.
- prefix function을 전체 prefix까지 허용해 자기 자신 길이를 저장한다.
- fallback 후 현재 문자를 다시 비교하지 않는다.
- 모든 일치 API에서 match 뒤 `j`를 0으로 만들어 겹치는 일치를 놓친다.
- rolling hash 충돌을 불가능하다고 가정한다.
- 빈 패턴 계약이 없다.

## 연습

[문자열 exercise](../../exercises/05-strings/README.md)에서 KMP를 구현하고 짧은 무작위 문자열을 표준 검색과 비교한다.
