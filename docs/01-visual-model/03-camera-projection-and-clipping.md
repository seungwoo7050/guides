# 카메라·투영·클리핑

## 목표

카메라의 pose를 view transform으로 바꾸고, perspective/orthographic projection이 view volume을 clip space로 옮기는 계약을 이해합니다. vertex가 화면 밖이라는 이유로 primitive 전체를 버리지 않고, homogeneous clip plane에 대해 올바르게 자른 뒤 perspective divide를 수행합니다.

## 시작하기 전에

[좌표 공간과 변환](02-coordinate-spaces-and-transforms.md)의 규약을 사용합니다. 과정은 left-handed view에서 camera가 `+Z`를 바라보고, NDC depth는 `[0, 1]`입니다.

### camera pose와 view matrix

camera의 world transform과 view matrix는 서로 반대 방향의 mapping입니다.

```text
camera world transform: camera local → world
view matrix:            world → camera/view
```

camera의 position·forward·up으로 orthonormal basis를 만들 때 다음을 검사합니다.

- forward 길이가 0이 아님
- up과 forward가 거의 평행하지 않음
- basis가 유한한 값이고 서로 수직임
- 축의 cross 순서가 handedness 규약과 일치함

invalid camera를 임의의 기본 방향으로 바꾸면 입력 오류가 숨습니다. scene validation에서 명시적으로 거부하거나 상태를 반환합니다.

### perspective projection

projection은 view-space frustum을 canonical clip volume으로 mapping합니다. field of view, aspect ratio, near, far는 다음 조건을 가져야 합니다.

```text
0 < vertical_fov < pi
aspect > 0
0 < near < far
```

near를 0으로 둘 수 없습니다. perspective divide와 깊이 정밀도 모두 문제가 됩니다. far/near 비율이 지나치게 크면 depth buffer의 구분 능력이 가까운 구간에 편중됩니다. 실제 renderer에서 reversed-Z를 선택할 수 있지만 이 가이드는 기본 `[0,1]` depth를 먼저 고정하고, 확장 시 비교 문서와 테스트를 추가합니다.

### clip space와 perspective divide

clipping은 `x/w`, `y/w`, `z/w`를 계산하기 전에 homogeneous coordinate에서 수행합니다. 과정 규약의 canonical volume은 다음 부등식을 사용합니다.

```text
-w <= x <= w
-w <= y <= w
 0 <= z <= w
```

vertex 하나가 밖에 있다고 triangle 전체를 버리면 화면 경계를 가로지르는 primitive가 사라집니다. 반대로 divide 뒤 screen 좌표에서 단순히 clamp하면 모양과 보간이 깨집니다.

### plane별 polygon clipping

삼각형을 각 clip plane에 순서대로 통과시키는 Sutherland–Hodgman 형태를 사용할 수 있습니다. edge의 두 endpoint가 plane 안/밖인지에 따라 다음을 수행합니다.

| 시작 | 끝 | 출력 |
|---|---|---|
| 안 | 안 | 끝 vertex |
| 안 | 밖 | 교차 vertex |
| 밖 | 안 | 교차 vertex, 끝 vertex |
| 밖 | 밖 | 없음 |

교차 parameter는 plane distance의 부호가 바뀌는 지점에서 구합니다. 새 vertex에는 position만 아니라 UV, color, normal 등 이후 보간에 필요한 vertex attribute도 같은 parameter로 보간합니다. 이 단계는 clip coordinate 기반의 선형 edge parameter를 사용합니다.

clipping 결과 polygon은 0개, 3개 이상 vertex를 가질 수 있습니다. fan triangulation을 사용할 때 winding과 attribute 순서를 보존합니다.

### `w`와 camera 뒤의 기하

`w <= 0`인 vertex를 개별적으로 바로 버리면 camera plane을 가로지르는 triangle을 잘못 처리할 수 있습니다. clip plane 평가와 clipping이 먼저입니다. 결과 vertex에서 `w`가 0에 너무 가까우면 divide가 불안정하므로 명시적 epsilon 정책과 거부 통계를 둡니다. epsilon은 장면 단위의 만능 해결책이 아니며 fixture와 수치 범위를 근거로 정합니다.

### viewport와 scissor

projection/frustum clipping과 viewport/scissor는 역할이 다릅니다.

- frustum clipping: primitive를 clip volume에 맞게 기하적으로 자름
- viewport transform: NDC를 framebuffer 좌표로 mapping
- scissor: 생성된 fragment를 정수 사각형 범위에서 거부

scissor는 near plane clipping을 대신하지 않습니다.

## 검증 fixture

- frustum 안의 triangle은 vertex 수와 winding 유지
- 한 plane을 가로지르는 triangle은 quadrilateral 뒤 두 triangle로 변환
- near plane과 side plane을 동시에 가로지르는 경우
- 완전히 밖인 triangle은 0개 출력
- 경계 plane 위 vertex는 일관되게 inside 취급
- invalid FOV/aspect/near/far 거부
- clipping 뒤 모든 vertex가 여섯 부등식을 만족
- perspective divide 뒤 NDC가 유한한 값

각 primitive에 원본 id와 clipping 뒤 child id를 부여하면 frame capture와 software/GPU 비교에서 추적하기 쉽습니다.

## 흔한 오답

- world-space plane과 clip-space 부등식 혼용
- NDC에서 clipping 후 attribute를 affine 보간
- 밖인 vertex가 하나라는 이유로 primitive 전체 제거
- screen 좌표 clamp로 clipping 대체
- `w`를 너무 일찍 나눔
- near/far와 NDC depth convention이 다른 projection matrix 복사

## 연결 실습

- [`01-transform-trace`](../../exercises/01-transform-trace/README.md): camera와 projection parameter, clip code와 교차 vertex를 기록합니다.
- [`03-triangle-coverage`](../../exercises/03-triangle-coverage/README.md): clipping 결과 triangle을 viewport와 coverage 단계로 넘깁니다.

## 완료 기준

- camera world transform과 view matrix의 방향을 구분합니다.
- projection parameter의 유효 조건과 depth 정밀도 영향을 설명합니다.
- homogeneous clip plane 여섯 개에 대해 triangle을 자르고 attribute를 보존합니다.
- clipping, viewport와 scissor의 서로 다른 책임을 artifact로 확인합니다.
