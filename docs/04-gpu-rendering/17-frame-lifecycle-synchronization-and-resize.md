# frame lifecycle·동기화·resize

## 목표

swapchain image 획득부터 command 기록·제출·GPU 완료·present와 frame slot 재사용까지의 상태를 명시합니다. 여러 frame이 동시에 진행될 때 uniform/upload/attachment를 안전하게 재사용하고, window resize·minimize·swapchain generation 변경을 일회성 예외가 아닌 정상 입력으로 처리합니다.

## 시작하기 전에

[GPU command 모델](14-gpu-execution-and-command-model.md)과 [resource retirement](15-resources-layouts-transfers-and-formats.md)을 사용합니다. 특정 API의 semaphore/fence 이름보다 “어떤 사건이 어떤 사용을 끝냈는가”를 먼저 설명합니다.

### frame slot

frames-in-flight를 `N`개 사용하면 CPU가 frame `k+1`을 준비하는 동안 GPU가 frame `k`를 처리할 수 있습니다. 각 slot은 GPU가 읽는 동적 resource를 독립적으로 가져야 합니다.

```text
FrameSlot
├── slot id와 generation
├── command resource
├── camera/object upload range
├── transient descriptor/binding state
├── completion token/fence
└── deferred destruction list
```

slot을 재사용하기 전에 이전 submission 완료를 확인합니다. 단순 `frame_index % N` 계산은 완료 보장이 아닙니다.

### 한 frame의 상태 기계

```text
idle slot
→ wait/poll previous completion
→ reset slot-local allocators
→ acquire command buffer
→ acquire swapchain texture
→ record upload/render passes
→ submit
→ present 또는 API의 submit-present 경로
→ in flight
→ completion observed
→ retire deferred resources
→ idle
```

API에 따라 swapchain acquire가 command recording 중 이뤄지거나 present가 submit에 결합될 수 있습니다. 내부 trace는 같은 논리 사건을 유지합니다.

### CPU/GPU synchronization

CPU가 매 frame GPU 완료를 기다리면 correctness는 단순해지지만 병렬성이 사라집니다. 다음 경우에만 필요한 wait를 둡니다.

- 해당 frame slot resource를 재사용할 때
- readback 결과를 CPU가 실제로 필요로 할 때
- device shutdown과 resource 최종 파괴
- swapchain/resource recreation이 이전 사용 완료를 요구할 때

upload마다 global idle wait를 호출하지 않습니다. queue completion token과 deferred retirement로 범위를 줄입니다.

### GPU 내부 dependency

같은 resource를 한 pass에서 쓰고 다음 pass에서 읽는 순서는 command stream과 API synchronization contract로 표현합니다. abstraction API가 transition을 자동 처리해도 pass 순서와 동일 command buffer/submit 관계를 유지해야 합니다.

readback이나 screenshot은 GPU color texture→transfer buffer copy와 CPU access 완료가 필요합니다. copy command를 기록한 즉시 CPU pointer를 읽지 않습니다.

### resize

window logical size, drawable pixel size와 render extent는 다를 수 있습니다. high-DPI 환경에서 logical width만 사용하면 viewport와 attachment가 어긋납니다.

resize 처리:

1. 새 drawable extent 관찰
2. zero extent/minimized이면 frame render를 skip하거나 wait 정책 적용
3. swapchain generation/format 변경 여부 확인
4. 새 depth/offscreen attachment 생성
5. 새 extent가 필요한 pipeline/state 갱신
6. 이전 generation은 in-flight 완료 뒤 retire
7. camera aspect와 viewport/scissor 갱신
8. 첫 새 frame artifact에 generation과 extent 기록

resize event가 여러 번 연속 오면 매 event마다 무거운 resource를 생성하기보다 실제 render 시 최신 extent로 coalesce할 수 있습니다.

### swapchain image 수명

acquired swapchain texture는 일반 asset texture처럼 장기 보관하지 않습니다. 현재 frame과 acquire generation에만 유효한 handle일 수 있습니다. 다음 frame에 저장해 재사용하지 않습니다.

acquire 실패 또는 texture 없음은 device loss와 같지 않을 수 있습니다. minimize, zero extent와 일시 상태를 API 문서에 따라 분류합니다.

### deferred destruction

shader/texture/mesh reload와 resize는 이전 GPU resource를 즉시 파괴하지 않습니다.

```text
retire(resource, completion_token_of_last_use)
```

completion을 관찰한 뒤 실제 destroy합니다. frame slot별 deferred list 또는 timeline value를 사용할 수 있습니다. resource가 어느 submission에서 마지막 사용됐는지 기록해야 합니다.

### shutdown

종료에서도 수명 계약을 지킵니다.

1. 새 frame 제출 중단
2. in-flight 완료 또는 device-defined wait
3. deferred resource 파괴
4. swapchain/window 연결 해제
5. pipeline/shader/resource 파괴
6. device 파괴

callback/thread가 device 파괴 뒤 resource를 만지지 않게 종료 순서를 문서화합니다.

## 검증 fixture

- frame slot 2–3개에서 object uniform이 서로 섞이지 않음
- GPU 완료를 지연시킨 상태에서 slot overwrite mutation 거부
- 800×600→1280×720 resize와 aspect 갱신
- 연속 resize와 zero extent/minimize
- old depth attachment가 in-flight 중 retire 대기
- screenshot readback이 completion 뒤만 CPU에서 접근
- asset reload와 이전 generation frame
- 종료 중 in-flight command와 deferred resource

trace에는 `frame_id`, `slot`, `swapchain_generation`, `extent`, `submission_id`, `completion_id`를 함께 남깁니다.

## 흔한 오답

- `frame_index % N`만으로 slot 재사용 안전성 판단
- 매 frame global GPU idle wait
- logical window size를 drawable extent로 사용
- resize 즉시 이전 attachment 파괴
- acquired swapchain handle을 다음 frame에 보관
- screenshot copy 직후 CPU buffer 읽기
- 종료 시 device를 먼저 파괴하고 resource wrapper 소멸

## 연결 실습

- [`06-gpu-first-frame`](../../exercises/06-gpu-first-frame/README.md): frame slot, acquire·submit과 resize trace를 구현합니다.
- [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md): reload·resize·screenshot·deferred destruction을 통합합니다.

## 완료 기준

- frame slot의 재사용을 실제 GPU completion 사건과 연결합니다.
- CPU wait, GPU dependency와 readback wait를 서로 다른 목적으로 사용합니다.
- resize·zero extent·swapchain generation을 정상 상태 전이로 처리합니다.
- reload와 종료에서 last-use submission 뒤 resource를 파괴합니다.
