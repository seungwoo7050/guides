# resource·layout·transfer·format

## 목표

GPU buffer와 texture를 단순한 handle이 아니라 크기·format·usage·memory domain·상태·generation·완료 시점을 가진 resource로 관리합니다. CPU/GPU 사이 data transfer, vertex/uniform layout, row pitch, texture format와 resource retirement를 검증합니다.

## 시작하기 전에

[GPU command 모델](14-gpu-execution-and-command-model.md)의 submission/completion 경계를 사용합니다. C++ object lifetime은 handle wrapper의 수명을 관리하지만 GPU in-flight 사용을 자동으로 끝내지 않습니다.

### resource descriptor

buffer:

```text
size in bytes
usage: vertex/index/uniform/storage/transfer...
memory/upload 방식
alignment 요구
label과 generation
```

texture:

```text
extent, dimension, layers, mip levels, samples
format
usage: sampled/render target/depth/transfer/storage...
clear/load/store 의미
label과 generation
```

resource를 만든 뒤 usage를 임의로 바꿀 수 있다고 가정하지 않습니다. 초기 descriptor가 후속 pass의 실제 사용을 모두 포함해야 합니다.

### CPU struct와 shader layout

C++ struct의 `sizeof`, member padding과 shader struct layout은 자동으로 같지 않습니다. 특히 `vec3`, matrix, array와 uniform/storage buffer의 alignment가 다를 수 있습니다.

다음 중 하나를 정본으로 삼습니다.

- 명시적 packed serialization 함수
- reflection으로 얻은 offset과 size 검사
- static assertion과 shader-side generated layout
- 작은 marker 값으로 runtime 검증

C++ object memory를 그대로 upload할 때는 trivially copyable 여부, endian, padding 초기화와 alignment를 확인합니다. pointer·`std::string`·virtual object를 byte로 복사하지 않습니다.

### vertex input

vertex buffer layout에는 stride, attribute offset, format와 input rate가 있습니다.

```text
location 0: position, float3, offset 0
location 1: normal,   packed/float3, offset ...
location 2: uv,       float2, offset ...
stride: ...
```

shader location과 pipeline descriptor가 일치해야 합니다. interleaved와 separate stream 중 선택은 update pattern과 cache/bandwidth 측정에 따라 결정합니다. 데이터 배치의 일반 원리는 `computer-architecture`가 소유하며 여기서는 GPU fetch 계약에 적용합니다.

### uniform과 dynamic data

매 frame 변하는 camera/object data는 frame slot별 upload 영역 또는 ring allocator를 사용할 수 있습니다. 필요한 불변식:

- offset alignment 충족
- 기록 범위가 buffer size 안
- 현재 GPU가 읽는 slot을 덮어쓰지 않음
- object 수 증가 시 overflow를 명시적으로 거부하거나 grow
- flush/coherency 요구를 API 계약에 맞춤

한 개 uniform buffer를 매 draw마다 같은 주소에 덮어쓰고 command만 여러 개 기록하면 모든 draw가 마지막 값을 읽을 수 있습니다.

### texture upload와 row pitch

CPU image row stride는 `width * bytes_per_pixel`과 다를 수 있습니다. GPU copy는 row pitch alignment 또는 block-compressed format의 block 단위를 요구할 수 있습니다.

검증 항목:

- source stride와 destination extent
- mip/layer/subresource 범위
- compressed block extent
- channel·numeric·sRGB format
- top-left origin과 필요한 one-time transform
- upload 완료 뒤 staging lifetime

corner/channel marker texture로 결과를 확인합니다.

### resource state와 synchronization

Vulkan 같은 저수준 API는 layout과 access transition을 명시적으로 다룹니다. SDL3 GPU 같은 abstraction은 많은 전환을 내부에서 처리하지만 pass와 usage의 올바른 조합은 여전히 필요합니다. abstraction이 barrier를 숨긴다고 data dependency가 사라지는 것은 아닙니다.

resource 사용 표를 유지합니다.

| resource | pass A | pass B | 위험 |
|---|---|---|---|
| upload buffer | copy source | 없음 | copy 완료 전 재사용 |
| vertex buffer | copy destination | vertex read | upload→draw ordering |
| color texture | render target | sampled | write→read dependency |
| swapchain | render target | present | acquire·submit·present lifecycle |

### resource cache와 generation

asset id만 key로 쓰면 reload 뒤 이전 GPU resource와 혼동할 수 있습니다. `asset id + generation + format/profile`을 key에 포함합니다. pipeline도 shader hash, render target format, depth/blend/raster state와 vertex layout이 key에 포함돼야 합니다.

resource 삭제는 logical removal과 physical destruction을 나눕니다.

```text
active
→ logically retired: 새 frame이 사용하지 않음
→ GPU completion 확인
→ destroyed
```

### memory와 예산

GPU memory usage를 정확히 얻기 어려운 API도 있지만 최소한 요청 bytes와 resource count를 기록합니다. texture mip, duplicate upload, transient attachment와 frame slot 수가 memory에 미치는 영향을 추적합니다. out-of-memory를 null handle 뒤 crash로 만들지 않고 현재 budget과 실패 descriptor를 보고합니다.

## 검증 fixture

- vertex marker로 location/offset/stride 확인
- uniform에 서로 다른 object id와 transform을 여러 draw에 배치
- row padding이 있는 3×2 image upload
- sRGB/color와 UNORM/data texture 비교
- frame slot overwrite mutation
- asset reload generation과 이전 frame 유지
- resize 뒤 이전 depth/color attachment retire
- buffer overflow·invalid alignment 거부

## 흔한 오답

- `sizeof(CppStruct)`와 shader layout이 같다고 가정
- dynamic uniform 하나를 여러 draw 사이에 같은 위치로 덮어씀
- image row stride와 tight packing 혼용
- texture format 이름만 보고 sRGB/data 의미 결정
- C++ wrapper 소멸 시 GPU resource 즉시 파괴
- asset id만 cache key로 사용해 reload generation 충돌
- abstraction API가 모든 data race와 ordering을 자동 해결한다고 판단

## 연결 실습

- [`06-gpu-first-frame`](../../exercises/06-gpu-first-frame/README.md): vertex/uniform/texture upload와 generation trace를 만듭니다.
- [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md): resource cache·frame slot·retirement를 통합합니다.

## 완료 기준

- buffer/texture descriptor와 실제 pass usage를 대조합니다.
- CPU struct, vertex input과 shader layout을 offset·format·marker로 검증합니다.
- transfer와 in-flight resource의 lifetime을 completion event에 연결합니다.
- reload·resize·frame slot에서 generation과 physical destruction을 분리합니다.
