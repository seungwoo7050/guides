# 표준 라이브러리 예제

이 디렉터리의 예제는 외부 ML package 없이 핵심 계약을 관찰하기 위한 축소 구현이다.

- `metrics.py`: confusion matrix, precision·recall·F1, log loss와 Brier score
- `split_audit.py`: row·entity 기반 split manifest의 overlap·completeness 검사
- `gradient_check.py`: scalar linear regression의 analytic gradient와 finite difference 비교

이 코드는 production 성능이나 numerical library를 대체하지 않는다. 작은 고정 입력에서 계산과 실패 조건을 이해하기 위한 기준 구현이다.

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```
