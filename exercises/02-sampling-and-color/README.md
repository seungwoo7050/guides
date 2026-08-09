# 실습 02 — sampling과 color

## 목적

작은 marker texture에서 texel center·address mode·nearest/bilinear·sRGB decode/encode·alpha 표현의 기준 결과를 만듭니다. texture가 보인다는 사실보다 어떤 texel과 weight가 linear output을 소유하는지 검증합니다.

관련 문서:

- [이미지·색 공간·alpha](../../docs/01-visual-model/04-images-color-and-alpha.md)
- [샘플링·filtering·aliasing](../../docs/01-visual-model/05-sampling-filtering-and-aliasing.md)
- [이미지 diff와 oracle](../../docs/90-appendix/03-image-diff-and-test-oracles.md)

## 입력 fixture

- 2×2 RGBA corner marker
- 4×4 black/white checker
- transparent edge color fixture
- normal/data texture marker
- odd extent image(3×5)

외부 image loader 없이 코드 배열 또는 PPM로 시작합니다. 각 texel의 logical RGBA와 encoding을 문서화합니다.

## 구현할 경계

- normalized UV→continuous texel coordinate
- nearest tie-breaking
- bilinear weight와 2×2 texel 선택
- clamp/repeat/mirrored repeat
- sRGB piecewise decode/encode
- straight↔premultiplied 변환과 over blending
- linear-space box-filter mip chain

## 필수 artifact

```text
out/sampling-color/
├── samples.json
├── address-grid.ppm
├── bilinear-linear.ppm
├── bilinear-wrong-srgb.ppm
├── alpha-straight.ppm
├── alpha-premultiplied.ppm
├── mip-level-0.ppm ...
└── report.json
```

`samples.json`은 UV, 선택 texel index, weights, decoded linear values와 최종 encode를 포함합니다.

## 핵심 case

- UV `(0,0)`, `(1,1)`, 각 texel center와 edge midpoint
- 음수와 1 초과 UV
- black/white의 50% bilinear 결과
- alpha 0 texel에 유색 RGB가 있는 edge
- color texture와 data texture의 동일 byte 입력
- odd extent에서 마지막 1×1 mip까지

## 알려진 오답

- `int(u*width)`로 UV 1 out-of-range
- 음수 repeat를 언어 `%`만으로 처리
- sRGB byte를 직접 평균
- premultiplied texture에 straight blend factor
- normal map을 sRGB decode
- odd extent의 마지막 row/column 누락

## 완료 근거

- sample trace와 PPM artifact
- `tools/ppm_diff.py`를 사용한 expected/actual report
- linear와 잘못된 sRGB 평균의 수치 차이 설명
- straight/premultiplied가 같은 의도 결과를 만드는 case
- known-bad mutation 최소 세 개 거부
