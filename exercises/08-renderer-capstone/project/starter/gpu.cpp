#include "cg/contracts.hpp"

#include <string_view>

namespace cg {

namespace {

struct StageScaffold {
  Stage stage;
  std::string_view inputs;
  std::string_view outputs;
  std::string_view invariants;
  std::string_view representative_failures;
};

[[nodiscard]] int pending_stage(
    const RunOptions& options,
    const StageScaffold& scaffold) noexcept {
  if (options.stage != scaffold.stage) return exit_contract_failure;
  // Pending GPU stages submit no unsafe commands and manufacture no screenshot,
  // trace, timing or capture evidence.  The checker must observe exit 3.
  return exit_not_implemented;
}

[[nodiscard]] int stage06_gpu_first_frame(const RunOptions& options) {
  static constexpr StageScaffold scaffold{
      Stage::gpu_first_frame,
      "shared SceneSnapshot + backend/profile + shader/layout/attachment manifest",
      "environment/shader/resource/pipeline JSON + frame/resize traces + readback + validation.log",
      "layout/bindings/formats agree; completion precedes readback/reuse; resize changes generation; zero extent skips",
      "wrong stride/binding; in-flight overwrite; early staging destroy/readback; depth mismatch; stale attachment"};

  // TODO 06A: create backend, tracked shader, vertex/index/uniform resources and color/depth pipeline.
  // TODO 06B: record one offscreen pass, fence it, then map readback and retire completed generations.
  // TODO 06C: handle resize/zero extent and publish validation plus screenshot only after completion.
  return pending_stage(options, scaffold);
}

[[nodiscard]] int stage07_frame_debugging(const RunOptions& options) {
  static constexpr StageScaffold scaffold{
      Stage::frame_debugging,
      "six fixed failure cases + frame-slot/generation events + three workloads",
      "case reports/traces/logs + before-after images/diffs + capture metadata + timing-report.json",
      "first divergent state is named; slot reuse/retire follows completion; warm-up excluded; median/p95 keep hashes/environment",
      "matrix/layout/binding/depth/color/blend mismatch; slot overwrite; stale resize target; readback before completion"};

  // TODO 07A: diagnose structure -> coverage -> depth -> attribute -> linear color -> sRGB.
  // TODO 07B: simulate and trace frame slots, generation retirement, resize and completion ordering.
  // TODO 07C: warm up, collect 30 real samples per workload, then report median/p95 without time gates.
  return pending_stage(options, scaffold);
}

[[nodiscard]] int stage08_renderer_capstone(const RunOptions& options) {
  static constexpr StageScaffold scaffold{
      Stage::renderer_capstone,
      "one shared SceneSnapshot rendered by software and an actually supported GPU backend",
      "software/gpu artifacts + ordered comparisons + correctness/debugging/performance reports",
      "scene hash matches; fixed predeclared edge mask/tolerance; known-bad stays rejected; lifetime/timing identities agree",
      "matrix/clip/top-left/UV/sRGB/depth/alpha/layout mutation; frame-slot overwrite; stale resize attachment"};

  // TODO 08A: run CPU and GPU paths from the identical validated snapshot and conventions.
  // TODO 08B: compare structure, coverage, depth, attribute, linear color and sRGB in that order.
  // TODO 08C: combine mutation, lifecycle and measured workload evidence; document manual GPU limits.
  return pending_stage(options, scaffold);
}

}  // namespace

int run_gpu_stage(const RunOptions& options) {
  switch (options.stage) {
    case Stage::gpu_first_frame: return stage06_gpu_first_frame(options);
    case Stage::frame_debugging: return stage07_frame_debugging(options);
    case Stage::renderer_capstone: return stage08_renderer_capstone(options);
    default: return exit_contract_failure;
  }
}

}  // namespace cg
