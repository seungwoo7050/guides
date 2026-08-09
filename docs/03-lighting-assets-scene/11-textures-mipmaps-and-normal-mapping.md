# texture·mipmap·normal mapping

## 목표

texture를 단순한 image file이 아니라 format·encoding·sampler·mip·coordinate와 material 의미가 결합된 resource로 다룹니다. mip chain과 LOD가 minification aliasing을 줄이는 과정을 검증하고, tangent-space normal map을 올바른 basis로 world/view 공간에 옮깁니다.

## 시작하기 전에

[샘플링과 mipmap](../01-visual-model/05-sampling-filtering-and-aliasing.md), [색 공간](../01-visual-model/04-images-color-and-alpha.md), [normal과 material](10-normals-lighting-and-materials.md)을 사용합니다.

### texture와 sampler 분리

texture는 texel storage와 format·extent·mip를 소유하고, sampler는 읽는 방식을 소유합니다.

```text
Texture
- extent, layers, mip count
- format와 color/data 의미
- origin과 coordinate convention
- GPU usage와 lifetime

Sampler
- min/mag filter
- mip filter
- address U/V/W
- LOD min/max와 bias
- anisotropy 지원 시 값
```

같은 texture를 다른 sampler로 읽을 수 있으므로 asset metadata와 runtime state를 구분합니다.

### mip chain 생성

각 level은 이전 level을 low-pass filter한 뒤 해상도를 줄입니다. 단순 2×2 box filter는 기준 구현으로 충분하지만 다음을 명시합니다.

- sRGB color는 linear decode 뒤 평균하고 저장 시 encode
- normal map은 vector를 decode·평균·renormalize하고 다시 encode
- roughness/metalness/occlusion 같은 data channel은 의미에 맞는 filter 필요
- alpha mask는 평균 뒤 threshold가 coverage를 바꿀 수 있어 coverage-preserving 보정이 필요할 수 있음
- odd extent와 1 pixel 축 처리

모든 texture에 동일한 byte 평균을 적용하지 않습니다.

### LOD와 trilinear

perspective-correct UV의 screen derivative로 footprint를 추정하고 LOD를 선택합니다. LOD를 integer level로 바로 반올림하면 level 경계에서 popping이 생깁니다. trilinear는 floor/ceil 두 level의 bilinear 결과를 fraction으로 보간합니다.

LOD bias나 clamp는 문제를 숨기는 임시 값이 될 수 있습니다. 선택 level distribution과 UV derivative를 통계로 남겨 scene scale·UV density·sampler 설정 중 무엇이 원인인지 확인합니다.

### normal map encoding

일반 tangent-space normal map은 texture RGB `[0,1]`을 signed `[-1,1]` 방향으로 decode합니다.

```text
n_tangent = normalize(2 * sample.rgb - 1)
```

normal map은 color texture가 아니므로 sRGB decode를 적용하지 않습니다. 일부 형식은 Y channel convention이나 두 channel 복원을 사용합니다. asset 입구에서 convention을 정규화하고 shader마다 임시로 Y를 뒤집지 않습니다.

### tangent basis

vertex position과 UV의 변화로 tangent/bitangent를 계산하거나 asset이 tangent를 제공합니다. basis는 다음을 확인합니다.

- tangent와 normal이 유한하고 길이가 0이 아님
- tangent를 normal에 대해 orthogonalize
- bitangent handedness sign 보존
- mirrored UV에서 방향 반전 처리
- transform 뒤 같은 shading 공간에 있음

보통 vertex에 tangent `xyz`와 handedness `w`를 저장하고 fragment에서 다음 basis를 구성합니다.

```text
T = normalize(T - N * dot(N, T))
B = handedness * cross(N, T)
N_world = normalize(TBN * n_tangent)
```

model의 negative scale과 tangent handedness를 함께 검토합니다.

### texture seams

UV seam에서는 같은 position이 서로 다른 UV와 tangent를 가져야 하므로 vertex가 분리될 수 있습니다. index deduplication이 position만 기준이면 seam이 깨집니다. mesh vertex identity는 position뿐 아니라 normal·UV·tangent·material boundary의 조합입니다.

### compressed format와 streaming

GPU compressed texture, sparse/streaming, virtual texturing은 후속 범위입니다. 하지만 asset 계약에는 다음을 남깁니다.

- source와 runtime format
- mip availability
- upload bytes와 residency 상태
- fallback level 또는 placeholder
- resource version

texture가 아직 resident하지 않을 때 어떤 값이 보이는지 명시합니다.

## 검증 fixture

- 2×2 color marker와 sampler 조합
- checker mip chain의 각 level hash
- linear/sRGB mip 평균 차이
- normal map flat 값 `(0.5,0.5,1)`의 조명 결과
- tangent 방향을 표시하는 debug view
- mirrored UV와 handedness
- seam이 있는 cube 또는 quad
- LOD level color coding과 minification scene
- normal texture에 sRGB가 잘못 적용된 mutation

## 흔한 오답

- normal map을 sRGB texture로 생성·sample
- mip마다 normal vector를 renormalize하지 않음
- UV만 보고 tangent를 공유해 seam과 mirrored island 오류
- tangent `w` 또는 negative scale 무시
- mag filter와 min/mip filter 혼동
- LOD bias로 잘못된 UV scale을 숨김
- source file format과 GPU runtime format을 같은 수명으로 관리

## 연결 실습

- [`02-sampling-and-color`](../../exercises/02-sampling-and-color/README.md): color texture와 sampler의 기준값을 만듭니다.
- [`05-textured-lit-scene`](../../exercises/05-textured-lit-scene/README.md): mip와 tangent-space normal을 lighting에 연결합니다.

## 완료 기준

- texture storage, color/data 의미와 sampler state를 분리합니다.
- texture 종류별 mip 생성 규칙을 설명하고 고정 fixture로 검증합니다.
- tangent basis와 handedness를 통해 normal map을 shading 공간으로 변환합니다.
- seam·LOD·encoding 오류를 debug view와 level 통계로 좁힙니다.
