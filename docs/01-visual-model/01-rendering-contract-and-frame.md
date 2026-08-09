# 렌더링 계약과 한 프레임

## 목표

렌더링을 “API를 호출해 화면을 갱신하는 일”이 아니라 입력 상태를 검증 가능한 frame artifact로 바꾸는 과정으로 정의합니다. 장면, 카메라, 설정, 시간, 외부 asset 중 무엇이 같은 입력일 때 같은 결과를 만들어야 하는지 구분하고, 최종 color image 외에 어떤 중간 상태를 남겨야 실패를 좁힐 수 있는지 정합니다.

## 시작하기 전에

이 문서는 C++ 객체 설계나 일반 상태 기계 작성을 다시 설명하지 않습니다. [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp)의 값·수명·책임 계약을 그래픽스의 frame 경계에 적용합니다.

과정 전체에서 한 frame의 논리 입력을 다음처럼 봅니다.

```text
FrameInput
├── scene snapshot
│   ├── mesh와 material 참조
│   ├── object transform
│   └── light
├── camera snapshot
├── render settings
├── output extent와 format
└── frame time 또는 고정 tick
```

출력은 화면 하나가 아닙니다.

```text
FrameArtifacts
├── final color
├── depth
├── object/primitive id
├── transform trace
├── draw/triangle/fragment 통계
├── 경고와 거부된 asset 목록
└── CPU/GPU timing과 환경 정보
```

### frame 입력을 snapshot으로 만드는 이유

렌더링 중 다른 thread가 scene transform을 바꾸면 한 object의 bounding volume은 이전 위치, vertex는 새 위치를 사용할 수 있습니다. 이런 오류는 “thread-safe container를 썼다”는 사실만으로 사라지지 않습니다. 한 frame이 읽는 상태의 버전과 lifetime을 고정해야 합니다.

가능한 방식은 여러 가지입니다.

- render thread 전용 immutable snapshot
- double-buffered scene state
- versioned handle과 명시적 publish
- update와 render 단계 사이의 barrier

어떤 방식을 쓰든 다음 불변식을 검사합니다.

1. 한 draw가 읽는 mesh, material, transform은 같은 scene version에 속합니다.
2. frame 제출이 끝날 때까지 GPU가 참조하는 resource가 살아 있습니다.
3. resize 전후 attachment extent를 한 pass에서 섞지 않습니다.
4. 실패한 asset이나 pipeline을 암묵적인 임의 값으로 바꾸지 않습니다.

### 결정적 정본과 실시간 실행을 분리하기

소프트웨어 정본은 고정 입력에서 byte-identical artifact를 목표로 할 수 있습니다. 실제 GPU 결과는 driver, shader compiler, 부동소수점 최적화와 format에 따라 작은 차이가 생길 수 있습니다. 그렇다고 모든 차이를 허용하면 검사기가 의미가 없어집니다.

비교 정책은 단계별로 둡니다.

- 정수 coverage, object id, primitive id: 정확히 같아야 함
- depth: 고정된 절대·상대 오차와 유효 범위 검사
- linear color: channel별 오차, changed-pixel 비율과 region mask
- 최종 sRGB image: 시각 검토용이며 원인 판정에는 중간 attachment를 우선

### frame graph라는 이름보다 먼저 필요한 것

초기에는 범용 frame graph를 구현하지 않습니다. pass별 읽기·쓰기 attachment와 resource lifetime을 표로 기록하는 것으로 충분합니다.

| pass | 읽기 | 쓰기 | 완료 뒤 필요한가 |
|---|---|---|---|
| upload | staging data | vertex/texture | staging은 submit 완료 뒤 폐기 가능 |
| geometry | vertex/index/material | color, depth, id | color·depth는 이후 pass에서 읽을 수 있음 |
| present | color | swapchain | present 완료 뒤 frame slot 재사용 |

이 표가 없다면 render pass 추상화보다 먼저 소유권이 불명확한 것입니다.

## 실패 모델과 관찰 근거

### 빈 화면

빈 화면은 원인이 아닙니다. 다음 카운터와 artifact를 순서대로 확인합니다.

1. 유효 scene object 수
2. camera frustum을 통과한 object 수
3. 제출한 draw 수
4. 유효 triangle 수
5. clipping 뒤 primitive 수
6. coverage sample 수
7. depth를 통과한 fragment 수
8. color attachment write 수
9. present 대상과 최종 attachment의 일치

처음 0이 된 지점이 조사 시작점입니다.

### 오래된 frame 또는 깜빡임

frame id, scene version, resource generation, swapchain extent를 artifact에 함께 남깁니다. “가끔 이전 값이 보인다”는 증상만으로 동기화 오류라고 단정하지 않습니다. CPU snapshot, upload, command recording, GPU completion, present 중 어느 version이 어긋났는지 확인합니다.

### 결과는 맞지만 재현되지 않음

시간, random seed, asset order, unordered container iteration, compiler 최적화, output format을 기록합니다. 테스트 fixture에서는 object와 draw order를 명시적으로 정렬하고, animation time을 고정합니다.

## 설계 검토 질문

- frame의 정본 입력은 누가 만들고 언제 publish합니까?
- 실패한 asset·shader·pipeline은 frame 전체 실패입니까, 해당 object 거부입니까?
- attachment별 초기값과 load/store 의미는 무엇입니까?
- 최종 image가 틀렸을 때 어느 중간 artifact가 첫 차이를 보여 줍니까?
- frame slot은 어떤 완료 사건 뒤 재사용할 수 있습니까?
- frame 통계가 실제 work를 세는지, API 호출만 세는지 구분됩니까?

## 연결 실습

- [`01-transform-trace`](../../exercises/01-transform-trace/README.md): 고정 scene snapshot과 frame id를 가진 좌표 trace를 만듭니다.
- [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md): software와 GPU가 같은 `FrameInput`을 소비하고 비교 가능한 artifact를 생성하도록 설계합니다.

## 완료 기준

- 한 frame의 입력·중간 상태·최종 artifact와 소유자를 표로 설명합니다.
- 결정적으로 같아야 하는 값과 허용 오차가 필요한 값을 구분합니다.
- 빈 화면 또는 깜빡임을 카운터와 version 정보로 첫 실패 단계까지 좁힙니다.
- resource가 “CPU 객체가 파괴되지 않음”과 “GPU가 더 이상 사용하지 않음”을 별개 상태로 가짐을 설명합니다.
