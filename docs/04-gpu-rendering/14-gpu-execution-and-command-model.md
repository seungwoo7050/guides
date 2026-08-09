# GPU 실행과 command 모델

## 목표

CPU 함수 호출과 GPU 작업 완료를 같은 사건으로 취급하지 않고, device·queue·command buffer·pass·submission의 상태와 수명을 구분합니다. 소프트웨어 renderer의 순차 pipeline을 비동기 GPU 실행으로 옮길 때 어떤 값이 기록 시점에 고정되고 어떤 resource가 완료 시점까지 살아 있어야 하는지 설명합니다.

## 시작하기 전에

[렌더링 계약](../01-visual-model/01-rendering-contract-and-frame.md)의 frame snapshot과 artifact를 사용합니다. C++ RAII 객체가 파괴됐다는 사실과 GPU가 resource 사용을 끝냈다는 사실은 다릅니다.

### host와 device

CPU(host)는 다음을 수행합니다.

- scene snapshot 준비
- GPU resource 생성 요청
- upload data 준비
- pipeline과 binding 선택
- command 기록
- submission
- completion 관찰과 resource retire

GPU(device)는 제출된 command를 자신의 queue와 execution unit에서 비동기로 처리합니다. `submit()` 반환은 일반적으로 “완료”가 아니라 “접수 또는 제출 성공”에 가깝습니다.

### device와 backend

GPU device 생성 시 다음을 기록합니다.

- 선택 backend와 adapter/device 이름
- 지원 shader format
- swapchain format과 present mode에 해당하는 정책
- limits와 feature profile
- validation/debug 설정
- driver/runtime version을 얻을 수 있다면 해당 값

SDL3 GPU 구현 프로필에서는 device 생성 시 제공 가능한 shader format을 선언하고, 선택된 driver/backend에 맞는 shader binary를 제공합니다. API가 cross-platform이라는 이유로 모든 device가 같은 format·limit·성능을 갖는다고 가정하지 않습니다.

### command buffer

command buffer는 즉시 GPU를 움직이는 함수 묶음이 아니라 실행할 작업의 기록입니다. 기본 상태 기계를 다음처럼 볼 수 있습니다.

```text
available
→ recording
→ ended/ready
→ submitted
→ completed
→ reusable 또는 released
```

API에 따라 객체 재사용 방식은 다르지만, submitted 상태의 backing memory나 command resource를 임의로 덮어쓰지 않는 원리는 같습니다.

명령 기록 중 사용하는 CPU pointer의 수명과 GPU가 실제로 읽는 resource의 수명을 구분합니다. upload API가 데이터를 즉시 복사하는지 command 실행 때 읽는지 공식 계약을 확인합니다.

### pass

render pass는 color/depth attachment와 load/store 계약 안에서 draw를 기록합니다. copy pass와 compute pass는 다른 resource 사용과 ordering을 가집니다.

한 render pass 안에서 다음은 보통 draw state의 일부입니다.

- graphics pipeline
- viewport/scissor
- vertex/index buffer
- texture/sampler/uniform/storage binding
- draw parameters

pass가 끝나면 API에 따라 dynamic binding state가 reset될 수 있습니다. 이전 pass 상태가 남아 있다고 가정하지 않습니다.

### submission과 ordering

같은 queue에 제출된 command의 순서와 resource visibility는 API의 synchronization 계약에 따릅니다. “CPU 코드가 먼저 실행됐다”는 사실만으로 GPU 순서를 보장하지 않습니다.

초기 구현은 한 graphics queue와 한 command buffer per frame을 사용할 수 있습니다. 여러 queue, parallel recording과 async compute는 실제 병목과 명확한 synchronization graph가 생긴 뒤 확장합니다.

### upload 흐름

정적 mesh를 예로 들면 다음 상태가 있습니다.

```text
CPU mesh bytes
→ transfer/upload buffer
→ copy command
→ GPU vertex/index buffer
→ graphics draw에서 read
→ upload resource retire
```

copy 제출 직후 staging buffer를 파괴하면 GPU가 아직 읽는 중일 수 있습니다. completion fence 또는 API가 제공하는 release semantics를 사용합니다. GPU buffer가 생성됐다는 사실만으로 내용이 upload됐거나 visible하다고 판단하지 않습니다.

### error와 device loss

resource 생성 실패, shader/pipeline 실패, swapchain acquire 실패와 device loss를 구분합니다. 오류를 로그한 뒤 null handle로 draw를 계속하지 않습니다.

- recoverable frame condition: minimize/zero extent, 일시 acquire 불가
- resource-local failure: 특정 texture 또는 pipeline 생성 실패
- device-wide failure: device loss 또는 backend fatal error

복구할 범위와 애플리케이션 종료 조건을 설계합니다. capstone에서는 모든 device loss 복구를 요구하지 않지만, 오류 분류와 cleanup은 문서화합니다.

## 실행 trace

한 frame에 다음 event를 남깁니다.

```text
frame 17 scene_version 5
acquire command_buffer 42
acquire swapchain_texture generation 3 extent 1280x720
begin copy pass
upload mesh 8 generation 2 bytes 24576
end copy pass
begin render pass color=swapchain depth=91
bind pipeline 12
bind mesh 8
record draw primitive_count=2048
end render pass
submit command_buffer 42 fence/frame_slot 2
```

trace는 API 호출 나열을 넘어 handle generation과 resource 사용 관계를 보여야 합니다.

## 흔한 오답

- submit 반환 뒤 staging·uniform memory를 즉시 재사용
- command recording과 GPU execution 시간을 같은 profile 구간으로 측정
- 이전 pass의 pipeline/binding이 유지된다고 가정
- backend가 바뀌어도 shader binary와 coordinate convention이 같다고 가정
- null/invalid handle을 skip하며 검은 화면 원인 숨김
- 여러 queue를 추가하면 자동으로 병렬성이 생긴다고 판단

## 연결 실습

- [`06-gpu-first-frame`](../../exercises/06-gpu-first-frame/README.md): device·command buffer·pass·submission trace로 첫 삼각형을 제출합니다.
- [`07-frame-debugging`](../../exercises/07-frame-debugging/README.md): command marker와 frame capture의 event를 대조합니다.

## 완료 기준

- CPU 호출, command 기록, submission과 GPU 완료를 네 개의 사건으로 구분합니다.
- upload와 draw가 참조하는 resource의 수명을 completion까지 유지합니다.
- pass별 attachment·load/store·binding 상태를 명시합니다.
- backend·shader format·device error를 frame artifact에 기록하고 실패 범위를 분류합니다.
