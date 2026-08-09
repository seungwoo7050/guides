# 실습 07 — frame debugging

## 목적

의도적으로 주입한 GPU 결함을 validation message·debug label·frame capture·software/debug attachment·CPU/GPU timing으로 분류합니다. 화면을 보고 추측하지 않고 마지막 정상 상태와 첫 비정상 상태를 갖는 bug report를 만듭니다.

관련 문서:

- [debugging·validation·frame capture](../../docs/04-gpu-rendering/18-debugging-validation-and-frame-capture.md)
- [성능·profiling·frame budget](../../docs/04-gpu-rendering/19-performance-profiling-and-frame-budget.md)
- [image diff와 oracle](../../docs/90-appendix/03-image-diff-and-test-oracles.md)

## 결함 case

최소 여섯 개를 선택합니다.

- 잘못된 matrix order
- vertex stride/format mismatch
- shader binding slot mismatch
- front-face/culling 반전
- depth clear/compare 불일치
- sRGB/data texture 교환
- uniform frame slot overwrite
- resize 뒤 stale attachment
- blend factor와 alpha representation mismatch
- GPU readback 완료 전 CPU access

일부는 validation이 검출하고 일부는 의미/image 검사만 검출해야 합니다.

## 조사 절차

```text
고정 frame 재현
→ environment와 input hash 확인
→ validation 새 message 확인
→ pass/draw event 존재 확인
→ attachment와 pipeline state
→ vertex/index/resource binding
→ shader input/output
→ depth/blend/present
→ software/debug attachment 비교
→ 최소 재현과 수정
```

## 필수 artifact

```text
out/frame-debugging/<case>/
├── report.md
├── environment.json
├── frame-trace.json
├── validation.log
├── capture-reference.txt 또는 capture file 경로/metadata
├── before.ppm
├── after.ppm
├── diff.json
└── timing.json
```

capture binary를 저장소에 넣지 못하면 재현 명령, tool version, frame/event/resource label과 screenshot을 남깁니다.

## report 필수 항목

- 증상과 재현 조건
- 마지막 정상 pipeline 단계
- 첫 비정상 값·resource·event
- validation이 검출한 것/검출하지 못한 것
- root cause
- 최소 수정
- regression oracle
- 수정 전후 CPU/GPU timing이 있다면 값과 환경
- 남은 불확실성

## 성능 case

정확성 결함과 별도로 한 workload를 profile합니다.

- resolution 변경
- draw 수 변경
- shader 단순화

세 실험에서 CPU/GPU 어느 구간이 변하는지 기록하고 병목 가설 하나를 검증합니다. 최적화 구현은 필수가 아니지만 근거 없는 결론은 허용하지 않습니다.

## 완료 근거

- 서로 다른 계층의 결함 최소 여섯 개 보고서
- validation이 못 잡는 의미 오류 최소 두 개
- capture event/resource label과 CPU trace 대응
- before/after diff와 regression test
- CPU/GPU timing을 분리한 병목 조사 하나

## 준비·workspace·stage 검사

[공통 workspace 절차](../README.md#workspace-준비와-공개-명령)의 같은 build와 frame id를 사용합니다.

```sh
cmake -S exercises/08-renderer-capstone/project -B build/workspace -DCG_IMPLEMENTATION=workspace -DCG_GPU=auto
cmake --build build/workspace
python3 exercises/check.py --impl workspace --stage 07-frame-debugging --expect pass --gpu auto
python3 exercises/check.py --impl reference --stage 07-frame-debugging --expect pass --gpu off
```

checker는 최소 여섯 결함 보고서의 artifact, before/after oracle, trace/capture label 관계와 CPU/GPU timing 구분을 검사합니다. 실제 validation·capture·timestamp 증거는 지원 환경에서 `--gpu required`로 다시 수집하며 생략을 성공으로 바꾸지 않습니다.

사람 검토에서는 validation이 검출한 오류와 의미 오류를 구분하고, 각 case의 마지막 정상/첫 비정상 상태를 지목하며, 세 workload 실험이 병목 가설을 어떻게 지지하거나 반박했는지 설명합니다.

`make clean`은 생성 build/out만 제거합니다. 실패 case의 환경·capture metadata·trace는 재현이 끝날 때까지 보존하고 workspace는 삭제하지 않습니다. capture binary를 보관할 수 없으면 재현 명령과 event/resource label을 남깁니다.
