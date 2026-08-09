#include "cg/artifact.hpp"
#include "cg/contracts.hpp"

#include <array>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

int main() {
  if (cg::parse_stage("01-transform-trace") != cg::Stage::transform_trace) return 1;
  if (cg::parse_stage("08-renderer-capstone") != cg::Stage::renderer_capstone) return 2;
  if (cg::parse_stage("99-unknown")) return 3;
  if (cg::parse_backend("software") != cg::Backend::software) return 4;
  if (cg::parse_backend("lifecycle-sim") != cg::Backend::lifecycle_sim) return 5;
  if (cg::parse_backend("sdl-gpu") != cg::Backend::sdl_gpu) return 6;
  if (cg::corner_marker_rgb().size() != 12) return 7;
  if (cg::expected_scene_id(cg::Stage::transform_trace) != "identity-triangle") return 8;
  if (cg::expected_scene_id(cg::Stage::renderer_capstone) != "shared-textured-triangle-v1") return 9;
  const std::array<std::pair<cg::Stage, std::string_view>, 8> stage_scenes{{
      {cg::Stage::transform_trace, "identity-triangle"},
      {cg::Stage::sampling_color, "corner-marker"},
      {cg::Stage::triangle_coverage, "shared-edge-rectangle"},
      {cg::Stage::perspective_depth_blend, "perspective-checker"},
      {cg::Stage::textured_lit_scene, "textured-lit-scene"},
      {cg::Stage::gpu_first_frame, "shared-textured-triangle-v1"},
      {cg::Stage::frame_debugging, "lifecycle-and-workloads"},
      {cg::Stage::renderer_capstone, "shared-textured-triangle-v1"},
  }};
  for (const auto& [stage, scene] : stage_scenes) {
    if (cg::expected_scene_id(stage) != scene) return 10;
  }

  std::vector<std::string> arguments{
      "cg-render",
      "--stage",
      "01-transform-trace",
      "--scene",
      "wrong-scene",
      "--backend",
      "software",
      "--out",
      "contract-test-output",
  };
  std::vector<char*> argv;
  argv.reserve(arguments.size());
  for (std::string& argument : arguments) argv.push_back(argument.data());
  bool mismatched_scene_rejected = false;
  try {
    static_cast<void>(cg::parse_arguments(static_cast<int>(argv.size()), argv.data()));
  } catch (const std::invalid_argument&) {
    mismatched_scene_rejected = true;
  }
  if (!mismatched_scene_rejected) return 11;

  bool existing_output_rejected = false;
  try {
    cg::validate_new_output_path(std::filesystem::temp_directory_path());
  } catch (const std::invalid_argument&) {
    existing_output_rejected = true;
  }
  if (!existing_output_rejected) return 12;
  std::cout << "CG_CONTRACTS_TEST_OK\n";
  return 0;
}
