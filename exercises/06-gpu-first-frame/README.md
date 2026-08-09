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
