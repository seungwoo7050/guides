# shader·pipeline·render pass

## 목표

shader source만 맞으면 draw가 성공한다는 가정을 버리고, shader stage interface·resource binding·vertex input·render target format·raster/depth/blend state를 하나의 graphics pipeline 계약으로 묶습니다. pipeline 생성 실패와 draw-time mismatch를 build artifact·reflection·validation으로 좁힙니다.

## 시작하기 전에

[resource와 layout](15-resources-layouts-transfers-and-formats.md)의 format·usage·binding 계약을 사용합니다. shader compiler와 binary format은 [SDL3 GPU 구현 프로필](../90-appendix/02-api-profile-sdl3-gpu.md)에 기록합니다.

### shader build는 source와 runtime 사이의 별도 단계

shader는 C++ string으로 runtime에 임의 컴파일하는 것보다 명시적 build artifact로 관리하는 편이 재현성이 좋습니다.

```text
shader source
→ compiler + options + target profile
→ binary/intermediate artifact
→ reflection/manifest
→ runtime shader object
```

manifest에 다음을 남깁니다.

- source hash와 include dependency
- compiler name/version와 options
- target format/backend
- stage와 entry point
- vertex input/output location
- resource binding과 array count
- push/uniform size
- binary hash

runtime이 기대한 manifest와 binary가 다르면 pipeline 생성 전에 거부합니다.

### stage interface

vertex shader output과 fragment shader input은 location, type, interpolation mode가 일치해야 합니다. 이름이 같다는 사실은 계약이 아닙니다. 정수 id는 flat interpolation을 사용하고, color/UV/normal은 필요한 mode를 명시합니다.

vertex input도 C++ vertex layout과 shader location을 함께 검사합니다. 사용하지 않는 attribute가 pipeline에 있거나 shader가 기대하는 location이 누락되면 validation 또는 잘못된 결과가 생깁니다.

### resource binding

API마다 set/group/register/space 표현이 다릅니다. 내부 manifest는 semantic name과 stage visibility를 정본으로 두고 backend mapping을 기록할 수 있습니다.

```text
FrameCamera   uniform, vertex+fragment
MaterialData uniform, fragment
BaseColor     sampled texture, fragment
BaseSampler   sampler, fragment
```

SDL3 GPU는 shader format과 backend에 따라 resource layout 규칙을 엄격히 요구합니다. slot count와 order를 manual로 중복 작성한다면 reflection 결과와 자동 비교합니다.

### graphics pipeline state

pipeline key에는 최소한 다음이 포함됩니다.

- vertex/fragment shader artifact hash
- vertex input layout
- primitive topology
- front face와 cull mode
- polygon/fill mode가 지원될 경우 값
- color attachment count와 format
- depth format, compare, write
- blend state와 write mask
- sample count

같은 shader라도 swapchain format이나 depth format이 바뀌면 다른 pipeline이 필요할 수 있습니다. resize가 extent만 바꾸는지 format/generation도 바꾸는지 확인합니다.

### render pass와 attachment

pass 시작 시 attachment를 선언합니다.

```text
color target: format, clear/load, store, clear value
optional depth: format, clear/load, store, clear depth
extent와 sample count
```

pipeline의 target 정보와 pass attachment가 호환돼야 합니다. depth pipeline을 bind하고 depth attachment를 제공하지 않거나 sample count가 다르면 오류입니다.

pass boundary는 단지 grouping이 아니라 attachment 사용과 load/store lifetime을 정의합니다. post-process가 추가되면 geometry color를 offscreen texture에 쓰고 다음 pass가 sample하는 dependency가 생깁니다.

### pipeline cache

pipeline 생성은 비쌀 수 있지만 첫 구현에서 premature cache를 만들지 않습니다. key를 완전하게 정의한 뒤 다음을 측정합니다.

- 생성 횟수와 시간
- frame 중 생성 여부
- cache hit/miss
- shader reload 뒤 invalidation
- device/backend별 binary cache 호환성

불완전한 key는 틀린 state를 재사용해 간헐적 rendering 오류를 만듭니다.

### shader 오류를 관찰하는 순서

1. shader artifact와 manifest가 존재하고 hash가 맞는가
2. runtime device가 해당 format을 지원하는가
3. stage/entry point가 맞는가
4. binding layout과 slot count가 맞는가
5. pipeline target format/state가 pass와 맞는가
6. draw 시 실제 resource가 모두 bind됐는가
7. shader input 값이 유효한가
8. output이 depth/blend/write mask를 통과하는가

shader를 무작정 단색으로 바꾸는 방법은 중간 조사로 사용할 수 있지만, 어느 단계의 가설을 검증하는지 기록합니다.

## 검증 fixture

- position만 사용하는 단색 triangle
- vertex color interpolation
- uniform transform이 다른 두 draw
- checker texture와 sampler
- depth attachment on/off pipeline
- straight/premultiplied blend pipeline
- 잘못된 binding slot·vertex format·target format mutation
- shader reload generation과 pipeline invalidation

pipeline manifest와 frame capture의 actual pipeline state를 비교합니다.

## 흔한 오답

- shader variable 이름으로 stage interface가 연결된다고 가정
- C++·shader·pipeline에 binding slot을 세 번 수동 복제
- shader hash만 pipeline cache key로 사용
- pass attachment format/sample count와 pipeline state 불일치
- shader compile 성공을 runtime resource binding 성공으로 취급
- hot reload 뒤 이전 pipeline이 새 shader resource layout을 사용
- blend/depth/write mask 때문에 출력이 사라진 사실을 shader 계산 오류로 오진

## 연결 실습

- [`06-gpu-first-frame`](../../exercises/06-gpu-first-frame/README.md): shader manifest와 단색/vertex-color pipeline을 구성합니다.
- [`07-frame-debugging`](../../exercises/07-frame-debugging/README.md): frame capture에서 pipeline·binding·attachment를 검증합니다.

## 완료 기준

- shader source부터 runtime object까지 compiler·profile·manifest·hash를 기록합니다.
- stage interface와 resource binding을 reflection 또는 자동 manifest 비교로 검증합니다.
- pipeline key에 shader 외 모든 고정 state와 attachment format을 포함합니다.
- 검은 화면을 pipeline 생성·binding·shader input·output test 단계로 나눠 조사합니다.
