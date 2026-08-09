#include "cg/artifact.hpp"
#include "cg/contracts.hpp"

#include <iostream>

int main() {
  if (cg::parse_stage("01-transform-trace") != cg::Stage::transform_trace) return 1;
  if (cg::parse_stage("08-renderer-capstone") != cg::Stage::renderer_capstone) return 2;
  if (cg::parse_stage("99-unknown")) return 3;
  if (cg::parse_backend("software") != cg::Backend::software) return 4;
  if (cg::parse_backend("lifecycle-sim") != cg::Backend::lifecycle_sim) return 5;
  if (cg::parse_backend("sdl-gpu") != cg::Backend::sdl_gpu) return 6;
  if (cg::corner_marker_rgb().size() != 12) return 7;
  std::cout << "CG_CONTRACTS_TEST_OK\n";
  return 0;
}
