# 실습 05 — textured lit scene

## 목적

검증된 mesh·material·texture·scene hierarchy를 소프트웨어 renderer에 연결하고, normal transform·mipmap·tangent-space normal·lighting·frustum culling과 간단한 LOD를 통합합니다. asset loader 성공과 renderable scene 성공을 구분합니다.

관련 문서:

- [normal·lighting·material](../../docs/03-lighting-assets-scene/10-normals-lighting-and-materials.md)
- [texture·mipmap·normal mapping](../../docs/03-lighting-assets-scene/11-textures-mipmaps-and-normal-mapping.md)
- [mesh·scene·asset 계약](../../docs/03-lighting-assets-scene/12-meshes-scenes-and-asset-contracts.md)
- [visibility·LOD](../../docs/03-lighting-assets-scene/13-visibility-spatial-organization-and-lod.md)

## 입력 fixture

외부 format loader보다 먼저 코드/JSON fixture를 사용합니다.

- UV seam과 hard normal edge가 있는 cube
- non-uniform scale parent와 child mesh
- color texture, data texture와 flat normal map
- mirrored UV island와 tangent handedness
- 두 LOD mesh와 screen threshold
- frustum 안/밖/교차 object
- invalid index, mismatched attribute, cycle hierarchy, stale handle

외부 glTF를 추가한다면 같은 내부 validation을 통과해야 합니다.

## 구현할 경계

```text
raw fixture
→ semantic validation
→ normalized render asset
→ scene snapshot과 world bounds
→ frustum/LOD
→ perspective UV + mip
→ normal/TBN
→ linear lighting
→ debug/final attachments
```

## 필수 artifact

```text
out/textured-lit-scene/
├── final.ppm
├── base-color.ppm
├── normal-world.ppm
├── ndotl.ppm
├── mip-level.ppm
├── object-id.ppm
├── asset-validation.json
├── culling-lod.json
└── frame.json
```

## 불변식

- 모든 index와 attribute count가 유효합니다.
- hierarchy에 cycle이 없고 world transform version이 일치합니다.
- world bounds가 geometry를 보수적으로 포함합니다.
- non-uniform scale 뒤 normal과 tangent가 유효합니다.
- normal map은 data texture이며 sRGB decode되지 않습니다.
- color texture와 lighting은 linear에서 계산됩니다.
- frustum 밖 object만 거부하며 LOD hysteresis가 경계 진동을 막습니다.

## 알려진 오답

- position만으로 vertex deduplication
- normal에 model matrix 직접 적용
- normal map sRGB 처리
- mipmap을 encoded byte 평균으로 생성
- world AABB를 min/max 두 점만 변환
- hierarchy cycle 무시
- distance threshold equality에서 LOD 진동

## 완료 근거

- final image와 다섯 debug attachment
- asset validation 정상·실패 목록
- culling/LOD input/output count와 선택 metric
- known-bad mutation 최소 네 개 거부
- 외부 format을 사용했다면 source/hash/license/import profile

## 준비·workspace·stage 검사

[공통 workspace 절차](../README.md#workspace-준비와-공개-명령)의 누적 learner 사본에서 asset·scene 단계를 추가합니다.

```sh
cmake -S exercises/08-renderer-capstone/project -B build/workspace -DCG_IMPLEMENTATION=workspace -DCG_GPU=off
cmake --build build/workspace
python3 exercises/check.py --impl workspace --stage 05-textured-lit-scene --expect pass --gpu off
python3 exercises/check.py --impl reference --stage 05-textured-lit-scene --expect pass --gpu off
```

checker는 정상 scene뿐 아니라 invalid index·attribute, cycle, stale handle, conservative bounds, non-uniform normal, data texture와 LOD hysteresis를 검사하고 final/debug attachment를 reference와 비교합니다. starter와 최소 네 known-bad mutation은 거부돼야 합니다.

사람 검토에서는 raw asset과 renderable asset의 실패 경계, mirrored UV·normal 공간의 선택, frustum/LOD 결정이 결과와 work count를 함께 보존하는지 설명합니다. 외부 asset을 사용했다면 source·hash·license도 확인합니다.

`make clean`은 생성물만 제거합니다. asset validation과 culling report를 먼저 보존하고 잘못된 입력을 reference로 교체하지 않은 채 원인별로 복구합니다. workspace는 자동 삭제하지 않습니다.
