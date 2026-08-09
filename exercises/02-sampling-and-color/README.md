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

## 준비·workspace·stage 검사

[공통 workspace 절차](../README.md#workspace-준비와-공개-명령)로 만든 learner 사본에서 진행합니다. 기존 workspace가 있으면 `new-workspace.sh`를 다시 실행하지 않습니다.

```sh
cmake -S exercises/08-renderer-capstone/project \
  -B build/workspace \
  -DCG_IMPLEMENTATION=workspace \
  -DCG_GPU=off
cmake --build build/workspace
python3 exercises/check.py --impl workspace --stage 02-sampling-and-color --expect pass --gpu off
python3 exercises/check.py --impl reference --stage 02-sampling-and-color --expect pass --gpu off
```

checker는 sample trace, address 결과, linear-space bilinear·mip, alpha 결과와 PPM diff를 reference와 비교합니다. UV 1 경계, 음수 repeat, odd extent와 alpha 0의 유색 RGB를 포함하며 starter와 최소 세 known-bad mutation이 거부돼야 합니다.

사람 검토에서는 다음에 답합니다.

- black/white 중간값을 encoded byte와 linear RGB에서 계산하면 왜 다릅니까?
- color texture와 data texture가 같은 bytes여도 처리 경계가 달라지는 이유는 무엇입니까?
- straight와 premultiplied alpha가 같은 의도 결과를 만들려면 어느 저장·blend 상태가 짝을 이뤄야 합니까?

`make clean`은 생성물만 지우고 workspace는 남깁니다. 실패한 diff·worst-pixel trace를 보존한 채 첫 다른 sample 단계부터 복구하며 reference image를 실제 결과로 덮어쓰지 않습니다.
