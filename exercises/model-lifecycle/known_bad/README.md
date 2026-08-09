# Known-bad lifecycle candidates

각 후보는 완성 reference를 임시 출력 디렉터리에 생성한 뒤 한 가지 공개 계약 위반만 주입한다.
공개 checker의 negative control이며 정답 구현 예제가 아니다.

| 후보 | 관찰 가능한 위반 |
|---|---|
| `fit-all-splits-preprocessing` | preprocessing fitted state가 train 외 split 통계를 사용한다 |
| `forbidden-feature` | prediction 시점 이후의 `future_refund_30d`를 feature order에 넣는다 |
| `test-based-selection` | model·threshold 선택 split을 final test로 바꾼다 |
