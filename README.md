# 알고리즘 설계와 검증 가이드

이 저장소는 알고리즘 이름을 외우는 대신 문제를 계약으로 바꾸고, 정확성을 증명하며, 입력 규모에 맞는 비용을 계산하고, 작은 독립 기준 구현으로 후보 구현을 검증하는 방법을 다룬다. 검증 도구의 기준 환경은 Python 3.12 이상이며 외부 Python 패키지는 필요하지 않다.

핵심 문서는 특정 언어에 종속되지 않는다. 의사코드와 상태·불변식을 중심으로 설명하며, 실제 구현 환경은 [Python 프로필](docs/90-implementation-profiles/python.md) 또는 [C++20 프로필](docs/90-implementation-profiles/cpp20.md)에서 선택한다.

## 시작

1. 저장소 루트에서 최종 구조와 실행 환경을 준비한다.

   ```sh
   ./prepare.sh
   ```

2. [학습 로드맵](docs/00-roadmap.md)을 읽는다.
3. 각 Part의 문서와 대응 exercise를 진행한다.
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
