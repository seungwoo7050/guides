# visibility·공간 구조·LOD

## 목표

최종 결과에 기여하지 않는 object·primitive·detail work를 줄이되, culling과 LOD가 visible geometry를 잘못 제거하지 않는다는 보수적 계약을 유지합니다. frustum culling, spatial structure, occlusion과 LOD를 서로 다른 단계와 측정값으로 구분합니다.

## 시작하기 전에

이 문서는 고급 rendering engine scene management 전체를 다루지 않습니다. 먼저 [asset과 bounds](12-meshes-scenes-and-asset-contracts.md)의 유효한 world bound와 [camera frustum](../01-visual-model/03-camera-projection-and-clipping.md)을 사용합니다.

### visibility 단계

```text
scene instance
→ layer/mask 거부
→ frustum culling
→ distance/LOD 선택
→ 선택적 occlusion culling
→ primitive culling
→ depth test
```

앞 단계일수록 CPU에서 큰 work 단위를 제거하고, 뒤 단계일수록 GPU와 pixel 단위에 가깝습니다. 각 단계의 input/output count를 따로 측정합니다.

### frustum culling

object의 world AABB 또는 bounding sphere를 camera frustum plane과 비교합니다. 결과는 세 가지로 분리할 수 있습니다.

- outside: 안전하게 제거
- intersecting: render 후보로 유지
- inside: 모든 plane 안

culling bounds는 geometry를 포함하는 보수적 근사여야 합니다. 너무 크면 성능만 나빠지지만 너무 작으면 visible geometry가 사라집니다. 이 비대칭을 검사에 반영합니다.

near plane과 camera 내부의 큰 object, negative scale, animation으로 변하는 bounds를 fixture에 포함합니다.

### 공간 구조

모든 object를 매 frame 순회하는 비용이 문제가 될 때 BVH, grid, octree 같은 구조를 사용할 수 있습니다. 자료구조 이름보다 update와 query 계약을 먼저 정합니다.

- static/dynamic object 분리 여부
- insertion/removal/update 비용
- object가 여러 cell/node에 중복될 수 있는지
- query 중 scene update 허용 여부
- stale bounds를 어떻게 검출하는지
- traversal order가 결과에 영향을 주는지

작은 scene에서는 flat array가 더 단순하고 빠를 수 있습니다. object 수와 query profile 없이 공간 구조를 도입하지 않습니다.

### LOD

LOD는 camera distance 하나가 아니라 화면에 투영된 크기와 품질 예산으로 선택하는 편이 안정적입니다. bounding sphere radius와 view-space depth로 screen-space error나 pixel diameter를 근사할 수 있습니다.

필요한 계약:

- level별 mesh/material/resource
- 선택 threshold와 hysteresis
- missing level fallback
- transition 중 두 level의 lifetime
- shadow/physics/selection 등 다른 subsystem과의 관계

threshold 경계에서 frame마다 level이 바뀌는 popping을 줄이기 위해 hysteresis를 사용합니다. 선택 결과와 screen metric을 artifact에 기록합니다.

### occlusion culling

frustum 안이지만 다른 surface 뒤에 완전히 가려진 object를 제거합니다. CPU query, hierarchical depth, GPU-driven 방식 등은 후속 구현입니다. 공통 위험은 다음과 같습니다.

- 이전 frame depth를 사용한 temporal lag
- camera가 급변할 때 false occlusion
- query result를 기다려 CPU/GPU 동기화 stall
- 너무 작은 object 단위로 query해 overhead 증가
- conservative하지 않은 bound로 visible object 제거

첫 renderer는 depth test에 맡기고, overdraw profile이 실제 문제임을 확인한 뒤 occlusion을 추가합니다.

### primitive와 back-face culling

object-level visibility와 triangle-level culling은 다릅니다. meshlet이나 GPU-driven culling은 primitive group bounds와 command generation 계약이 추가됩니다. 이 과정에서는 개념과 artifact만 다루고 필수 구현으로 요구하지 않습니다.

### LOD와 asset streaming

선택한 LOD resource가 resident하지 않을 수 있습니다. render thread가 I/O 완료를 기다리지 않게 다음 상태를 둡니다.

```text
requested
loading
resident
failed
retiring
```

현재 resident한 가장 가까운 fallback을 선택하고, frame artifact에 요청 level과 실제 level을 모두 기록합니다.

## 측정값

- scene object 수
- frustum outside/intersect/inside
- LOD level별 선택 수
- requested vs resident LOD 차이
- submitted draw/triangle 수
- depth rejected fragment와 overdraw 추정
- culling CPU 시간
- resource upload와 memory 변화

`draw call 감소`만으로 개선을 판단하지 않습니다. CPU traversal, GPU vertex work, fragment work와 memory를 함께 봅니다.

## 검증 fixture

- frustum 내부/외부/plane 교차 sphere와 AABB
- camera 안에 있는 큰 object
- rotated/non-uniform scale bound
- threshold 전후 LOD와 hysteresis
- 빠른 camera 이동에서 occlusion fallback
- missing/failed LOD resource
- stale bound mutation이 visible object를 제거하는지 검사
- flat scan과 spatial query 결과 집합 비교

## 흔한 오답

- bound가 geometry를 포함하는지 검증하지 않음
- distance만으로 LOD를 선택해 FOV/resolution 변화 무시
- threshold equality에서 매 frame level 진동
- occlusion query 결과를 즉시 기다려 pipeline stall
- static spatial structure에 dynamic object를 갱신하지 않음
- culling이 빨라졌다는 이유로 전체 frame time 개선을 단정
- visible 결과 차이를 tolerance image로 숨김

## 연결 실습

- [`05-textured-lit-scene`](../../exercises/05-textured-lit-scene/README.md): frustum culling과 두 단계 LOD를 작은 scene에 적용합니다.
- [`07-frame-debugging`](../../exercises/07-frame-debugging/README.md): culling 통계와 frame capture draw 목록을 대조합니다.

## 완료 기준

- frustum·LOD·occlusion·depth culling의 입력과 거부 단위를 구분합니다.
- bounds가 geometry를 보수적으로 포함함을 fixture로 검증합니다.
- LOD threshold·hysteresis·residency와 fallback을 상태로 기록합니다.
- culling의 정확성과 CPU/GPU 성능 근거를 별도로 평가합니다.
