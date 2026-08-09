# 실습 06 — GPU first frame

## 목적

선택한 GPU profile에서 device·shader·resource·pipeline·command buffer·render pass·submission·swapchain의 첫 완전한 frame을 만듭니다. 삼각형 출력만이 아니라 backend·shader manifest·resource generation·frame lifecycle을 artifact로 남깁니다.

관련 문서:

- [GPU 실행과 command](../../docs/04-gpu-rendering/14-gpu-execution-and-command-model.md)
- [resource·layout·transfer](../../docs/04-gpu-rendering/15-resources-layouts-transfers-and-formats.md)
- [shader·pipeline·pass](../../docs/04-gpu-rendering/16-shaders-pipelines-and-render-passes.md)
- [frame lifecycle·resize](../../docs/04-gpu-rendering/17-frame-lifecycle-synchronization-and-resize.md)
- [SDL3 GPU profile](../../docs/90-appendix/02-api-profile-sdl3-gpu.md)

## 초기 단계

1. device와 window를 연결하고 clear frame을 표시합니다.
2. 단색 triangle을 그립니다.
3. vertex color를 전달합니다.
4. indexed quad와 camera/object uniform을 추가합니다.
5. depth attachment와 texture를 추가합니다.
6. frame slot 2개와 resize를 처리합니다.

각 단계는 이전 artifact를 보존합니다.

## 필수 artifact

```text
out/gpu-first-frame/
├── environment.json
├── shader-manifests/*.json
├── resources.json
├── pipelines.json
├── frame-trace.json
├── screenshot.ppm 또는 lossless image
├── resize-trace.json
└── validation.log
```

`environment.json`에는 OS, GPU, driver/backend, SDL/API version, shader compiler, build type와 validation 설정을 기록합니다.

## 불변식

- shader binary와 manifest hash가 일치합니다.
- vertex layout offset/format과 shader location이 맞습니다.
- upload resource는 GPU copy 완료 전 재사용/파괴되지 않습니다.
- pipeline target/depth format이 pass attachment와 맞습니다.
- frame slot은 이전 submission completion 뒤 재사용합니다.
- zero extent에서 invalid render target을 만들지 않습니다.
- resize 뒤 old attachment는 last-use 완료 뒤 파괴됩니다.

## 알려진 오답

- vertex stride mismatch
- shader binding count/slot mismatch
- uniform buffer 같은 offset 덮어쓰기
- upload 직후 staging 파괴
- depth format/pipeline 불일치
- resize 뒤 이전 extent의 viewport/depth 사용

## 완료 근거

- clear→triangle→indexed/depth/texture 단계별 screenshot
- resource/pipeline/frame trace
- validation fatal 0과 warning baseline 설명
- resize·minimize·restore 로그
- known-bad mutation 최소 세 개가 validation 또는 image 검사에서 실패
- 지원하지 않는 backend/platform과 이유

## 준비·workspace·stage 검사

[공통 workspace 절차](../README.md#workspace-준비와-공개-명령)를 수행하고 GPU mode를 명시합니다.

```sh
cmake -S exercises/08-renderer-capstone/project -B build/workspace -DCG_IMPLEMENTATION=workspace -DCG_GPU=auto
cmake --build build/workspace
python3 exercises/check.py --impl workspace --stage 06-gpu-first-frame --expect pass --gpu auto
python3 exercises/check.py --impl reference --stage 06-gpu-first-frame --expect pass --gpu off
```

두 번째 명령은 결정적 state/lifetime 기준선이지 실제 GPU 실행의 대체물이 아닙니다. 지원 환경에서 최종 GPU 증거를 만들 때는 CMake와 checker를 모두 `required`로 다시 실행합니다.

```sh
python3 exercises/check.py --impl workspace --stage 06-gpu-first-frame --expect pass --gpu required
```

자동 증거는 shader manifest, layout/pipeline attachment, upload completion, frame-slot 재사용, zero extent와 resize generation을 검사합니다. starter와 최소 세 known-bad mutation이 validation 또는 의미/image oracle에서 거부돼야 합니다.

사람 검토에서는 submit과 completion의 차이, old resource의 last-use 사건, validation이 잡지 못한 의미 오류와 미지원 backend의 한계를 환경 artifact로 설명합니다. `make clean`은 생성물만 제거하고 workspace는 보존합니다. GPU 실패 로그·validation baseline을 남긴 채 CPU 회귀와 실제 device 문제를 분리해 복구합니다.
