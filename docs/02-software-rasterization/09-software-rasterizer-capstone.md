# 소프트웨어 래스터라이저 capstone

## 목표

문서 01–08의 계약을 하나의 결정적 CPU renderer로 연결합니다. 완성된 engine을 만드는 대신 고정 scene에서 transform·clipping·coverage·보간·depth·texture·color·blend의 첫 차이를 찾을 수 있는 reference artifact와 검사 구조를 설계합니다.

## 시작하기 전에

[`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md)의 누적 project에는 공개 계약을 설명하는 작은 결정적 `reference`가 있습니다. checker가 그 source를 learner `workspace`로 복사하지 않으며, reference는 임의 scene을 처리하는 완제품 renderer나 제출용 정답이 아닙니다. 학습자는 starter의 미완성 경계를 직접 구현해 CPU 정본을 완성하고, GPU 단계에서 같은 scene id와 artifact 의미를 재사용합니다.

실행 전 [안전 및 운영 계약](../../SAFETY.md)을 읽고 생성물은 `build/`, `out/` 또는 새 임시 디렉터리에 둡니다. 실패 trace와 learner workspace를 정리 명령으로 덮어쓰거나 삭제하지 않습니다.

### 최소 기능 범위

필수:

- indexed triangle mesh
- model/view/projection transform
- homogeneous frustum clipping
- viewport와 scissor
- top-left fill rule
- flat·affine·perspective attribute
- depth test/write
- nearest와 bilinear texture sample
- linear/sRGB 경계
- opaque와 alpha blend
- PPM color output
- depth·primitive id·통계·pixel trace

선택:

- mipmap과 trilinear
- vertex normal과 단순 Lambert 조명
- back-face culling
- wireframe 또는 debug overlay
- tile 기반 work 분할

필수 기능을 검증하기 전에 멀티스레딩, SIMD, scene graph framework와 범용 material system을 추가하지 않습니다.

## 권장 구조

```text
src/
├── math/             과정 규약을 구현하는 최소 vector·matrix
├── image/            format·linear/sRGB·PPM
├── scene/            검증된 mesh·material·camera snapshot
├── pipeline/
│   ├── transform
│   ├── clipping
│   ├── setup
│   ├── raster
│   ├── shading
│   └── output
├── trace/            JSON과 통계 artifact
└── app/              fixture 선택과 CLI
```

각 단계는 거대한 `draw_triangle` 함수가 아니라 입력·출력 계약을 갖습니다. 그러나 class 계층을 만들기 위해 단계를 쪼개지는 않습니다. 테스트에서 독립적으로 관찰해야 하는 상태 전이가 경계입니다.

### frame 입력

고정 JSON 또는 C++ fixture로 다음 scene을 제공합니다.

1. RGB vertex triangle
2. clip plane을 가로지르는 triangle
3. shared edge rectangle
4. perspective checker quad
5. 앞/뒤 opaque triangle
6. 두 transparent layer
7. invalid mesh/index/texture fixture

asset parser 자체가 학습을 방해하면 fixture는 코드로 정의해도 됩니다. 입력 순서와 random seed를 고정합니다.

### artifact 계약

실행 한 번에 다음을 생성합니다.

```text
out/<case>/
├── color.ppm
├── depth.pgm 또는 depth.json
├── primitive-id.ppm
├── frame.json
├── rejected-primitives.json
└── traces/
    ├── vertex-<id>.json
    └── pixel-x-y.json
```

`frame.json`에는 최소한 다음이 있습니다.

- 규약 version
- extent와 sample 위치
- scene/camera/settings hash
- input/output primitive 수
- clipped/culled/degenerate 수
- covered/depth-passed/shaded sample 수
- invalid·NaN·out-of-range 수
- output file hash

pixel trace는 선택한 소수의 pixel만 생성합니다. 모든 fragment를 JSON으로 남기면 상태보다 I/O가 커집니다.

위 트리는 학습자 capstone의 제출 역할을 설명합니다. 번들 reference는 같은 역할을 stage별 파일명으로 나눕니다. `01`의 transform/rejection JSON, `02`의 sample·mip·alpha PPM/JSON, `03`의 coverage·primitive-id, `04`의 perspective·depth·blend, `05`의 asset·lighting·LOD·debug attachment를 공개 checker가 독립 값과 고정 artifact에 대조합니다. 파일명이 예시 트리와 다르다는 이유로 의미 증거를 생략하지 않습니다.

번들 CPU reference의 자동 범위도 구체적으로 제한합니다. `01`은 identity가 아닌 left-handed look-at camera와 유효 basis를 계산하고, attribute를 보존한 채 left/right/top/bottom/near/far 여섯 homogeneous plane을 clip합니다. `04`의 depth는 perspective attribute와 달리 화면 barycentric으로 affine한 NDC z를 검사합니다. `05`는 공통 `SceneSnapshot`의 vertex color·normal·UV, marker texture, inverse-transpose normal과 단순 linear lighting을 실제 attachment까지 연결하고, culling/LOD 선택이 visible count뿐 아니라 vertex/sample work count를 바꾸는지도 검사합니다. 각 선언 mutation은 false invariant만 미리 뒤집는 대신 첫 차이 artifact를 남겨 checker가 재계산합니다.

이 자동 reference는 cube 전체, mirrored UV island의 TBN handedness나 glTF 같은 범용 loader를 구현하지 않습니다. 그것들은 아래 단계와 실습 05에서 학습자가 추가하고, seam·normal 공간·import validation 근거를 사람이 확인할 범위입니다.

## 자동 근거와 사람 검토

| 근거 | 자동으로 판정하는 범위 | 사람이 확인할 범위 |
|---|---|---|
| 정상·경계 fixture | 고정 scene의 수치, sample 소유권, depth/color 값과 추적 PPM | 단계 경계와 자료구조가 새 입력에도 설명 가능한지 |
| known-bad mutation | 선언한 오답이 exit 4와 false invariant로 거부되는지 | 오답이 실제로 어느 계산을 바꿨고 첫 차이가 왜 그 artifact인지 |
| 성능 artifact | sample 수·hash·측정 형식 같은 재현 계약 | 최적화 선택, 환경 잡음과 정확성·복잡도 trade-off |
| asset/provenance | 저장소 fixture의 id와 결정적 결과 | 외부 asset을 추가한 경우 source·hash·license·import 변환 |

자동 검사는 고정 fixture에 대한 회귀 oracle입니다. 화면의 미적 품질, 모든 부동소수점 플랫폼, 설명의 충분성이나 일반 renderer 설계를 자동으로 증명하지 않습니다.

## 단계별 완료 순서

### 단계 1. output과 marker

framebuffer clear, pixel write, PPM 저장과 corner/channel marker를 검증합니다. 아직 triangle을 그리지 않습니다.

### 단계 2. transform trace

vertex를 local에서 viewport까지 옮기고 단계별 값을 출력합니다. invalid camera와 `w` 처리도 포함합니다.

### 단계 3. clipping과 coverage

clip plane을 가로지르는 triangle과 shared edge rectangle을 통과시킵니다. primitive-id image에 빈 sample·중복 sample이 없어야 합니다.

### 단계 4. interpolation과 depth

perspective checker와 앞/뒤 triangle을 사용합니다. affine UV mutation과 depth compare mutation을 검사기가 거부해야 합니다.

### 단계 5. color·texture·blend

sRGB texture를 linear로 sample하고 straight/premultiplied alpha fixture를 비교합니다. final encode 이전 linear 값도 trace합니다.

### 단계 6. 통합과 오답 주입

알려진 잘못된 구현을 한 번씩 주입합니다.

- matrix order 교환
- clipping 생략
- 모든 edge `>=`
- affine UV
- sRGB byte 평균
- depth write 비활성 또는 compare 반전
- alpha blend factor 불일치

각 mutation이 어떤 fixture와 artifact에서 처음 거부되는지 표로 남깁니다.

## 성능의 위치

소프트웨어 renderer는 정확성 정본입니다. 최소 기능이 완료된 뒤 다음 정도만 측정합니다.

- frame 전체 시간
- setup/raster/shading/output 단계 시간
- tested sample 대비 covered sample 비율
- triangle 수와 pixel 수에 따른 증가

측정 전후 이미지 hash와 artifact 계약이 같아야 합니다. tile, SIMD, thread를 도입한다면 결정적 결과와 race 검사를 먼저 유지합니다. 실제 GPU보다 빠르거나 실시간이어야 할 이유는 없습니다.

## 실패 판정

다음은 완료가 아닙니다.

- 예제 screenshot이 비슷해 보임
- 한 해상도와 한 triangle에서만 통과
- NaN을 0으로 clamp해 숨김
- 경계 pixel을 넓은 image tolerance로 무시
- 모든 GPU 차이를 부동소수점 차이라고 처리
- reference image를 갱신해 실패를 없앰

정본 image를 변경할 때는 어떤 계약이 바뀌었는지, 이전 결과가 왜 틀렸는지와 mutation test를 함께 수정합니다.

## 연결 실습

- [`03-triangle-coverage`](../../exercises/03-triangle-coverage/README.md)
- [`04-perspective-depth-blend`](../../exercises/04-perspective-depth-blend/README.md)
- [`05-textured-lit-scene`](../../exercises/05-textured-lit-scene/README.md)
- [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md)

## 완료 기준

- 최소 일곱 fixture를 고정 입력으로 재현합니다.
- 최종 color 외에 depth·primitive id·통계·선택 pixel trace를 생성합니다.
- 알려진 오답 mutation이 정확한 단계의 검사에서 실패합니다.
- 최적화 전후 결과 계약을 보존하고 시간 측정의 환경과 범위를 기록합니다.
- GPU renderer가 같은 scene과 비교 정책을 사용할 수 있는 CPU 정본을 제공합니다.
- 자동 검사 결과와 별도로 첫 차이·tolerance·비범위·외부 asset 출처를 사람이 검토할 수 있게 기록합니다.
