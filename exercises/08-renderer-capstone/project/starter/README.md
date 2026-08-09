# 누적 renderer starter

이 디렉터리는 공개 `cg-render` CLI와 같은 C++20 build 계약을 유지하는 학습자 출발점입니다. 각 stage에는 입력, artifact 경계, 불변식, 대표 실패와 이름 있는 `TODO`가 있지만 구현되지 않은 함수는 출력 디렉터리를 만들지 않고 정확히 `exit_not_implemented = 3`을 반환합니다. 빈 JSON이나 reference 복사본을 성공 증거로 만들지 마십시오.

`scripts/new-workspace.sh`는 이 디렉터리를 `workspace/`로 한 번만 복사합니다. 기존 workspace를 덮어쓰거나 자동 삭제하지 않습니다.

## stage별 구현 지도

| stage | starter 함수와 TODO 단위 | 완료할 주요 artifact | 반드시 거부하거나 구분할 대표 실패 |
|---|---|---|---|
| 01 transform trace | `stage01_transform_trace`: typed transform, clip, hierarchy·normal 검증 | `conventions.json`, transform case JSON, `rejected.json` | matrix 순서 교환, clip 전 divide, cycle, singular normal transform |
| 02 sampling/color | `stage02_sampling_and_color`: address/filter, color·alpha, mip | `samples.json`, address/filter/alpha PPM, `report.json` | negative UV truncate, encoded sRGB 보간, alpha 계약 불일치, odd mip texel 유실 |
| 03 coverage | `stage03_triangle_coverage`: setup/bounds, top-left coverage, ownership evidence | coverage·primitive-id image, `setup-trace.json`, count/mutation report | shared-edge equality 오류, 음수 bounds truncate, Y flip 뒤 winding, degenerate divide |
| 04 perspective/depth/blend | `stage04_perspective_depth_blend`: reciprocal-w, depth state, linear blend | perspective/depth/primitive-id/blend image, pixel trace, `report.json` | affine UV, depth convention 반전, transparent depth write, encoded color blend |
| 05 textured lit scene | `stage05_textured_lit_scene`: asset validation, sampling·lighting, culling·LOD | final/debug PPM, `asset-validation.json`, `culling-lod.json`, `frame.json` | invalid index/cycle/singular normal, seam merge, stale bounds, LOD oscillation |
| 06 GPU first frame | `stage06_gpu_first_frame`: device/pipeline, fenced readback, resize generation | environment/shader/resource/pipeline JSON, frame/resize trace, screenshot, validation log | layout/binding/format mismatch, in-flight overwrite, completion 전 readback, stale extent |
| 07 debugging/profiling | `stage07_frame_debugging`: ordered diagnosis, lifecycle trace, measured workloads | six case reports, before/after diff, capture metadata, `timing-report.json` | first difference 오진, slot overwrite, stale generation, warm-up 포함 또는 hash 없는 timing |
| 08 renderer capstone | `stage08_renderer_capstone`: shared snapshot, ordered CPU/GPU comparison, cumulative evidence | software/GPU artifact, comparison report, `correctness.md`, `debugging.md`, `performance.md` | fixed mask 확대, known-bad 허용, scene hash 불일치, lifetime/timing identity 불일치 |

정확한 전체 목록과 identifier는 각 `exercises/<stage>/contract.json`을 정본으로 사용합니다. 위 표는 구현 순서의 축약이며 artifact를 생략할 권한을 주지 않습니다.

## 안전한 누적 구현 순서

1. 새 workspace를 만들고 아직 구현되지 않았다는 negative control부터 확인합니다.

   ```sh
   ./scripts/new-workspace.sh
   python3 exercises/check.py --impl workspace --stage 01-transform-trace --expect not-implemented --gpu off
   ```

2. 한 stage의 `TODO A → B → C`만 구현합니다. 입력 shape·범위·cycle·extent를 allocation이나 GPU 제출 전에 검증하고, 오류를 reference 값으로 대체하지 않습니다.
3. 정상·경계 case와 해당 known-bad mutation이 같은 불변식에서 갈리는지 먼저 확인합니다. stage가 완료되기 전에는 artifact를 쓰지 않거나 새 임시 출력에서만 조사합니다.
4. 모든 필수 artifact가 같은 scene/convention/hash를 가리킬 때만 `--expect pass`로 검사합니다.

   ```sh
   python3 exercises/check.py --impl workspace --stage 01-transform-trace --expect pass --gpu off
   ```

5. 앞 단계의 pass를 회귀시킨 뒤 다음 stage로 이동합니다. 06과 08의 actual GPU 근거는 지원 환경에서 `--gpu required`로 별도 실행하며 lifecycle simulator 결과를 GPU 성공으로 표시하지 않습니다.

GPU known-bad는 기본적으로 unsafe command 제출 전에 계약 검사로 거부합니다. output, capture와 build 생성물은 `build/`·`out/` 또는 새 임시 디렉터리에 두고, 실패 근거와 learner workspace를 정리 도구가 예고 없이 삭제하지 않게 하십시오.
