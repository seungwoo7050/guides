# 기여 안내

문서, 실습 계약, C++ reference와 검증 도구는 같은 그래픽스 규약을 가리켜야 합니다. 새 효과나 API 이름보다 어떤 상태가 바뀌고, 어떤 실패가 생기며, 어떤 artifact가 결과를 증명하는지 먼저 명확히 합니다.

## 범위와 소유권

이 브랜치는 다음을 소유합니다.

- 좌표 공간에서 frame pixel까지의 graphics pipeline
- rasterization·sampling·depth·blend·lighting의 그래픽스 계약
- mesh·texture·scene asset의 renderable validation
- GPU resource·shader·pipeline·command·frame lifecycle
- frame capture 조사 순서, image oracle와 graphics performance evidence

다음은 다른 브랜치 또는 외부 전문 과정의 소유입니다.

- C++ 문법·RAII·CMake 일반 과정: `cpp`
- 자료구조·복잡도·기준 구현: `algorithms`
- cache·SIMD·멀티코어 일반 원리: `computer-architecture`
- 게임플레이·물리·오디오·게임 엔진 제품 전체
- ray/path tracing, advanced PBR, GPU driver/compiler 전문 과정

같은 설명을 복사하지 않고 필요한 전제와 이 renderer의 상태·실패 적용만 다룹니다.

## 문서를 고칠 때

- 자연스러운 한국어 경어체를 사용합니다.
- API, 타입, 수식과 식별자는 원래 표기와 백틱을 사용합니다.
- 좌표·단위·범위·색 encoding·alpha 표현을 값 이름에 드러냅니다.
- 정의 나열보다 상태, 소유권, 실패 조건과 검증 방법을 우선합니다.
- 특정 API의 현재 사실은 공식 문서, 확인 날짜와 실제 검증 판본을 기록합니다.
- minimum floor, 이번 실행 환경과 비교 문서만 읽은 판본을 섞지 않습니다.
- 성능·정확성·이식성을 실행 근거 없이 단정하지 않습니다.
- 외부 문서의 표와 코드를 복제하지 않고 자체 설명과 fixture를 만듭니다.

핵심 문서 `01–20`은 최소한 다음 절을 유지합니다.

```text
목표
시작하기 전에
연결 실습
완료 기준
```

모든 문서에 동일한 세부 목차를 기계적으로 복제하지 않습니다.

## 규약을 바꿀 때

좌표·색·alpha·sample 규약은 다음 파일과 실제 reference artifact를 함께 검토합니다.

```text
docs/00-roadmap.md
docs/90-appendix/01-math-conventions-and-formulas.md
reference/formulas-and-checklist.md
관련 exercises/*/contract.json
exercises/08-renderer-capstone/project/reference/
```

reference image를 새 결과로 덮어쓰는 것으로 변경을 끝내지 않습니다. 이전/새 결과, 첫 달라진 pipeline 단계, mutation test와 migration 이유를 기록합니다.

## 실습과 계약을 고칠 때

- 실습 `README.md`와 `contract.json`을 함께 갱신합니다.
- 초기 상태, 입력, 필수 artifact, 불변식, 대표 실패와 완료 근거를 명시합니다.
- `required_artifacts`, `invariants`, `known_bad_mutations`, `completion_evidence`가 README의 실제 용어와 대응해야 합니다.
- known-bad mutation은 잘못된 artifact와 false invariant를 만들고 공개 checker에서 거부돼야 합니다.
- image tolerance를 실패 뒤 근거 없이 넓히지 않습니다.
- 자동 검사하기 어려운 시각·설계·운영 판단에는 사람 검토 질문과 필요한 증거를 둡니다.

새 실습 contract는 [`exercises/contract.schema.json`](exercises/contract.schema.json)의 strict field, identifier pattern과 최소 항목을 유지합니다. repository verifier는 JSON 중복 key, 상대 링크·anchor, 관련 문서의 양방향 연결과 최소 의미 대응을 검사하지만 내용의 교육적 충분성을 판정하지 않습니다.

## C++ project를 고칠 때

현재 실행 기반은 [`exercises/08-renderer-capstone/project`](exercises/08-renderer-capstone/project/README.md)의 누적 C++20 project입니다.

- Python 3.10 이상, C++20 compiler와 CMake 3.20 이상을 필수 기반으로 유지합니다.
- `CG_IMPLEMENTATION=reference|starter|workspace`가 같은 `cg-render` CLI를 보존해야 합니다.
- starter와 새 workspace는 유효한 입력에서 명시적 `not-implemented` exit 3을 유지하고, 학습자가 구현한 stage만 pass로 바꿉니다.
- invalid input은 exit 2, invariant 실패는 exit 4, 지원되지 않는 GPU runtime은 exit 5로 구분합니다.
- source와 learner workspace를 checker·test가 예고 없이 덮어쓰거나 삭제하지 않습니다.
- output은 명시한 새 artifact 디렉터리나 build directory에만 씁니다.
- 공개 행동과 artifact를 검사하고 특정 내부 함수·문자열을 정답으로 강제하지 않습니다.

reference 변경은 정상 path뿐 아니라 관련 known-bad mutation이 같은 contract에서 실제로 거부되는지 확인합니다. CPU 결과를 바꾼 뒤 GPU tolerance를 넓히기 전에 첫 다른 transform·coverage·depth·attribute·color 단계를 기록합니다.

## GPU와 shader를 고칠 때

SDL compatibility floor는 3.4.10이며 현재 3.4.12 Metal/MSL 실행과 호환성을 확인했습니다. `CG_GPU`의 의미를 보존합니다.

- `off`: SDL과 actual GPU를 평가하지 않음
- `auto`: 가능한 환경에서 실행하되 미지원 GPU는 미평가로 명시
- `required`: SDL configure와 actual GPU stage가 모두 필수

[`triangle.metal`](exercises/08-renderer-capstone/project/shaders/triangle.metal)은 현재 runtime MSL source이고 [`triangle.hlsl`](exercises/08-renderer-capstone/project/shaders/triangle.hlsl)은 offline SPIR-V·DXIL·MSL 입력입니다. SDL_shadercross commit, entry point, layout, hash와 정확한 명령은 [`shaders/manifest.json`](exercises/08-renderer-capstone/project/shaders/manifest.json)을 정본으로 유지합니다.

- generated `.spv`, `.dxil`, `.msl`/`.metallib`과 generated header는 `build/`에만 둡니다.
- compiler·options·input/output hash 없이 generated binary를 source에 추가하지 않습니다.
- actual Metal/MSL 성공을 Vulkan·D3D12나 다른 platform 성공으로 표현하지 않습니다.
- 현재 actual shader는 position·vertex color만 소비합니다. texture/sampler/material/normal/light binding을 추가하지 않은 결과를 textured-lit GPU parity로 표현하지 않습니다.
- `submit_to_fence_ns`는 CPU wall time이며 GPU timestamp로 이름을 바꾸거나 해석하지 않습니다.
- validation log와 readback은 capture file, 실제 window resize와 장시간 driver 안정성을 대신하지 않습니다.
- lifecycle simulator의 resize/generation과 synthetic workload를 실제 window event·GPU workload 측정으로 표현하지 않습니다.
- GPU mutation은 기본적으로 unsafe state를 제출하기 전에 거부합니다. 실제 driver validation 실험이 필요하면 격리된 fixture, timeout, cleanup과 복구 절차를 먼저 문서화합니다.

## fixture, 출처와 라이선스

현재 project에는 외부 image·mesh·scene asset이 없습니다. `scene-v1.json`과 `marker-texture.json`은 `repository-generated-fixture`, `external_asset: false`, `license: MIT`를 명시합니다. 나머지 invalid/event JSON도 저장소 자체 test input이며 [코드·JSON의 MIT 계약](LICENSE.md)을 따릅니다.

외부 asset을 추가한다면 다음을 함께 제출합니다.

- 원본 source URL과 가져온 날짜
- content hash
- 원본 license와 재배포 가능 여부
- 좌표·색·alpha·channel·import 변환
- fixture/reference 결과가 바뀐 이유

외부 자료를 repository-generated로 표시하거나 출처 없는 binary를 commit하지 않습니다.

## 안전 계약

GPU 실행, capture, 외부 asset과 생성물 처리에는 [`SAFETY.md`](SAFETY.md)를 적용합니다. 기본 검증은 작은 고정 extent와 제한된 frame 수로 실행하고, 실제 장비에서 hang·device loss·과열·메모리 증가가 관찰되면 실행을 중단해 환경·마지막 정상 사건·validation log를 보존합니다. capture에는 사용자 경로, 다른 process/window 내용과 device 식별 정보가 포함될 수 있으므로 공개 전 검토합니다.

`make clean`은 `.guide/`, `build/`, `out/`만 대상으로 하며 learner `workspace/`와 실패 artifact를 자동 삭제하지 않습니다. 새 정리 도구는 정확한 대상, dry-run 또는 동등한 사전 확인, 비파괴 복구 경계를 갖춰야 합니다.

## 변경 전 준비와 검증

```sh
./prepare.sh
python3 scripts/verify_repository.py --quick
make check
./verify.sh
```

`prepare.sh`는 package를 설치하지 않습니다. Git, Python 3.10, CMake 3.20, C++20 compiler를 검사하고 SDL3/capture 도구의 환경 정보와 source 지문을 기록합니다. source를 변경했다면 다시 실행합니다.

`verify.sh`는 고유 임시 복사본에서 독립 검사를 계속 실행해 하나의 실패가 다른 근거를 숨기지 않게 합니다.

- repository 문서·상대 링크·anchor·contract와 verifier negative controls
- Python syntax와 PPM 정상·오답 oracle
- starter not-implemented negative control
- reference stage와 known-bad mutation
- workspace 생성·비파괴 안전성
- release build와 CTest
- 지원 compiler/runtime의 address·undefined sanitizer
- `VERIFY_GPU=auto|required|off` 정책에 따른 GPU 검사
- 원본 source snapshot과 tracked Git 상태 불변

이 검사가 통과해도 문서의 교육적 완성, 실제 window resize/high-DPI, 외부 capture tool과 실행하지 않은 backend를 자동 증명하지 않습니다. GPU 미평가와 성공을 구분하고 로그를 검토합니다.

실제 GPU·capture·외부 asset을 다룬 변경은 자동 검사 뒤에도 [`SAFETY.md`](SAFETY.md)의 사람 검토 항목을 확인합니다.

커밋 전에는 다음도 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

## 버전 갱신

SDL, Vulkan, WebGPU/WGSL, RenderDoc, CMake와 glTF 기준을 갱신할 때는 공식 release/specification을 확인합니다. 정본은 [`reference/version-baseline.md`](reference/version-baseline.md)에 기록합니다.

1. 최소 floor와 실제 실행 판본을 분리합니다.
2. API ownership, shader format·binding과 coordinate/format 영향을 검토합니다.
3. tracked shader source와 manifest compiler commit·명령·hash를 확인합니다.
4. CPU reference, mutation, PPM, sanitizer와 지원 GPU runtime을 다시 실행합니다.
5. capture, resize와 다른 backend의 미검증 범위를 공개합니다.

## 커밋 예시

```text
docs(raster): shared-edge fill rule의 경계 계약 보완
docs(gpu): Metal runtime source와 offline target 경계 명시
feat(reference): depth mutation oracle 추가
test(exercise): affine UV mutation 계약 강화
tool(ppm): P6 extent 오류 진단 보완
```

서로 독립적인 개념, reference 단계, fixture와 검증 인프라 변경은 의미 단위로 나누어 기록합니다.
