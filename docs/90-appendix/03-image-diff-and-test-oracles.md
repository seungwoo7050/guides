# 이미지 차이와 테스트 oracle

## 목적

렌더링 테스트가 “눈으로 비슷하다”와 “모든 pixel이 정확히 같다” 사이에서 의미 있는 판정을 하도록 설계합니다. 어떤 attachment가 정확 비교 대상인지, 허용 오차와 mask를 어디에 적용하는지, reference image를 어떻게 변경하는지 정합니다.

## oracle의 계층

최종 color image 하나로 모든 오류를 판정하지 않습니다.

```text
구조 oracle
- draw/primitive/vertex count
- asset·pipeline·resource manifest

정확 oracle
- object/primitive id
- coverage bitmask
- 정수 index와 rejection reason

수치 oracle
- transform trace
- depth
- UV/normal/linear color

표시 oracle
- final sRGB image
- 사람이 보는 screenshot
```

앞 단계가 다르면 뒤 image tolerance를 넓혀 통과시키지 않습니다.

## exact comparison

다음은 고정 CPU 정본에서 byte-identical을 목표로 합니다.

- 작은 PPM marker
- primitive id image
- integer coverage map
- JSON key/value 중 정수·문자열·hash
- 정렬된 rejection list

float를 text로 저장한다면 formatting precision과 `-0`, NaN/inf 정책을 고정합니다.

## numeric comparison

float attachment에는 다음 지표를 함께 사용합니다.

- channel별 max absolute error
- mean absolute error
- relative error가 의미 있는 값의 경우 max/mean relative error
- threshold를 넘은 pixel 수와 비율
- bounding box와 top-N worst pixel
- NaN/inf mismatch 수

한 지표만 사용하면 작은 영역의 큰 오류나 전체 영역의 작은 bias를 놓칠 수 있습니다.

## image encoding

PPM 8-bit final image는 이미 quantization과 sRGB encode가 적용된 결과일 수 있습니다. lighting 원인을 검사하려면 linear float attachment를 별도 format으로 저장하거나 선택 pixel trace를 사용합니다.

이 저장소의 `ppm_diff.py`는 P3/P6 8-bit PPM의 단순 회귀를 위한 도구입니다. 다음을 대신하지 않습니다.

- HDR/float image 비교
- perceptual metric
- color profile 처리
- GPU driver별 허용 범위 결정
- coverage/depth 원인 분석

## threshold 설계

threshold는 실패한 뒤 숫자를 늘려 정하지 않습니다.

1. 같은 구현의 반복 실행 분산을 측정합니다.
2. 지원 환경과 format의 expected numeric 차이를 설명합니다.
3. 알려진 올바른 변경과 알려진 오답 mutation을 모두 실행합니다.
4. 오답은 거부하면서 expected 차이만 허용하는 범위를 선택합니다.
5. threshold와 근거를 versioned contract에 기록합니다.

`max_abs <= 2/255`처럼 단일 규칙이 모든 image에 적합하지 않습니다. attachment와 fixture별로 둡니다.

## mask

mask는 다음처럼 의미가 있을 때만 사용합니다.

- backend raster rule 차이를 의도적으로 허용한 경계 sample
- 시간에 따라 달라지는 UI/debug overlay를 비교 대상에서 제외
- undefined/unsupported 영역을 명시적으로 제외

전체 silhouette 경계를 두껍게 mask하면 coverage bug를 숨깁니다. mask image 자체를 version control하고 왜 제외하는지 문서화합니다.

## reference 갱신

reference image 변경은 테스트 삭제와 같은 위험을 가집니다. PR 또는 변경 기록에 다음을 포함합니다.

- 계약 변경 이유
- 이전/새 image와 diff
- 첫 달라진 pipeline 단계
- threshold/mask 변경 여부
- known-bad mutation이 여전히 실패하는 결과
- source scene·shader·environment hash

“새 결과가 현재 화면과 같아서”는 근거가 아닙니다.

## software와 GPU

비교 순서:

1. scene/camera/settings hash
2. transform·clipping 통계
3. primitive/coverage id
4. depth
5. UV/normal/material debug
6. linear color
7. final encoded color

GPU의 작은 float 차이를 허용하더라도 primitive id와 큰 coverage 차이는 별도 failure로 처리합니다.

## metamorphic test

정답 image가 없어도 관계를 검증할 수 있습니다.

- identity transform은 결과를 유지
- draw order 교환이 opaque depth 결과를 유지
- 두 triangle로 나눈 rectangle의 shared edge에 틈/중복 없음
- light intensity 0에서 lighting contribution 0
- texture UV를 정수만큼 이동하고 repeat sampler면 결과 유지
- viewport 크기와 projection aspect를 함께 조정한 invariant
- object id 변경은 color/depth가 아니라 id attachment만 변경

이 검사는 새로운 scene에서 reference 남발을 줄입니다.

## 알려진 오답 mutation

- matrix order 교환
- clipping 생략
- top-left equality 제거
- perspective UV를 affine으로 변경
- sRGB decode 생략
- depth compare 반전
- straight/premultiplied blend mismatch
- uniform slot overwrite

검사기는 최소한 이 오답을 거부해야 합니다.

## 완료 검토표

- 최종 image 전에 구조·coverage·depth oracle이 있는가?
- tolerance 단위와 color encoding이 명확한가?
- NaN/inf를 숫자 차이로 숨기지 않는가?
- mask가 versioned이고 제외 이유가 있는가?
- reference 변경이 mutation test를 유지하는가?
- 환경·shader·scene hash가 결과에 연결되는가?
