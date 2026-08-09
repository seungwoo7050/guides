# 실습 경로

이 디렉터리는 완성된 renderer 답안을 제공하지 않습니다. 각 실습은 문서의 개념을 구현할 수 있도록 **초기 상태, 입력 fixture, 필수 artifact, 불변식, 알려진 오답과 완료 근거**를 고정합니다.

## 진행 원칙

```text
관련 문서 읽기
→ contract.json 확인
→ 구현 저장소 또는 workspace 선택
→ 최소 fixture부터 구현
→ artifact 생성
→ 알려진 오답 mutation 실행
→ 완료 보고서 작성
```

`contract.json`은 기계 판독 가능한 최소 계약입니다. README가 설명을 담당하고 JSON은 자동 검사기·후속 구현 저장소가 참조할 id와 artifact를 담당합니다.

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

## 구현 위치

세 가지 방식 중 하나를 선택합니다.

1. 별도 학습 저장소에서 각 contract를 차례로 구현
2. 하나의 renderer 저장소에서 stage별 branch/tag로 구현
3. 기존 오픈소스 renderer에 작은 fixture와 test 형태로 적용

이 가이드 압축파일 자체에 대규모 skeleton을 넣지 않습니다. 그래픽스 backend와 package 설치가 문서 검증을 방해하지 않게 하고, 사용자가 자신의 플랫폼과 프로젝트에 맞게 구현하도록 하기 위해서입니다.

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

## artifact 규칙

- 작은 image는 PPM/PGM 또는 명시된 lossless format을 사용합니다.
- 수치 trace는 JSON으로 저장하고 key 순서를 결정적으로 만듭니다.
- float formatting precision과 NaN/inf 정책을 고정합니다.
- 파일명에 frame/case/generation을 포함합니다.
- binary shader와 external asset에는 compiler/source/license metadata를 붙입니다.
- reference를 변경할 때 diff와 계약 변경 이유를 남깁니다.

## 완료 판정

화면이 나오는 것만으로 완료하지 않습니다. 각 실습의 `completion_evidence`를 모두 제출하고, 최소 한 개의 알려진 오답 mutation이 올바른 검사에서 실패해야 합니다.
