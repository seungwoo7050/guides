#include "cg/contracts.hpp"

#include <string_view>

namespace cg {

namespace {

// A stage becomes implemented only after its public evidence is complete.  Until
// then, pending_stage deliberately does not create the output directory: an
// empty or partial artifact set must never look like successful evidence.
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
  return exit_not_implemented;
}

[[nodiscard]] int stage01_transform_trace(const RunOptions& options) {
  static constexpr StageScaffold scaffold{
      Stage::transform_trace,
      "RunOptions + identity/non-uniform/hierarchy/near-clip fixtures",
      "conventions.json + transform cases + rejected.json",
      "column vectors; P*V*M; left-handed +Z; clip before divide; normals use inverse-transpose",
      "matrix-order swap; early perspective divide; scene cycle; singular normal transform"};

  // TODO 01A: define typed model/view/projection and homogeneous point/vector operations.
  // TODO 01B: trace local -> world -> view -> clip and clip the near plane before division.
  // TODO 01C: validate hierarchy/normal inputs, then atomically publish all JSON evidence.
  return pending_stage(options, scaffold);
}

[[nodiscard]] int stage02_sampling_and_color(const RunOptions& options) {
  static constexpr StageScaffold scaffold{
      Stage::sampling_color,
      "corner-marker texels + UV/address/filter/color/alpha policy",
      "samples.json + address/filter/alpha PPMs + report.json",
      "negative UV is defined; bilinear works in linear RGB; alpha convention is explicit; odd mip edges survive",
      "truncate negative UV; interpolate encoded sRGB; mix straight and premultiplied alpha; drop odd mip texels"};

  // TODO 02A: implement clamp/repeat addressing and nearest/bilinear texel selection.
  // TODO 02B: separate sRGB color decode/encode from data textures and alpha compositing.
  // TODO 02C: build odd-extent mip levels, compare known-bad paths, then publish evidence.
  return pending_stage(options, scaffold);
}

}  // namespace

int run_visual_stage(const RunOptions& options) {
  switch (options.stage) {
    case Stage::transform_trace: return stage01_transform_trace(options);
    case Stage::sampling_color: return stage02_sampling_and_color(options);
    default: return exit_contract_failure;
  }
}

}  // namespace cg
