# 실습 06 — GPU first frame

## 목적

선택한 GPU profile에서 device·shader·resource·pipeline·command buffer·render pass·submission·swapchain의 첫 완전한 frame을 만듭니다. 삼각형 출력만이 아니라 backend·shader manifest·resource generation·frame lifecycle을 artifact로 남깁니다.

위 문장은 learner 구현의 단계 목표입니다. 번들 reference의 actual 경로는 window/swapchain 대신 macOS Metal offscreen RGBA8+D16 target에 position·vertex color triangle을 그립니다. 또한 같은 Metal device 안에서 실제 frame slot 2개와 submission 3개를 사용해 completion 뒤 slot 0을 재사용하고, zero extent를 건너뛰며, 64×64→96×72 offscreen generation 생성·readback·retire를 12개 사건으로 검사합니다. texture sampling과 실제 window/swapchain resize·minimize·high-DPI는 자동 증거가 아니며 사람 검토로 구분합니다.

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

두 번째 명령은 이 stage를 실행하지 않고 `GPU_NOT_EVALUATED`로 기록합니다. CPU 01–05와 lifecycle stage 07의 결정적 기준선을 계속 검사할 때 쓰는 mode이지, 06의 state/lifetime 통과나 실제 GPU 실행의 대체물이 아닙니다. 지원 환경에서 이 stage의 actual GPU 증거를 만들 때는 checker를 `required`로 다시 실행합니다.

```sh
python3 exercises/check.py --impl workspace --stage 06-gpu-first-frame --expect pass --gpu required
```

actual GPU 자동 증거는 고정 scene/hash, position·vertex-color shader와 vertex layout, RGBA8+D16 pass, upload→submit→fence→readback 순서와 color/depth hash를 검사합니다. 별도 same-device probe의 2 slots·3 submits·12 events, zero-target skip, 64×64→96×72 generation, completion 기반 재사용·retire·readback은 결정적 model trace와 정확히 대조됩니다. 이것은 실제 offscreen resource 수명 증거지만 window event, swapchain 재생성, 장시간 stress 증거는 아닙니다. starter와 최소 세 known-bad mutation은 안전한 pre-submit 계약 또는 lifecycle/image oracle에서 거부돼야 하며, `mutation-diagnostic.json`의 `executed_on_gpu: false`를 driver validation 성공으로 해석하지 않습니다.

사람 검토에서는 자동 trace의 submit/completion·last-use 관계를 설명하고, 별도로 실제 window resize/minimize/restore·high-DPI, texture bind가 포함된 다음 단계, validation이 잡지 못한 의미 오류와 미지원 backend의 한계를 환경 artifact로 확인합니다. `make clean`은 생성물만 제거하고 workspace는 보존합니다. GPU 실패 로그·validation baseline을 남긴 채 CPU 회귀와 실제 device 문제를 분리해 복구합니다.
