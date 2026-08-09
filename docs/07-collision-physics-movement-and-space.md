# 충돌, 물리, 이동과 좌표 계약

## 문제

게임에서 position 하나는 여러 시스템이 동시에 사용합니다. gameplay movement, physics body, animation root motion, navigation agent, camera interpolation, network prediction과 renderer가 각각 transform을 쓰거나 수정합니다. 누가 정본인지 정하지 않으면 jitter, tunneling, double movement, desync와 update-order bug가 발생합니다.

또한 collision과 physics는 같은 개념이 아닙니다.

- collision query: 특정 shape와 ray가 무엇과 겹치는지 질문
- contact generation: physics body 사이 접촉 후보 생성
- dynamics simulation: force, mass, constraint로 다음 state 계산
- character movement: gameplay 규칙에 맞춘 kinematic/controlled motion
- trigger/overlap: 물리 반응 없이 event 생성

## 핵심 상태

### 좌표 공간

| 공간 | 용도 | 대표 위험 |
|---|---|---|
| local | parent 기준 transform | parent scale/rotation |
| world | current world origin 기준 | large world precision |
| view/camera | camera 기준 | gameplay 정본으로 오인 |
| screen/UI | pixel 또는 normalized | DPI·safe area |
| physics | engine physics world | interpolation·substep |
| navigation | navmesh/graph 좌표 | stale rebuild |
| network | quantized/relative transform | precision·origin 차이 |

변환 함수와 unit을 명시합니다. meter, centimeter, tile과 pixel을 암묵적으로 섞지 않습니다.

### movement owner

대표 선택:

- dynamic physics body가 transform을 소유
- kinematic character controller가 transform을 소유
- gameplay simulation이 canonical state를 소유하고 physics를 query로 사용
- authoritative server가 canonical transform을 소유하고 client는 prediction view를 가짐

한 entity에서 여러 owner가 동시에 최종 transform을 write하지 않게 합니다.

### collision data

- simulation shape와 visual mesh를 분리합니다.
- layer/channel/mask의 의미를 data contract로 기록합니다.
- continuous collision 필요 대상을 정합니다.
- query-only, physics-only, trigger를 구분합니다.
- material/friction/restitution이 gameplay rule인지 presentation인지 정합니다.

### contact/event 수명

`enter`, `stay`, `exit` event는 object lifecycle, fixed step 수와 filtering에 영향을 받습니다. event 순서나 정확한 개수를 gameplay invariant로 사용할 때는 engine 보장을 확인해야 합니다.

## 설계 계약

### transform write authority를 표로 만듭니다

| phase | reader | writer | state |
|---|---|---|---|
| command | input/router | command buffer | desired move |
| simulation | movement system | canonical pose/velocity | fixed tick state |
| physics | physics world | contacts/correction | simulation result |
| animation | presentation | visual root/bones | render state |
| render | renderer | none | interpolated snapshot |

animation root motion을 gameplay movement로 사용할 경우 animation marker와 fixed simulation 사이 변환 정책을 명시합니다.

### query와 mutation을 분리합니다

- query 결과에는 tick/world/filter version을 포함합니다.
- query 뒤 object가 사라질 수 있으므로 stable handle을 검증합니다.
- query callback 안에서 physics collection을 바로 변경하지 않고 command/deferred queue를 사용할 수 있습니다.

### fixed step과 substep을 구분합니다

physics engine이 한 gameplay fixed tick을 여러 internal substep으로 나눌 수 있습니다. gameplay timer와 command를 substep마다 중복 소비하지 않습니다. substep callback에서 허용하는 side effect를 제한합니다.

### collision filtering을 중앙 contract로 관리합니다

layer 숫자를 코드 곳곳에 직접 쓰지 않습니다.

```text
PlayerBody collides with WorldStatic, DynamicObstacle
PlayerHitQuery queries Damageable, Shield
PickupTrigger overlaps PlayerBody
CameraProbe queries WorldStatic, CameraBlocker
```

변경 시 기존 content와 test scene을 자동 검증합니다.

### correction policy를 둡니다

- 작은 penetration: depenetration 또는 snap
- 큰 invalid pose: safe checkpoint/respawn
- network correction: prediction history rewind/replay 또는 smoothing
- moving platform: parent/local motion과 world transform 합성

correction이 gameplay event를 중복 발생시키지 않게 합니다.

## 대표 실패

### frame update와 fixed update가 모두 transform을 씁니다

animation 또는 camera code가 canonical transform을 수정해 physics 결과를 덮습니다.

### visual mesh를 collision 정본으로 사용합니다

LOD와 asset 변경이 gameplay collision을 바꿉니다. simplified authored collision과 validation을 둡니다.

### overlap event 개수를 점수로 사용합니다

step 수, disable/enable과 streaming에 따라 중복·누락될 수 있습니다. unique entity state와 explicit rule transition을 사용합니다.

### raycast hit를 오래 보관합니다

다음 tick에 object가 파괴되거나 pool reuse될 수 있습니다. generation handle과 tick을 검증합니다.

### teleport가 velocity·contacts·network history를 정리하지 않습니다

이전 motion이 새 위치에 적용되거나 correction이 원래 위치로 되돌립니다. teleport를 특별한 state transition으로 처리합니다.

### 낮은 frame rate에서 무한 physics catch-up이 발생합니다

fixed step 정책과 maximum allowed catch-up을 함께 설계합니다.

## 관찰과 검증

### movement trace

```json
{
  "tick": 903,
  "entity": "player-1#7",
  "command": [0.8, 0.0],
  "pose_before": [12.0, 0.0, 4.0],
  "desired_delta": [0.08, 0.0, 0.0],
  "contacts": ["wall-3"],
  "pose_after": [12.03, 0.0, 4.0],
  "correction": "slide"
}
```

### 검사 시나리오

- 동일 command trace를 서로 다른 render FPS에서 실행합니다.
- 얇은 wall과 high velocity에서 tunneling 정책을 확인합니다.
- moving platform enter/exit와 world unload를 반복합니다.
- crouch/stand shape 변경 시 invalid space를 거부합니다.
- teleport 뒤 velocity, contacts, camera와 prediction history를 확인합니다.
- collision layer 변경이 기존 content validator에 잡힙니다.
- server correction 뒤 damage/trigger event가 중복되지 않습니다.

### debug visualization

- simulation vs render pose
- collision shapes와 layer
- contact normal과 penetration
- navmesh와 agent corridor
- prediction/correction history

visual debug는 증거를 돕지만 자동 test를 대체하지 않습니다.

## 실습 연결

Capstone에서 `movement-and-space.md`에 transform owner, fixed phase, collision matrix와 correction policy를 작성합니다. [authority 실습](../exercises/06-authority-and-latency/README.md)에서는 predicted pose와 authoritative correction을 분석합니다.

## 기존 브랜치와 경계

- 벡터·행렬·좌표 변환의 수학은 `computer-graphics`가 소유합니다.
- fixed time과 frame policy는 이 브랜치의 02장이 소유합니다.
- network transport와 loss는 `computer-networks`가 소유합니다.
- 현재 문서는 gameplay transform ownership, collision filtering, movement·physics·presentation 통합을 소유합니다.

## 완료 기준

- 좌표 공간과 unit을 명시하고 transform writer를 하나로 정합니다.
- collision query, trigger, dynamic physics와 character movement를 구분합니다.
- fixed tick·physics substep·render interpolation을 연결합니다.
- teleport, moving platform, tunneling과 network correction을 재현 가능한 시나리오로 검증합니다.
