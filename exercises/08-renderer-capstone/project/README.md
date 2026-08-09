# 누적 C++20 renderer project

이 project는 실습 01–08이 공유하는 `starter`, 결정적 `reference`와 learner `workspace`를 같은 공개 CLI로 빌드합니다. 문서만 있는 skeleton이 아니라 CPU visual/raster reference, lifecycle simulator와 지원 환경의 SDL GPU offscreen reference를 포함합니다.

## 필수 환경

- Python 3.10 이상: 공개 checker와 repository 검증
- C++20 compiler: 세 구현 profile과 sanitizer build
- CMake 3.20 이상: configure, build와 CTest
- SDL 3.4.10 이상: `CG_GPU=auto|required`에서 실제 GPU code를 구성할 때 사용

이번 확인 환경은 SDL 3.4.12이며 stable compatibility floor는 3.4.10입니다. 정확한 판본과 검증 범위는 [버전 기준](../../../reference/version-baseline.md)을 따릅니다.

## 구현 profile

| `CG_IMPLEMENTATION` | source | 완료 기대 |
|---|---|---|
| `reference` | `reference/visual.cpp`, `raster.cpp`, `gpu.cpp` | 공개 artifact·invariant와 known-bad oracle의 기준 |
| `starter` | `starter/` | 유효한 CLI 뒤 명시적 `not-implemented` exit 3 |
| `workspace` | `workspace/` | learner 구현. 디렉터리가 없으면 configure가 안전하게 실패 |

저장소 root의 `scripts/new-workspace.sh`는 starter를 Git에서 제외된 `workspace/`에 한 번만 복사합니다. 기존 workspace가 있으면 덮어쓰지 않으며 build·checker·검증도 learner source를 삭제하지 않습니다.

## GPU mode

| `CG_GPU` | configure와 실행 |
|---|---|
| `off` | SDL을 검색하지 않습니다. CPU renderer와 lifecycle simulator만 평가합니다. |
| `auto` | SDL 3.4.10 이상을 찾으면 GPU code를 빌드합니다. package 또는 runtime device가 없으면 실제 GPU stage는 미평가로 남을 수 있습니다. |
| `required` | SDL을 찾지 못하면 configure가 실패합니다. 실제 GPU stage까지 성공해야 GPU 근거로 사용할 수 있습니다. |

`off`의 성공과 `auto`의 GPU 미실행을 actual GPU 통과로 표현하지 않습니다.

## build와 CTest

저장소 root에서 reference를 빌드합니다.

```sh
cmake -S exercises/08-renderer-capstone/project -B build/reference \
  -DCG_IMPLEMENTATION=reference -DCG_GPU=auto
cmake --build build/reference
ctest --test-dir build/reference --output-on-failure
```

공개 executable은 `build/reference/cg-render`, test executable은 `build/reference/cg-tests`입니다. CLI 계약은 다음과 같습니다.

```text
cg-render
  --stage 01-transform-trace..08-renderer-capstone
  --scene <stable-id>
  --backend software|lifecycle-sim|sdl-gpu
  --out <새 artifact directory>
  [--frames 1..10000]
  [--mutation <contract-id>]
```

잘못된 인자는 exit 2, 의도적으로 미완성인 starter/workspace stage는 exit 3, invariant 위반은 exit 4, 지원되지 않는 GPU runtime은 exit 5로 구분합니다.

## shader source와 offline profile

[`shaders/triangle.metal`](shaders/triangle.metal)은 현재 macOS Metal runtime이 실제로 사용하는 MSL source입니다. CMake configure가 이 추적 source를 build directory의 generated header에 포함하고 SDL에 `SDL_GPU_SHADERFORMAT_MSL`로 전달합니다.

[`shaders/triangle.hlsl`](shaders/triangle.hlsl)은 portable offline source입니다. SDL_shadercross commit, entry point, vertex layout, tracked MSL hash와 SPIR-V·DXIL·MSL 생성 명령은 [`shaders/manifest.json`](shaders/manifest.json)이 유일한 정본입니다. 고정 commit은 `e55cf5e31ced6f3d1be5cc6d0c50e99384f9f4ba`입니다.

기본 build는 SDL_shadercross를 요구하지 않습니다. manifest 명령이 만든 `.spv`, `.dxil`, `.msl`과 선택적으로 만든 `.metallib`은 `build/shaders/` 아래에만 두며 source로 커밋하지 않습니다.

## 실제 GPU 경로와 측정 한계

현재 actual GPU reference는 macOS Metal에서 offscreen RGBA8 color·D16 depth target을 만들고 upload, indexed draw, readback, submit과 fence completion을 실행합니다. 별도 persistent probe는 같은 device에서 실제 slot 2개와 submission 3개를 사용해 completion 뒤 slot 0을 재사용하고, zero extent를 건너뛰며, 64×64 generation 1에서 96×72 generation 2로 전환한 뒤 gen1 retire와 gen2 readback·retire를 수행합니다. model과 actual의 12개 사건, 두 extent의 런타임 correctness hash와 96×72 PPM을 artifact로 대조합니다.

tracked MSL/HLSL shader의 입력은 position과 vertex color뿐입니다. texture·sampler·material·normal·light resource를 bind하거나 sample/shade하지 않으므로, 이 actual path의 image 비교는 실습 05의 textured lit scene GPU parity를 증명하지 않습니다.

다음은 사람 검토 또는 명시적 미지원 대상으로 남습니다.

- window/swapchain과 실제 resize·minimize·high-DPI
- Xcode·RenderDoc·PIX capture file과 label 대응
- Vulkan·D3D12 등 두 번째 backend runtime
- 장시간 frame·device-loss stress
- texture/material/normal/lighting의 GPU 이식과 단계별 debug attachment

`submit_to_fence_ns`는 CPU steady clock으로 submit 직전부터 fence wait 반환까지 잰 wall time입니다. GPU timestamp나 render-pass 실행 시간으로 해석하지 않습니다.

CPU reference도 범위를 숨기지 않습니다. 자동 checker는 비자명한 LH camera, six-plane attribute clipping, screen-affine NDC depth, `SceneSnapshot` vertex color·normal+marker texture+단순 lighting, mutation 첫 차이와 culling/LOD work count를 재계산합니다. cube·mirrored TBN과 범용 외부 asset loader는 learner/human 범위입니다.

## fixture provenance와 라이선스

project에는 외부 image, mesh 또는 scene asset을 포함하지 않습니다. `fixtures/scene-v1.json`과 `fixtures/marker-texture.json`은 `repository-generated-fixture`, `external_asset: false`, `license: MIT` provenance를 명시합니다. invalid asset과 resource event case도 이 저장소가 작성한 JSON test input이며 [저장소 코드·JSON의 MIT 계약](../../../LICENSE.md)을 따릅니다.

향후 외부 asset을 추가하면 source URL, content hash, 원본 license와 import profile을 함께 기록해야 합니다. repository-generated fixture라는 표기로 외부 자료의 출처를 대신하지 않습니다.

## 공개 checker와 repository 검증

한 stage는 다음처럼 확인합니다.

```sh
python3 exercises/check.py \
  --impl reference \
  --stage 01-transform-trace \
  --expect pass \
  --gpu off
```

저장소 전체 검증은 `verify.sh`가 고유 임시 복사본에서 수행합니다. 원본 source와 workspace는 변경하지 않고 다음을 실행합니다.

- repository 문서·상대 링크·anchor·contract와 verifier negative controls
- PPM oracle
- starter의 명시적 미완성 경계
- reference stages와 known-bad mutations
- workspace 생성·비파괴 검사
- release build·CTest
- 지원되는 compiler의 address/undefined sanitizer
- `VERIFY_GPU=auto|required|off` 결정에 따른 GPU 검사

이 자동 검사는 공개 행동과 artifact의 회귀 근거입니다. 교육적 완성, 실제 window resize, 외부 capture tool 또는 실행하지 않은 backend를 증명하지 않습니다. `auto`에서 GPU가 미평가됐다면 로그의 `GPU_NOT_EVALUATED`를 보존하고 성공한 GPU 검사로 바꾸어 말하지 않습니다.

## 생성물과 정리

build와 artifact는 source 밖의 `build/`, `out/` 또는 명시한 임시 디렉터리에 둡니다. generated shader/header/binary를 tracked source에 복사하지 않습니다. 정리할 때도 learner `workspace/`와 실패 조사에 필요한 artifact를 예고 없이 삭제하지 않습니다.
