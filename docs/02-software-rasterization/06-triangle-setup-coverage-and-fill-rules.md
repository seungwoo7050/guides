# 삼각형 setup·coverage·fill rule

## 목표

viewport 좌표의 삼각형이 어떤 pixel sample을 소유하는지 edge function과 일관된 fill rule로 결정합니다. shared edge에서 틈이나 이중 rasterization이 생기지 않게 하고, winding·back-face·degenerate triangle·bounding box의 역할을 분리해 검증합니다.

## 시작하기 전에

[카메라·투영·클리핑](../01-visual-model/03-camera-projection-and-clipping.md)을 통과한 vertex만 입력으로 받습니다. perspective divide와 viewport transform은 완료됐지만, 원근 보정에 필요한 clip `w`와 vertex attribute는 보존돼 있어야 합니다.

### triangle setup의 출력

rasterizer의 setup 단계는 매 sample마다 같은 값을 다시 계산하지 않도록 primitive 상태를 만듭니다.

```text
TriangleSetup
├── screen vertex 3개
├── signed area와 winding
├── edge equation 3개
├── top-left 포함 여부
├── 정수 또는 보수적 bounding box
├── attribute plane 준비값
└── primitive id와 거부 이유
```

setup이 거부한 primitive도 통계에 이유를 남깁니다.

- clipping 결과 없음
- non-finite coordinate
- 면적 0 또는 threshold 이하
- culling state에 의해 제거
- framebuffer/scissor와 bounding box가 겹치지 않음

### edge function

screen point `p`가 directed edge `a → b`의 어느 쪽에 있는지 2D signed area로 계산합니다.

```text
E(a, b, p) = (p.x - a.x)(b.y - a.y) - (p.y - a.y)(b.x - a.x)
```

부호는 coordinate convention과 winding에 따라 달라집니다. 과정에서는 viewport `+Y down`, 앞면 CCW라는 최종 규약을 테스트 fixture로 고정하고, 구현은 한 번 정한 부호를 모든 edge에 일관되게 사용합니다.

세 edge가 내부 조건을 만족하면 sample이 triangle에 포함됩니다. signed area의 절대값은 barycentric denominator로도 사용합니다.

### top-left rule

두 triangle이 edge를 공유할 때 경계 sample을 둘 다 포함하거나 둘 다 제외하면 중복 또는 틈이 생깁니다. top-left rule은 일부 directed edge만 경계 equality를 포함해 공유 edge를 정확히 한 primitive가 소유하도록 합니다.

과정의 viewport 규약에서 top-left 판정은 구현 식과 fixture를 함께 정본으로 둡니다. 부호 식을 외워 복사하기보다 다음 불변식을 검사합니다.

1. 두 triangle이 rectangle을 이루면 모든 내부 sample이 정확히 한 번 포함됩니다.
2. vertex 순서를 바꿔 front-face로 정규화한 뒤 결과가 같습니다.
3. shared horizontal/vertical/diagonal edge에서 중복과 빈 sample이 없습니다.
4. framebuffer 경계에서 out-of-range write가 없습니다.

float equality만으로 경계를 판정하면 작은 수치 차이가 생길 수 있습니다. 교육용 정본은 subpixel fixed-point 좌표 또는 명시적 epsilon 없는 정수 edge evaluation을 선택할 수 있습니다. 어떤 방식이든 quantization 규칙을 artifact에 기록합니다.

### bounding box

triangle의 axis-aligned bounding box를 sample center 규약에 맞게 정수 pixel 범위로 변환합니다. 단순히 vertex min/max를 `int` cast하면 음수와 반올림에서 범위가 틀릴 수 있습니다.

- lower bound는 포함 가능한 첫 sample index
- upper bound는 포함 가능한 마지막 sample index
- framebuffer와 scissor 범위로 clamp
- 빈 범위는 primitive 거부

bounding box는 coverage를 판정하지 않습니다. 검사할 후보를 줄일 뿐입니다.

### winding과 culling

signed area로 winding을 판정합니다. back-face culling은 triangle이 화면에 보일지의 완전한 판정이 아니라 설정된 front-face 규약에 따른 primitive 제거입니다.

- negative scale은 winding을 뒤집을 수 있습니다.
- viewport Y mapping도 winding의 부호에 영향을 줍니다.
- double-sided material은 culling을 끌 수 있습니다.
- clipping 뒤 생성된 triangle은 원래 winding을 보존해야 합니다.

culling 결과와 degenerate 결과를 같은 카운터에 넣지 않습니다.

### degenerate triangle

세 vertex가 같은 선 위에 있거나 quantization 뒤 면적이 0이면 rasterization하지 않습니다. 작은 면적을 임의 epsilon으로 제거하면 zoom과 resolution에 따라 결과가 바뀔 수 있습니다. fixed-point setup을 사용한다면 quantized area 0을 기준으로 삼고, float 구현에서는 입력 범위와 시험 사례에 맞춘 명시적 정책을 둡니다.

## 검증 fixture

- 하나의 axis-aligned right triangle
- 두 triangle이 이루는 rectangle
- horizontal, vertical, diagonal shared edge
- vertex가 pixel center와 정확히 겹치는 경우
- clockwise/counter-clockwise 순서
- negative framebuffer coordinate와 부분 visible triangle
- 면적 0, 거의 0, 매우 큰 좌표
- clipping 뒤 생성된 polygon fan
- scissor가 triangle 일부만 자르는 경우

`coverage.ppm` 외에 sample별 primitive id image를 저장하면 겹침과 틈을 직접 확인할 수 있습니다.

## 흔한 오답

- 세 edge 모두 `>= 0`으로 처리해 shared edge 중복
- 모든 경계에 `> 0`을 사용해 틈 생성
- float epsilon을 장면 크기와 무관하게 사용
- bounding box 반올림이 pixel center 규약과 다름
- viewport Y flip 뒤 front-face 설정을 갱신하지 않음
- degenerate triangle에서 0으로 나눠 barycentric NaN 생성

## 연결 실습

- [`03-triangle-coverage`](../../exercises/03-triangle-coverage/README.md): shared edge와 top-left rule을 primitive-id artifact로 검증합니다.
- [`04-perspective-depth-blend`](../../exercises/04-perspective-depth-blend/README.md): coverage sample에 barycentric·depth·color 계산을 연결합니다.

## 완료 기준

- edge function, signed area와 barycentric denominator의 관계를 설명합니다.
- top-left rule로 shared edge를 정확히 한 triangle이 소유하게 합니다.
- bounding box·coverage·culling·degenerate 거부를 서로 다른 단계와 통계로 유지합니다.
- fixed-point 또는 float setup의 quantization·경계 정책을 fixture와 함께 기록합니다.
