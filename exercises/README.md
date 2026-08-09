# 실습 경로

이 디렉터리는 01부터 08까지 같은 C++20 renderer를 누적하는 starter·reference·learner workspace와 공개 checker를 제공합니다. 각 실습은 문서의 개념을 실제로 구현하도록 **초기 상태, 입력 fixture, 필수 artifact, 불변식, 알려진 오답, 자동 증거와 사람 검토 근거**를 고정합니다.

세 구현은 같은 `exercises/08-renderer-capstone/project/` CMake project를 사용합니다.

| 구현 | 역할 | 기대 결과 |
|---|---|---|
| `starter` | 공개 `TODO`와 명시적 `not-implemented` 경계를 가진 출발점 | checker의 `--expect not-implemented` 통과 |
| `reference` | 결정적 CPU 기준 결과와 GPU 상태 모델의 올바른 구현 | checker의 `--expect pass` 통과 |
| `workspace` | `scripts/new-workspace.sh`가 한 번 만드는 학습자 사본 | 처음에는 `not-implemented`, 단계 완료 뒤 `pass` |

checker는 reference를 학습자 workspace에 복사하지 않습니다. expected artifact와 공개 invariant를 비교하고, starter와 알려진 오답이 성공으로 오인되지 않는지도 검사합니다.

## 진행 원칙

```text
관련 문서 읽기
→ contract.json 확인
→ starter를 learner workspace로 복사
→ 최소 fixture부터 구현
→ artifact 생성
→ 알려진 오답 mutation 실행
→ 완료 보고서 작성
```

`contract.json`은 기계 판독 가능한 최소 계약입니다. README가 설명을 담당하고 JSON은 checker가 참조할 id·artifact·invariant·mutation·완료 증거를 담당합니다.

## 실습 목록

| 순서 | 실습 | 결과 |
|---:|---|---|
| 01 | [transform trace](01-transform-trace/README.md) | 좌표·camera·clip 단계별 JSON trace |
| 02 | [sampling과 color](02-sampling-and-color/README.md) | texture sample·sRGB·alpha 기준 image와 수치 |
| 03 | [triangle coverage](03-triangle-coverage/README.md) | top-left fill rule과 primitive-id map |
| 04 | [perspective·depth·blend](04-perspective-depth-blend/README.md) | pixel별 보간·depth·blend trace |
| 05 | [textured lit scene](05-textured-lit-scene/README.md) | 검증된 asset·mip·normal·lighting scene |
| 06 | [GPU first frame](06-gpu-first-frame/README.md) | device부터 submit까지 첫 GPU frame |
| 07 | [frame debugging](07-frame-debugging/README.md) | validation·capture·timing 기반 결함 보고서 |
| 08 | [renderer capstone](08-renderer-capstone/README.md) | software/GPU renderer와 단계별 비교 보고서 |

## workspace 준비와 공개 명령

저장소 root에서 다음을 실행합니다.

```sh
./prepare.sh
./scripts/new-workspace.sh

cmake -S exercises/08-renderer-capstone/project \
  -B build/workspace \
  -DCG_IMPLEMENTATION=workspace \
  -DCG_GPU=auto
cmake --build build/workspace
ctest --test-dir build/workspace --output-on-failure
```

`new-workspace.sh`는 `project/starter/`를 같은 project의 Git ignored `workspace/`로 원자 복사합니다. 기존 `workspace/`가 있으면 덮어쓰거나 합치지 않고 실패합니다.

단계 검사는 다음 형식입니다.

```sh
python3 exercises/check.py \
  --impl workspace \
  --stage 01-transform-trace \
  --expect not-implemented \
  --gpu auto
```

`--impl`은 `reference|starter|workspace`, `--stage`는 실습 id 또는 `all`, `--expect`는 `pass|not-implemented|fail`, `--gpu`는 `auto|required|off`입니다. 새 workspace에서 `not-implemented`를 확인한 뒤 해당 stage의 `TODO`를 완성하고 `--expect pass`로 바꿉니다.

검사기 자체의 양성·음성 대조군도 공개합니다.

```sh
python3 exercises/check.py --impl reference --stage all --expect pass --gpu off
python3 exercises/check.py --impl starter --stage all --expect not-implemented --gpu off
```

실제 GPU 장비·driver·window 환경의 증거가 필수인 검사는 지원 환경에서 `--gpu required`로 실행합니다. `auto`는 지원 여부를 탐지해 CPU/상태 모델 검사를 계속하지만, 실행하지 못한 GPU 검사를 성공으로 기록하지 않습니다. `off`는 결정적 CPU reference와 repository CI에 사용하며 실제 GPU 완료의 대체물이 아닙니다.

reference 또는 starter를 별도로 build할 때는 같은 CMake source에서 구현만 바꿉니다.

```sh
cmake -S exercises/08-renderer-capstone/project \
  -B build/reference \
  -DCG_IMPLEMENTATION=reference \
  -DCG_GPU=off
cmake --build build/reference
ctest --test-dir build/reference --output-on-failure
```

## 정리와 복구

`make clean`은 `.guide/`, `build/`, `out/`만 제거합니다. learner `workspace/`는 자동 삭제하거나 reference로 덮어쓰지 않습니다.

- 단순 재검사: 해당 `build/<impl>/`을 정리한 뒤 CMake configure부터 다시 실행합니다.
- workspace 손상: 먼저 workspace를 다른 이름이나 외부 위치에 보존하고, 원래 경로가 없어진 뒤 `./scripts/new-workspace.sh`로 새 starter 사본을 만듭니다.
- reference 불일치: expected를 덮어쓰지 말고 첫 차이 stage, 실제 artifact와 checker report를 보존합니다.
- GPU 실패: `--gpu off`로 CPU/계약 회귀를 분리하되, GPU 실패를 해결한 것으로 표시하지 않습니다.

## 공통 제출물

모든 실습은 다음을 포함합니다.

- 환경과 build/run 명령
- 사용한 규약 version
- 입력 fixture와 hash 또는 코드 위치
- 필수 artifact
- 정상·경계·실패 결과
- known-bad mutation의 실패 근거
- 구현하지 않은 범위
- 다음 단계에서 바꿀 구조
- 실행한 CMake·checker 명령과 exit status
- 자동화할 수 없는 판단에 대한 사람 검토 답변

## artifact 규칙

- 작은 image는 PPM/PGM 또는 명시된 lossless format을 사용합니다.
- 수치 trace는 JSON으로 저장하고 key 순서를 결정적으로 만듭니다.
- float formatting precision과 NaN/inf 정책을 고정합니다.
- 파일명에 frame/case/generation을 포함합니다.
- binary shader와 external asset에는 compiler/source/license metadata를 붙입니다.
- reference를 변경할 때 diff와 계약 변경 이유를 남깁니다.

## 완료 판정

화면이 나오는 것만으로 완료하지 않습니다. 각 실습의 `completion_evidence`를 모두 제출하고, 그 실습 README가 요구하는 알려진 오답 수가 올바른 검사에서 실제로 실패해야 합니다. reference 통과, starter의 `not-implemented`, workspace 단계 통과를 구분하며 사람 검토 질문에도 artifact를 인용해 답합니다.

전체 종료 판정은 다음 세 명령의 의미를 함께 확인합니다.

```sh
python3 exercises/check.py --impl reference --stage all --expect pass --gpu off
python3 exercises/check.py --impl starter --stage all --expect not-implemented --gpu off
python3 exercises/check.py --impl workspace --stage all --expect pass --gpu auto
```

마지막 명령에서 GPU 검사가 생략됐다면 CPU capstone 완료만 증명합니다. 같은 장면의 실제 GPU pipeline 이전과 frame-time 측정 능력은 `--gpu required` 결과, validation/capture와 환경 보고서를 사람이 최종 확인해야 합니다.
