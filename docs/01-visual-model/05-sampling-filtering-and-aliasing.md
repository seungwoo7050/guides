# 샘플링·필터링·aliasing

## 목표

연속적인 표면 신호를 유한한 pixel과 texel에서 평가할 때 생기는 aliasing을 이해하고, sample 위치·좌표 mapping·address mode·filter·mipmap 선택을 명시적인 계약으로 구현합니다. “bilinear가 더 부드럽다”는 설명을 넘어 어떤 texel과 level이 결과를 소유하는지 검증합니다.

## 시작하기 전에

[이미지·색 공간·alpha](04-images-color-and-alpha.md)의 linear 연산 규칙을 사용합니다. texture coordinate는 과정 규약에서 top-left origin, `+V down`이며 정규화 범위 `[0,1]`을 기본으로 합니다.

### pixel과 texel은 면적이고 sample은 점이다

framebuffer pixel `(x, y)`의 기본 sample 위치는 `(x+0.5, y+0.5)`입니다. texture의 texel center도 크기 `W×H`일 때 다음과 같이 볼 수 있습니다.

```text
u_center(i) = (i + 0.5) / W
v_center(j) = (j + 0.5) / H
```

정규화 UV를 texel 공간으로 옮길 때 사용하는 식은 filter convention과 함께 고정합니다. 예를 들어 bilinear에서 `u*W - 0.5`를 사용하면 UV 0이 첫 texel 중심보다 반 texel 바깥에 해당합니다. clamp/repeat/border가 이 좌표에 어떤 값을 주는지 fixture로 확인합니다.

### nearest와 bilinear

nearest는 가장 가까운 하나의 texel을 선택합니다. tie-breaking과 음수 좌표 처리까지 정해야 결정적입니다.

bilinear는 2×2 texel을 두 축으로 선형 보간합니다. color texture라면 각 texel을 linear RGB로 decode한 뒤 보간합니다. straight alpha texture를 그대로 보간할지 premultiplied로 변환할지 asset 계약과 일치해야 합니다.

### address mode

- clamp-to-edge: 마지막 texel의 edge 값을 연장
- repeat: 정규화 좌표의 정수 부분을 제거해 반복
- mirrored repeat: 반복 구간마다 방향 반전
- border: 범위 밖에 고정 색 또는 값

C/C++의 음수 나머지 연산을 그대로 repeat에 사용하면 언어별 기대와 다를 수 있습니다. 수학적 floor 기반 wrap을 기준으로 테스트합니다.

### aliasing은 확대보다 축소에서 더 어렵다

한 pixel footprint가 texture의 많은 texel을 덮을 때 한두 texel만 sample하면 고주파 신호가 낮은 주파수로 잘못 보입니다. mipmap은 미리 low-pass filtered한 여러 해상도 level을 제공해 footprint에 맞는 정보를 선택합니다.

```text
level 0: W × H
level 1: max(1, W/2) × max(1, H/2)
...
```

mip 생성은 linear 공간에서 수행하고, 홀수 크기와 alpha를 어떻게 처리하는지 정합니다. 평균 하나만으로 모든 reconstruction 문제를 해결하지는 않지만 안정적인 기준선을 제공합니다.

### texture footprint와 LOD

GPU에서는 fragment quad의 UV 미분값으로 screen pixel이 texture에서 차지하는 footprint를 추정합니다. 개념적으로 다음 크기를 사용할 수 있습니다.

```text
rho_x = length(dUV/dx * texture_extent)
rho_y = length(dUV/dy * texture_extent)
rho   = max(rho_x, rho_y)
lod   = log2(rho)
```

software 정본에서는 이웃 sample이나 triangle plane에서 미분값을 계산할 수 있습니다. edge·작은 triangle·분기에서 derivative가 안정적이지 않을 수 있으므로 invalid 정책과 clamp 범위를 둡니다.

trilinear filtering은 인접 mip level의 bilinear 결과를 level fraction으로 보간합니다. anisotropic filtering은 길게 늘어난 footprint를 하나의 isotropic level로 근사할 때 잃는 정보를 줄이지만 이 과정의 필수 구현은 아닙니다.

### geometry aliasing과 texture aliasing

mipmap은 texture 신호만 줄입니다. 가느다란 triangle, edge와 subpixel geometry의 깜빡임은 coverage sample 수와 reconstruction 문제입니다. multisampling은 pixel 안 여러 coverage sample을 평가해 edge를 더 잘 적분하지만 shader·depth·resolve 계약이 추가됩니다. 기본 rasterizer는 center sample 하나로 시작하고, MSAA는 후속 프로젝트로 남깁니다.

## 검증 fixture

- 2×2 corner marker의 nearest/bilinear 기준값
- UV 0, 1, 정확한 texel center와 경계 사이 값
- 음수·1 초과 UV에서 clamp/repeat/mirror 결과
- black/white checker의 linear mip 평균
- 1×N, odd extent와 마지막 1×1 level
- 축소되는 checker에서 level 0 고정과 mip 선택 차이
- UV가 뒤집힌 triangle과 texture origin marker
- alpha edge에서 straight/premultiplied filtering 차이

통계에는 선택한 mip level 분포와 out-of-range UV 수를 남깁니다.

## 흔한 오답

- `u*W`를 그대로 정수 cast해 UV 1에서 범위를 벗어남
- 음수 repeat를 `%`만으로 구현
- sRGB byte를 직접 bilinear·mipmap 평균
- texture minification을 bilinear 하나로 해결했다고 판단
- mip level마다 alpha 표현이나 channel 의미가 바뀜
- geometry edge aliasing을 texture filter 문제로 오진
- GPU derivative를 모든 fragment에서 정확한 미분으로 취급

## 연결 실습

- [`02-sampling-and-color`](../../exercises/02-sampling-and-color/README.md): address mode, nearest/bilinear와 linear color fixture를 구현합니다.
- [`05-textured-lit-scene`](../../exercises/05-textured-lit-scene/README.md): perspective-correct UV와 mip 선택을 textured scene에 연결합니다.

## 완료 기준

- pixel center와 texel center 규약을 수식과 fixture로 고정합니다.
- nearest·bilinear·address mode가 선택하는 texel과 weight를 trace합니다.
- linear 공간에서 mip chain을 만들고 footprint 기반 LOD를 설명합니다.
- texture aliasing, geometry aliasing과 color/alpha 오류를 서로 다른 근거로 구분합니다.
