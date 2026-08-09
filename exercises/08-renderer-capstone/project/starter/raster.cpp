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
  // Do not call ensure_output_directory until every artifact below can be
  // produced and validated as one stage result.
  return exit_not_implemented;
}

[[nodiscard]] int stage03_triangle_coverage(const RunOptions& options) {
  static constexpr StageScaffold scaffold{
      Stage::triangle_coverage,
      "clip-space triangles + viewport/scissor + winding/cull policy",
      "coverage/primitive-id images + setup-trace.json + counts/mutation reports",
      "pixel-center samples; top-left shared-edge ownership; clamped signed bounds; degenerate reject",
      "all edges inclusive/exclusive; truncated negative bounds; stale winding after Y flip; zero-area divide"};

  // TODO 03A: set up oriented edge equations and a conservative signed bounding box.
  // TODO 03B: apply culling, scissor, pixel-center and top-left equality exactly once.
  // TODO 03C: emit ownership/count traces only after shared-edge and degenerate checks pass.
  return pending_stage(options, scaffold);
}

[[nodiscard]] int stage04_perspective_depth_blend(const RunOptions& options) {
  static constexpr StageScaffold scaffold{
      Stage::perspective_depth_blend,
      "covered samples + clip w/attributes + depth/cull/blend state",
      "perspective/affine images + depth/primitive-id + pixel traces + report.json",
      "attributes use reciprocal-w; depth stays [0,1]; opaque depth writes precede linear-RGB blending",
      "affine UV; reversed depth without projection change; transparent depth write; encoded-sRGB blend"};

  // TODO 04A: interpolate reciprocal-w and reconstruct UV/color/depth at each covered sample.
  // TODO 04B: make depth compare/write and straight/premultiplied blend state explicit.
  // TODO 04C: preserve first-failing pixel traces and known-bad images before publishing the report.
  return pending_stage(options, scaffold);
}

[[nodiscard]] int stage05_textured_lit_scene(const RunOptions& options) {
  static constexpr StageScaffold scaffold{
      Stage::textured_lit_scene,
      "validated SceneSnapshot mesh/material/texture hierarchy + camera",
      "final/base-color/normal/ndotl/mip/object-id images + asset/culling/frame JSON",
      "indices/layout/cycles validated; normals inverse-transposed; data maps stay linear; bounds and LOD are stable",
      "invalid index; scene cycle; singular normal matrix; position-only seam merge; stale bounds; LOD oscillation"};

  // TODO 05A: normalize and reject non-renderable mesh, hierarchy, material and texture inputs.
  // TODO 05B: combine sampling, tangent/normal handling, simple lighting, culling and LOD.
  // TODO 05C: publish color plus debug attachments with work/rejection counts from the same frame.
  return pending_stage(options, scaffold);
}

}  // namespace

int run_raster_stage(const RunOptions& options) {
  switch (options.stage) {
    case Stage::triangle_coverage: return stage03_triangle_coverage(options);
    case Stage::perspective_depth_blend: return stage04_perspective_depth_blend(options);
    case Stage::textured_lit_scene: return stage05_textured_lit_scene(options);
    default: return exit_contract_failure;
  }
}

}  // namespace cg
