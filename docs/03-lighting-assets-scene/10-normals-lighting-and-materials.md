# normal·조명·material

## 목표

표면 위치·normal·view direction·light와 material parameter를 같은 공간과 단위로 맞춰 단순한 조명 모델을 구현합니다. 보기 좋은 숫자를 임의로 곱하는 대신 각 항의 의미·범위·색 공간과 에너지 한계를 기록하고, normal transform과 shading 실패를 중간 attachment로 검증합니다.

## 시작하기 전에

이 문서는 물리 기반 렌더링 전체를 가르치지 않습니다. 먼저 diffuse와 제한된 specular 모델로 입력 계약을 고정합니다. [좌표 공간](../01-visual-model/02-coordinate-spaces-and-transforms.md), [linear color](../01-visual-model/04-images-color-and-alpha.md), [perspective interpolation](../02-software-rasterization/07-interpolation-perspective-and-derivatives.md)을 사용합니다.

### shading 공간

lighting에 사용하는 position, normal, light direction과 view direction은 같은 공간에 있어야 합니다. world space 또는 view space를 선택할 수 있지만 frame artifact에 기록합니다.

과정의 기본 설명은 world space를 사용합니다.

```text
P: fragment world position
N: normalized world normal
V: normalize(camera_position - P)
L: normalize(light_position - P) 또는 directional light 방향
```

`N`, `V`, `L`의 길이가 0이거나 non-finite이면 shading을 계속하지 않고 primitive/material id와 함께 거부 또는 debug color로 표시합니다.

### normal의 의미

normal은 위치가 아니라 표면의 접평면에 수직인 방향입니다. 비균일 scale에서는 inverse-transpose normal matrix를 사용하고 보간 뒤 normalize합니다. face normal과 vertex normal의 역할도 다릅니다.

- face normal: 삼각형 기하에서 계산한 평평한 방향
- vertex normal: 인접 면을 이용해 asset이 제공한 부드러운 shading 방향
- normal map: texture가 제공한 tangent-space 미세 방향

이 세 값을 같은 이름으로 덮어쓰지 않고 debug attachment로 각각 확인합니다.

### diffuse 기준선

Lambert diffuse의 각도 항은 다음과 같습니다.

```text
NdotL = max(dot(N, L), 0)
diffuse = base_color * light_radiance * NdotL / pi
```

교육용 renderer에서 `1/pi`를 생략한 고전적인 식을 사용할 수도 있지만 material과 light intensity의 의미가 달라집니다. 어떤 식을 정본으로 쓰는지 고정합니다. 과정에서는 에너지 의미를 드러내기 위해 `1/pi`를 포함한 식을 권장합니다.

point light에는 distance attenuation이 필요합니다. 단순 inverse-square는 거리가 0에 가까우면 발산하므로 최소 거리, finite light size 또는 명시적 clamp 정책이 필요합니다. 임의의 `1/(a+bd+cd²)` 계수를 사용할 때도 단위와 tuning 목적을 문서화합니다.

### specular 기준선

초기에는 Blinn–Phong 같은 제한된 모델로 half vector와 roughness 비슷한 parameter의 효과를 관찰할 수 있습니다.

```text
H = normalize(L + V)
specular = color * pow(max(dot(N, H), 0), exponent)
```

이 식은 완전한 microfacet BRDF가 아니며 exponent와 실제 roughness를 같은 물리 parameter로 취급하지 않습니다. 후속 PBR 프로젝트에서는 Fresnel, normal distribution, geometry term과 에너지 보존을 별도 학습합니다.

### material 계약

material은 shader에 전달하는 임의 struct가 아니라 surface의 입력 의미를 고정합니다.

```text
Material
├── base_color_linear 또는 sRGB texture 참조
├── alpha mode: opaque / mask / blend
├── double_sided
├── normal texture와 scale
├── diffuse/specular 또는 metallic/roughness profile
└── emissive
```

서로 다른 material profile의 parameter를 하나의 shader에서 암묵적으로 해석하지 않습니다. unsupported extension이나 누락 texture에는 명시적 fallback 또는 asset 거부 정책을 둡니다.

### gamma와 clamp

lighting 중간 값을 sRGB로 encode하거나 0–1로 너무 일찍 clamp하지 않습니다. negative나 매우 큰 값은 입력 오류, 모델 특성 또는 HDR 범위일 수 있습니다. debug build에서는 non-finite와 예상 범위를 통계로 남기고, tone mapping/output 단계에서 display 범위로 변환합니다.

## debug attachment

최종 shaded color만 보면 어느 입력이 잘못됐는지 알기 어렵습니다. 다음 view를 제공합니다.

- world normal을 `[-1,1] → [0,1]`로 mapping한 image
- `N·L`, `N·V`, light distance
- base color와 sampled material channel
- diffuse, specular, emissive를 분리한 attachment
- invalid/renormalized normal 수
- material id와 light count

normal debug view는 표시용 encoding일 뿐 실제 lighting 계산 값은 linear signed vector입니다.

## 검증 fixture

- 한 평면과 directional light의 정면·측면·후면
- non-uniform scale object의 normal
- flat vs smooth normal
- camera를 움직일 때 diffuse는 유지되고 specular가 변화
- light distance 두 배에서 attenuation 변화
- black/white/colored base material
- alpha mode와 double-sided 설정
- zero-length normal과 invalid light parameter 거부

## 흔한 오답

- world position과 view-space normal을 dot
- normal transform에 translation 또는 model matrix 직접 적용
- normal 보간 뒤 normalize 생략
- sRGB base color에서 조명 계산
- specular를 base color에 항상 곱해 금속/비금속 의미 혼동
- 조명 결과를 각 항마다 clamp해 에너지 관계 파괴
- debug normal image의 0–1 값을 실제 normal로 재사용

## 연결 실습

- [`05-textured-lit-scene`](../../exercises/05-textured-lit-scene/README.md): normal transform, diffuse/specular와 material validation을 통합합니다.
- [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md): software/GPU의 normal·lighting attachment를 비교합니다.

## 완료 기준

- lighting 입력의 공간·정규화·단위와 color encoding을 명시합니다.
- 비균일 scale과 보간 뒤 normal을 올바르게 처리합니다.
- diffuse·specular·emissive와 material parameter를 독립 attachment로 관찰합니다.
- 단순 모델의 한계와 후속 PBR에서 추가할 계약을 구분합니다.
