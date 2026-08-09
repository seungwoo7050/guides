# mesh·scene·asset 계약

## 목표

외부 mesh와 scene을 “loader가 성공했으니 유효하다”고 가정하지 않고, 좌표·index·vertex layout·material·hierarchy·resource 참조를 renderable snapshot으로 변환하는 입구 계약을 설계합니다. parser 오류, 의미 오류와 GPU upload 오류를 분리해 거부 근거를 남깁니다.

## 시작하기 전에

이 문서는 glTF나 특정 file format의 모든 필드를 가르치지 않습니다. 기본 원리는 API 중립적이며, glTF 2.0 같은 공개 scene format은 후속 구현 프로필로 사용할 수 있습니다. 외부 asset을 직접 읽기 전에 코드 fixture로 동일한 내부 구조를 검증할 수 있어야 합니다.

### raw asset와 render asset 분리

```text
file bytes
→ parsed document
→ validated semantic asset
→ normalized render asset
→ GPU resources
→ scene instance snapshot
```

각 단계의 실패가 다릅니다.

- bytes/parser: 잘린 file, 잘못된 JSON/binary 구조
- semantic: 범위를 벗어난 accessor/index, 누락 참조, invalid transform
- normalization: 좌표·unit·color·tangent convention 변환 실패
- upload: 지원하지 않는 format, memory/resource 생성 실패
- instance: 순환 hierarchy, 파괴된 handle, material mismatch

loader가 default 값으로 계속 진행할 항목과 전체 asset을 거부할 항목을 명시합니다.

### mesh primitive 계약

내부 primitive는 최소한 다음을 가집니다.

```text
vertex count와 index count
primitive topology
position stream
선택 normal·tangent·UV·color stream
index type와 범위
material handle
local bounds
```

검증:

- position은 필수이며 finite
- 모든 enabled attribute의 vertex count가 일치
- index가 vertex count 미만
- triangle list라면 index count가 3의 배수
- NaN·infinity·0-length normal 정책
- bounds가 모든 position을 포함
- empty primitive와 degenerate 비율 기록

GPU buffer offset·stride·format은 내부 semantic과 분리합니다. packed GPU layout으로 변환하기 전 canonical CPU representation을 둘 수 있습니다.

### index와 vertex identity

index buffer는 position만 공유하는 것이 아니라 vertex 전체 attribute tuple을 참조합니다. UV seam, hard normal edge와 material boundary에서 같은 position을 가진 별도 vertex가 필요합니다. 잘못된 deduplication은 기하보다 shading seam으로 나타납니다.

16-bit/32-bit index 선택은 vertex count와 backend 지원을 확인합니다. byte offset과 element index를 혼용하지 않습니다.

### transform hierarchy

scene node는 local transform과 parent 관계를 갖습니다.

```text
world(node) = world(parent) * local(node)
```

검증:

- parent 참조 유효
- cycle 없음
- 한 node의 parent 정책 명확
- matrix와 TRS가 동시에 있을 때 format 규칙 준수
- singular transform 처리
- unit·axis conversion은 root 또는 asset normalization에서 한 번 수행

world transform cache는 scene version과 함께 invalidation합니다. node 수정 뒤 descendant가 이전 transform을 읽지 않게 합니다.

### handle과 lifetime

scene node가 raw pointer로 mesh·material·texture를 가리키면 asset reload와 GPU retirement가 어려워집니다. handle에는 id와 generation을 둘 수 있습니다.

```text
MeshHandle { index, generation }
```

lookup 실패는 stale handle이며 다른 resource를 우연히 가리키지 않아야 합니다. CPU asset lifetime과 GPU resource lifetime은 별도입니다. reload 시 새 generation을 publish하고 기존 frame이 사용하는 resource는 GPU 완료 뒤 retire합니다.

### bounds

AABB/sphere는 culling과 debugging에 사용합니다. local bounds를 world로 옮길 때 단순히 min/max 두 점만 변환하면 rotation에서 틀립니다. AABB corner를 변환해 새 bounds를 만들거나 center/extent 행렬 방법을 사용합니다. bounds가 보수적으로 geometry를 포함한다는 불변식을 fixture로 검사합니다.

### asset metadata

최소한 다음을 기록합니다.

- source URI와 content hash
- format/version
- import profile과 tool version
- 좌표·unit·color·normal convention
- 생성된 mesh/material/texture id
- warning과 fallback
- normalized artifact hash

파일 timestamp만으로 cache key를 만들지 않습니다.

## glTF 구현 프로필의 경계

첫 외부 format으로 glTF 2.0을 선택할 수 있습니다. 그러나 이 가이드는 loader 전체 답안을 제공하지 않습니다. 다음을 공식 명세에서 확인하고 mapping 문서를 작성합니다.

- buffer/bufferView/accessor bounds와 alignment
- component type·normalized 의미
- node TRS/matrix와 hierarchy
- primitive mode와 material
- texture/sampler/image와 color/data texture 의미
- extension 지원/거부 정책

지원하지 않는 extension을 무시할 때 결과 의미가 바뀌는지 판단해야 합니다.

## 검증 fixture

- 최소 triangle과 indexed quad
- out-of-range index
- mismatched attribute count
- NaN position과 zero normal
- UV seam/hard edge vertex
- cyclic scene hierarchy
- parent-child transform
- stale generation handle
- rotated/scaled mesh의 world bounds
- unsupported material/extension

## 흔한 오답

- parser 성공을 renderable asset 성공으로 취급
- position만 기준으로 vertex deduplication
- index element와 byte offset 혼용
- min/max 두 점만 변환해 world AABB 계산
- axis/UV flip을 loader와 shader에서 중복 수행
- asset reload 즉시 GPU resource 파괴
- warning으로 fallback한 상태를 artifact에 기록하지 않음

## 연결 실습

- [`05-textured-lit-scene`](../../exercises/05-textured-lit-scene/README.md): validated mesh·material·texture snapshot을 구성합니다.
- [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md): asset generation과 GPU retirement를 frame lifecycle에 연결합니다.

## 완료 기준

- bytes에서 GPU resource까지 단계별 상태와 실패를 구분합니다.
- mesh/index/attribute/hierarchy/bounds 불변식을 loader 밖에서도 검사합니다.
- 좌표·unit·색·normal convention을 입구에서 한 번 정규화합니다.
- handle generation과 GPU retirement로 reload 중 기존 frame의 수명을 보존합니다.
