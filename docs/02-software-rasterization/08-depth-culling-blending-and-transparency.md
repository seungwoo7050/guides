# 깊이·culling·blending·투명도

## 목표

여러 primitive의 fragment가 같은 framebuffer sample을 차지할 때 depth test, depth write, face culling, color blending과 draw order가 최종값을 결정하는 순서를 명시합니다. opaque와 transparent 경로를 분리하고, color/alpha representation과 attachment 초기 상태를 함께 검증합니다.

## 시작하기 전에

[보간과 perspective](07-interpolation-perspective-and-derivatives.md)에서 유효한 NDC depth와 linear color를 제공합니다. [이미지·색·alpha](../01-visual-model/04-images-color-and-alpha.md)의 색 공간과 alpha 계약을 사용합니다.

### depth attachment의 상태

한 sample의 depth 상태에는 최소한 다음이 있습니다.

```text
clear value
comparison operation
write enabled 여부
format과 precision
현재 저장값
```

과정의 기본 conventional depth는 near 0, far 1이며 clear 1, compare `less`를 사용합니다. `less-or-equal`, reversed-Z 또는 다른 정책을 선택하면 projection과 clear·compare를 함께 바꿔야 합니다.

fragment 처리의 기본 흐름은 다음처럼 설명할 수 있습니다.

```text
coverage
→ interpolated depth
→ depth/stencil test
→ fragment shading 또는 조기 검사
→ color blend
→ depth/color write
```

실제 GPU는 early/late test와 최적화를 수행할 수 있으므로 shader side effect, discard와 depth write가 있을 때 실행 순서 보장을 추측하지 않습니다. software 정본은 명시적인 교육용 순서를 사용하고 GPU capture에서 실제 state를 확인합니다.

### depth test와 depth write 분리

transparent object도 opaque geometry에 가려져야 하므로 depth test는 켤 수 있지만, 일반 alpha blending 경로에서 depth write를 켜면 먼저 그린 transparent surface가 뒤 surface를 완전히 막을 수 있습니다.

기본 경로:

- opaque: depth test on, depth write on, blending off
- cutout/mask: alpha threshold 뒤 opaque와 같은 depth 처리
- transparent: depth test on, depth write off, blending on, 보통 back-to-front 정렬

이것은 모든 transparency 문제의 완전한 해결책은 아닙니다. intersecting geometry, self-overlap와 per-pixel order에는 추가 기법이 필요하며 필수 범위 밖입니다.

### culling

face culling은 depth test 이전에 primitive를 제거합니다. winding convention, negative scale, double-sided material과 clipping 결과가 일치해야 합니다.

- back-face culling은 보이지 않는 내부 면 제거에 유용하지만 폐쇄 mesh라는 가정을 갖습니다.
- front-face culling은 shadow나 특수 pass에서 사용할 수 있으나 기본값이 아닙니다.
- culling을 껐을 때 문제가 사라진다면 winding·transform·asset contract를 조사해야지 영구 해결로 삼지 않습니다.

### blending

blending은 source shader output과 destination attachment value를 factor와 operation으로 합칩니다. 일반 straight-alpha over의 color factor는 `srcAlpha`, `oneMinusSrcAlpha`, premultiplied는 `one`, `oneMinusSrcAlpha`입니다.

attachment가 sRGB format이면 일반적으로 저장 전 encode와 blending을 위한 linear decode 동작을 API 규약에 따라 확인해야 합니다. software 정본은 linear attachment 값에서 blend한 뒤 최종 output에서 encode합니다.

alpha channel의 blend factor도 별도로 설정합니다. color 식만 맞고 alpha가 잘못되면 후속 compositing에서 오류가 나타납니다.

### draw order

opaque는 depth test가 최종 visibility를 결정하므로 결과 관점에서 순서 의존성이 작지만 성능에는 영향을 줍니다. front-to-back은 early depth rejection을 늘릴 수 있습니다.

transparent over 연산은 일반적으로 교환법칙을 만족하지 않으므로 back-to-front 정렬이 필요합니다. object center 거리만으로는 큰/교차 mesh를 정확히 정렬하지 못합니다. 이 한계를 문서화하고 테스트 scene을 둡니다.

### attachment load·clear·store

frame 시작 시 color/depth를 clear하지 않았거나 이전 frame 값을 load하면 ghosting처럼 보일 수 있습니다. render pass마다 다음을 기록합니다.

- load: clear, load, discard/don't-care
- clear value
- store: 보존 또는 폐기
- 다음 pass가 읽는지 여부

“화면을 매 frame 지운다”는 단순 설명보다 attachment의 이전 내용이 유효한지 계약으로 표현합니다.

## 검증 fixture

- 앞/뒤 두 opaque triangle의 draw order 교환
- 같은 depth에서 `less`와 `less-or-equal` 차이
- depth write off인 transparent layer 두 개
- transparent draw order 반전
- straight/premultiplied blend state 비교
- alpha mask의 threshold 경계
- negative scale mesh와 culling
- color/depth clear 누락
- far/near와 depth precision이 드러나는 가까운 surface

중간 artifact로 depth image, primitive id, blend 전 source/destination와 최종 color를 저장합니다.

## 흔한 오답

- depth test와 depth write를 하나의 on/off 상태로 취급
- transparent를 depth write on으로 그린 뒤 사라지는 면을 정렬 문제로만 판단
- straight texture와 premultiplied blend factor 혼용
- sRGB attachment 값을 linear color처럼 직접 합성
- winding 오류를 culling off로 숨김
- depth clear·compare와 projection convention 불일치
- 모든 transparency를 object center 정렬로 해결했다고 주장

## 연결 실습

- [`04-perspective-depth-blend`](../../exercises/04-perspective-depth-blend/README.md): depth·draw order·alpha mode에 따른 sample trace를 만듭니다.
- [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md): opaque·mask·transparent queue와 attachment 계약을 통합합니다.

## 완료 기준

- depth value의 공간·범위·clear·compare·write 계약을 한 표로 고정합니다.
- opaque, mask와 transparent 경로의 state와 draw order를 분리합니다.
- straight/premultiplied alpha에 맞는 blend 식을 linear color에서 검증합니다.
- depth·culling·blending·attachment load 오류를 각각 다른 artifact로 좁힙니다.
