# 예측 가능한 분기와 불규칙한 분기 관찰

같은 비교문을 정렬된 패턴과 의사 난수 패턴에 적용합니다. 정렬된 입력은 한동안 참이다가 한동안 거짓이고, 난수 입력은 결과가 자주 바뀝니다.

```sh
make check
make benchmark
make assembly
```

이 예제는 난수 입력이 몇 배 느린지를 정답으로 고정하지 않습니다. 컴파일러가 `if`를 조건 이동이나 벡터 비교로 바꾸면 실제 조건 분기가 사라질 수 있습니다. `make assembly`로 `count_selected`의 기계어를 먼저 확인하고, Linux에서 사용할 수 있다면 다음 계수기를 함께 관찰하세요.

```sh
perf stat -e cycles,instructions,branches,branch-misses ./build/branch_benchmark 16000000
```

`branch-misses`는 CPU와 권한 설정에 따라 제공되지 않을 수 있습니다. 계수기를 얻지 못했다면 실행 시간만으로 분기 예측기의 내부 동작을 단정하지 마세요.

threshold를 거의 항상 참 또는 거의 항상 거짓이 되도록 바꾸고, 입력 배열을 읽는 메모리 비용이 분기 비용보다 커지는 지점도 찾아보세요.
