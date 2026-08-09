# 단일 register linearizability checker

작은 read/write register history를 exhaustive search로 검사합니다. 교육용 구현이며 대규모 history, multi-object transaction, weak consistency checker를 대신하지 않습니다.

## 실행

```sh
python3 examples/linearizable-register/checker.py \
  exercises/05-validation/01-linearizability/histories.json
```

각 history에 대해 다음을 출력합니다.

- `linearizable`
- 가능한 sequential witness
- 탐색한 상태 수
- pending operation을 포함했는지 여부

## 알고리즘 경계

- completed operation의 real-time precedence를 보존합니다.
- 같은 process의 완료된 operation 순서를 보존합니다.
- pending write는 drop하거나 `OK`로 completion한 경우를 모두 시도합니다.
- read/write register sequential specification만 지원합니다.
- 검색 결과가 유효하려면 fixture의 invocation·completion·result 기록이 정확해야 합니다.
