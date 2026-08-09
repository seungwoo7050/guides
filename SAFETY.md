# 안전 및 운영 계약

이 저장소의 기본 실습은 로컬의 작은 결정적 fixture와 제한된 offscreen GPU frame을 대상으로 합니다. 유료 cloud resource 생성, 실제 서비스 배포, 시스템 driver 변경, 관리자 권한 사용이나 외부 시스템 조작을 요구하지 않습니다. `prepare.sh`도 package를 설치하지 않습니다.

## 실행 전 경계

- 먼저 `./prepare.sh`로 Python·C++·CMake와 선택 GPU 도구의 상태를 기록합니다.
- GPU가 필요하지 않은 CPU 회귀는 `CG_GPU=off` 또는 `--gpu off`로 분리합니다. 이 결과를 actual GPU 성공으로 표시하지 않습니다.
- actual GPU 검사는 지원 여부를 탐색할 때 `auto`, 반드시 실행해야 할 통제된 환경에서만 `required`를 사용합니다.
- 기본 64×64 fixture와 공개 checker의 frame 수에서 시작합니다. extent·frame 수·asset 크기를 늘릴 때 예상 GPU/CPU memory와 출력 크기, timeout을 먼저 정합니다.
- output은 `build/`, `out/` 또는 새 임시 디렉터리에 둡니다. 개인 파일이 있는 기존 디렉터리를 artifact root로 재사용하지 않습니다.

## GPU·driver 안전

잘못된 GPU state는 process 종료를 넘어 driver reset, device loss, 화면 정지나 긴 대기를 일으킬 수 있습니다.

- known-bad mutation은 기본적으로 unsafe submission 전에 계약 검사로 거부합니다. `mutation-diagnostic.json`의 `executed_on_gpu: false`는 이 안전 경계를 뜻합니다.
- 실제 validation 실험이 필요하면 한 mutation·한 frame·작은 offscreen target으로 격리하고 timeout과 종료 경로를 둡니다. production renderer, 공유 원격 장비나 저장하지 않은 작업이 있는 환경에서 실행하지 않습니다.
- resource는 last-use completion 전 파괴·재사용하지 않고, readback은 fence 완료 뒤 map합니다. resize/reload는 generation을 올리고 이전 generation을 completion 뒤 retire합니다.
- zero extent, acquire 실패, device loss와 out-of-memory를 정상적인 실패 상태로 분류합니다. 무제한 retry나 allocation loop를 두지 않습니다.
- hang, 반복되는 device loss, 비정상 memory 증가, 과열 또는 화면 불안정이 보이면 실행을 중단합니다. 마지막 정상 event, backend/device, validation log와 재현 명령을 보존하고 CPU/lifecycle 경로로 회귀 범위를 분리합니다.

현재 actual reference는 macOS Metal의 작은 offscreen color/depth 경로입니다. 같은 device에서 2 slots·3 submits와 64×64→96×72 generation 전이를 실제 실행하고 completion 뒤 retire/readback하지만, window/swapchain을 만들지 않습니다. 따라서 이 trace는 실제 window resize·minimize·high-DPI 증거가 아니며, colored triangle readback도 texture/material/lighting GPU 이식을 증명하지 않습니다.

## capture·로그와 개인정보

GPU capture, validation log와 environment artifact에는 device/driver 식별자, 사용자 경로, shader/resource 내용이 들어갈 수 있습니다. window capture 도구는 다른 application이나 화면 내용까지 포함할 수 있습니다.

- capture 범위를 대상 process와 한 frame으로 제한하고, 시작 전 다른 민감한 window와 resource를 닫습니다.
- capture binary, screenshot, absolute path, device id와 로그를 공개하거나 commit하기 전에 민감 정보와 제3자 자료를 검토합니다.
- 저장소에는 capture binary 대신 가능하면 tool/version, backend, frame/event/resource label, 재현 명령과 필요한 최소 screenshot을 남깁니다.
- `capture-reference.txt` 같은 label 참조를 실제 capture file로 표현하지 않습니다.

## asset·shader와 출처

현재 포함된 scene·marker·invalid/event fixture는 저장소가 직접 만든 MIT test input이며 외부 image·mesh·scene asset이 아닙니다. 외부 자료를 추가할 때는 source URL, 가져온 날짜, content hash, 원본 license·재배포 조건과 import 변환을 기록합니다.

- 출처가 불명확한 binary, model, texture, shader나 capture를 추가하지 않습니다.
- 외부 자료를 `repository-generated-fixture`로 표시하지 않습니다.
- generated shader binary와 header는 `build/`에만 두고, tracked source와 manifest hash를 정본으로 유지합니다.
- 외부 asset parser는 index/count/extent, NaN/inf, 참조 cycle과 예상 memory 크기를 allocation·render 전에 검증합니다.

법적 배포 범위는 [라이선스](LICENSE.md), 공식 출처와 고정 판본은 [reference 자료](reference/sources.md)와 [version 기준](reference/version-baseline.md)을 따릅니다.

## 생성물 정리와 복구

`make clean`은 `.guide/`, `build/`, `out/` 생성물만 대상으로 하며 learner `workspace/`를 삭제하지 않습니다.

- 실패 artifact와 validation/capture metadata는 원인 조사가 끝날 때까지 보존합니다.
- workspace가 손상되면 먼저 다른 이름이나 저장소 밖 위치에 복사해 보존합니다. 기존 경로가 없어진 뒤 `./scripts/new-workspace.sh`로 새 starter 사본을 만듭니다.
- reference/expected를 실제 learner 결과로 덮어써 실패를 숨기지 않습니다.
- 정리 전에 대상 경로가 저장소의 생성물 디렉터리인지 확인합니다. 광범위한 재귀 삭제, unresolved glob·환경 변수 또는 저장소 root를 대상으로 삼지 않습니다.

## 자동 검사와 사람 확인

자동 검사는 고정 fixture, artifact schema, mutation 거부, build/CTest와 지원 actual GPU의 좁은 공개 행동을 회귀시킵니다. 다음은 사람이 별도로 확인합니다.

- 설명과 학습 순서의 충분성
- texture/material/normal/lighting의 실제 GPU binding과 debug attachment
- window resize·minimize·high-DPI, reload·shutdown stress
- 외부 capture의 event/resource label과 개인정보
- 실제 GPU timestamp/counter, raw workload와 성능 결론
- 실행하지 않은 backend/platform과 외부 asset의 라이선스

실행하지 못한 필수 검사는 `not-evaluated`와 이유로 남깁니다. simulation, manifest 또는 exit 0을 actual GPU·capture·성능 완료로 바꾸어 보고하지 않습니다.
