# Model lifecycle reference

이 디렉터리는 합성 fixture에 대한 **한 가지 완성 예시**다. 점수의 정답이 아니라
split 독립성, train-only fitted state, 재현 가능한 선택과 실제 inference artifact의
증거를 보여 준다. 표준 라이브러리와 CPU만 사용하며 network access가 없다.

저장소 루트에서 산출물을 임시 디렉터리에 재생성한다.

```sh
PYTHONPATH=exercises/model-lifecycle/reference/src \
  python3 -m model_project.pipeline --output /tmp/ml-reference
```

출력 경로는 존재하지 않거나 비어 있어야 한다. 생성기는 기존 산출물·학습자 작업을
덮어쓰지 않으므로 반복 실행할 때는 새로운 임시 경로를 사용한다.

검사와 inference smoke test:

```sh
PYTHONPATH=exercises/model-lifecycle/reference/src \
  python3 -m unittest discover \
    -s exercises/model-lifecycle/reference/tests -v

PYTHONPATH=exercises/model-lifecycle/reference/src \
  python3 -m model_project.inference \
    --bundle exercises/model-lifecycle/reference/artifacts/model-bundle \
    --input exercises/model-lifecycle/reference/artifacts/model-bundle/golden-inputs.jsonl
```

두 번째 명령의 input은 JSON object 하나 또는 JSONL이다. 필수 field 누락,
unknown field/category, 잘못된 type·범위, checksum·version 불일치는 오류로
종료한다. `reports/release-decision.md`의 승인은 합성 fixture에서 다음 개발
단계로 이동하는 것만 뜻하며 실제 사용자 대상 배포 승인이 아니다.
