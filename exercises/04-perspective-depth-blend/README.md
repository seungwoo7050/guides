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

## 준비·workspace·stage 검사

[공통 workspace 절차](../README.md#workspace-준비와-공개-명령) 뒤 같은 누적 renderer에서 진행합니다.

```sh
cmake -S exercises/08-renderer-capstone/project -B build/workspace -DCG_IMPLEMENTATION=workspace -DCG_GPU=off
cmake --build build/workspace
python3 exercises/check.py --impl workspace --stage 04-perspective-depth-blend --expect pass --gpu off
python3 exercises/check.py --impl reference --stage 04-perspective-depth-blend --expect pass --gpu off
```

checker는 perspective/affine 차이, opaque draw-order metamorphic test, depth 범위, flat id, linear blend와 alpha state를 reference trace·image와 비교합니다. starter와 최소 네 known-bad mutation은 거부돼야 합니다.

사람 검토에서는 `1/w` numerator·denominator 중 첫 차이를 지목하고, opaque와 transparent draw order가 다른 이유, exact attachment와 float tolerance를 나눈 근거를 artifact로 설명합니다.

`make clean`은 build와 output만 정리합니다. 실패 pixel trace와 diff는 보존하고 tolerance를 넓히기 전에 coverage→depth→attribute→color 순서로 복구합니다. workspace는 지우지 않습니다.
