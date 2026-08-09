# 이미지·색 공간·alpha

## 목표

pixel format의 숫자를 빛의 양과 같은 것으로 취급하지 않고, encoding·color space·channel order·alpha 표현을 경계마다 명시합니다. texture filtering, lighting과 blending을 linear 공간에서 수행하고, 저장·표시 시점의 sRGB encoding과 premultiplied alpha 계약을 검증합니다.

## 시작하기 전에

이 문서는 전문 color science, ICC profile, HDR display calibration 전체를 다루지 않습니다. 렌더러가 흔히 처리하는 RGB image의 최소 계약을 고정합니다.

### image는 크기만 있는 byte 배열이 아니다

한 image resource에는 최소한 다음 metadata가 필요합니다.

```text
extent: width × height × layers
format: channel 수·순서·bit width·numeric interpretation
color encoding: linear, sRGB 또는 명시된 다른 transfer
alpha mode: none, straight, premultiplied
origin과 row stride
usage: sampled, render target, transfer source/destination 등
```

`RGBA8`이라는 이름만으로 linear인지 sRGB인지 알 수 없습니다. GPU format이 `*_SRGB`인지, loader가 decode를 수행했는지, shader가 직접 변환하는지 한 곳에서 결정합니다.

### linear 연산과 sRGB encoding

sRGB 값은 저장과 표시를 위한 비선형 encoding입니다. 두 sRGB byte를 그대로 평균하면 실제 빛의 평균과 다릅니다. 다음 연산은 linear RGB에서 수행합니다.

- texture bilinear/trilinear filtering
- lighting과 material 계산
- additive 연산
- alpha blending
- mipmap downsampling

일반적인 color texture는 sample 시 sRGB decode가 적용되도록 format을 선택하고, normal·roughness·metalness·depth·id 같은 data texture는 sRGB decode를 적용하지 않습니다.

과정 fixture는 표준 sRGB transfer의 piecewise decode/encode를 사용합니다. 단순 `pow(x, 2.2)`는 근사 비교로만 언급하고 정본 검사에 사용하지 않습니다.

### channel order와 numeric format

CPU memory의 RGBA byte 순서와 GPU format의 logical channel이 같다고 가정하지 않습니다. UNORM, SNORM, UINT, SINT, FLOAT는 shader가 받는 값의 의미가 다릅니다.

예:

- `R8_UNORM`: byte 0–255를 0–1로 정규화
- `R8_UINT`: shader에서 정수 0–255
- depth format: 일반 color처럼 sample/write하지 못할 수 있음
- packed format: memory byte 순서와 이름만 보고 해석하면 안 됨

upload 전후에 작은 2×2 marker texture를 읽거나 캡처해 channel과 origin을 확인합니다.

### straight alpha와 premultiplied alpha

straight alpha에서는 RGB가 alpha와 독립된 원래 색을 나타냅니다. premultiplied alpha에서는 이미 `rgb *= alpha`가 적용돼 있습니다.

straight source를 linear 공간에서 over 연산하면 다음과 같습니다.

```text
out.rgb = src.rgb * src.a + dst.rgb * (1 - src.a)
out.a   = src.a + dst.a * (1 - src.a)
```

premultiplied source는 다음처럼 계산합니다.

```text
out.rgb = src.rgb + dst.rgb * (1 - src.a)
out.a   = src.a + dst.a * (1 - src.a)
```

texture edge에서 transparent pixel의 RGB가 임의 값이면 straight alpha filtering 중 색 번짐이 생길 수 있습니다. premultiplied representation은 filtering과 compositing의 경계를 더 안정적으로 만들지만, loader·shader·blend state·저장 형식이 모두 같은 계약을 따라야 합니다.

### alpha는 투명도 하나만 뜻하지 않는다

alpha channel이 다음 중 무엇인지 asset 계약에서 구분합니다.

- coverage 또는 opacity
- mask threshold 입력
- UI compositing alpha
- 사용하지 않는 padding
- 별도 data channel

opaque geometry에서 alpha를 무조건 1로 쓰지 않는 pipeline도 있으므로 render target의 의미를 문서화합니다.

### HDR과 tone mapping의 위치

초기 lighting target은 float 또는 충분한 범위의 linear color로 생각합니다. display target에 바로 clamp하면 밝기 관계가 사라집니다. HDR 전체 과정은 범위 밖이지만 다음 경계는 구분합니다.

```text
linear scene-referred lighting
→ exposure/tone mapping
→ display-referred linear color
→ sRGB encoding
→ output format
```

소프트웨어 정본은 제한된 LDR fixture를 사용하되, 어느 단계에서 clamp하는지 명시합니다.

## 검증 fixture

- sRGB 0, 임계 구간, 0.5, 1의 decode/encode round-trip
- black/white texel의 linear 평균과 sRGB byte 평균 차이
- data texture가 sRGB decode되지 않음
- RGBA channel marker와 top-left origin
- straight와 premultiplied alpha의 동일한 시각 결과
- alpha 0·1과 두 반투명 layer의 합성
- NaN·infinity·negative linear color의 정책

최종 screenshot만 비교하지 말고 decode 뒤 linear 값과 blending 전후 값을 JSON으로 기록합니다.

## 흔한 오답

- 모든 8-bit texture를 sRGB color로 취급
- sRGB 값에서 lighting과 mipmap 평균 계산
- premultiplied texture에 straight blend factor 사용
- alpha 0 pixel의 RGB를 무시해 filtering edge에 색 번짐 생성
- output attachment와 texture asset의 encoding을 같은 것으로 가정
- channel order 오류를 shader swizzle로 여러 곳에서 임시 보정

## 연결 실습

- [`02-sampling-and-color`](../../exercises/02-sampling-and-color/README.md): sRGB decode, bilinear filtering과 alpha 합성 기준값을 만듭니다.
- [`05-textured-lit-scene`](../../exercises/05-textured-lit-scene/README.md): color texture와 data texture를 구분해 material에 적용합니다.

## 완료 기준

- image resource의 format·encoding·alpha·origin·stride를 명시합니다.
- filtering·lighting·blending을 linear 공간에서 수행하고 output encoding 경계를 구분합니다.
- straight와 premultiplied alpha의 blend 식과 texture edge 차이를 fixture로 설명합니다.
- channel·origin·encoding 오류를 작은 marker image와 중간 값으로 좁힙니다.
