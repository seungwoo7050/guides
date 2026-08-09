# 실습 04 — perspective·depth·blend

## 목적

coverage sample에 perspective-correct attribute, depth test/write와 alpha blending을 연결합니다. 한 pixel의 barycentric·`1/w`·UV·depth·source/destination color를 단계별로 기록해 affine interpolation, depth convention과 alpha state 오답을 거부합니다.

관련 문서:

- [보간·원근 보정](../../docs/02-software-rasterization/07-interpolation-perspective-and-derivatives.md)
- [깊이·culling·blending](../../docs/02-software-rasterization/08-depth-culling-blending-and-transparency.md)

## 입력 fixture

- 원근이 강한 checker quad(두 triangle)
- 앞/뒤 opaque triangle
- 같은 depth의 coplanar case
- straight alpha layer 두 개
- premultiplied alpha layer 두 개
- alpha mask threshold case

## 구현할 경계

- barycentric weight
- flat/affine/perspective attribute mode
- NDC depth `[0,1]`
- depth clear 1, compare less, write on/off
- linear color blending
- straight/premultiplied state
- final sRGB encode

## 필수 artifact

```text
out/perspective-depth-blend/
├── perspective-correct.ppm
├── affine-mutation.ppm
├── depth.ppm 또는 depth.json
├── primitive-id.ppm
├── transparent-order-a.ppm
├── transparent-order-b.ppm
├── pixel-traces/*.json
└── report.json
```

선택 pixel trace는 `lambda`, `vertex w`, `1/w`, denominator, UV, sampled linear color, incoming/stored depth, test result, blend operands와 output을 포함합니다.

## 불변식

- quad의 두 triangle 경계에서 UV가 연속입니다.
- opaque draw order를 바꿔도 depth 결과가 같습니다.
- transparent order를 바꾸면 일반 over 결과가 다름을 관찰합니다.
- straight와 premultiplied fixture는 올바른 state에서 의도한 같은 결과를 만듭니다.
- depth는 유효 fragment에서 `[0,1]`이고 non-finite가 없습니다.
- flat primitive id는 보간되지 않습니다.

## 알려진 오답

- UV affine interpolation
- view-space z를 depth buffer 값으로 사용
- depth compare 반전 또는 clear 0
- transparent depth write on
- sRGB 값에서 blending
- alpha representation과 blend factor 불일치

## 완료 근거

- 올바른/affine image diff와 worst pixel trace
- depth draw-order metamorphic test
- transparent order와 alpha 표현 보고서
- known-bad mutation 최소 네 개 거부
- float tolerance와 exact attachment의 구분
