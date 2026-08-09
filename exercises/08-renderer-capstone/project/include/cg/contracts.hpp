#pragma once

#include <filesystem>
#include <optional>
#include <string>
#include <string_view>

namespace cg {

enum class Stage {
  transform_trace = 1,
  sampling_color = 2,
  triangle_coverage = 3,
  perspective_depth_blend = 4,
  textured_lit_scene = 5,
  gpu_first_frame = 6,
  frame_debugging = 7,
  renderer_capstone = 8,
};

enum class Backend { software, lifecycle_sim, sdl_gpu };

struct RunOptions {
  Stage stage{};
  Backend backend{Backend::software};
  std::string scene;
  std::filesystem::path output;
  int frames{1};
  std::optional<std::string> mutation;
};

inline constexpr int exit_ok = 0;
inline constexpr int exit_usage = 2;
inline constexpr int exit_not_implemented = 3;
inline constexpr int exit_contract_failure = 4;
inline constexpr int exit_unsupported = 5;

std::optional<Stage> parse_stage(std::string_view value);
std::optional<Backend> parse_backend(std::string_view value);
std::string_view stage_id(Stage stage);
std::string_view backend_id(Backend backend);
RunOptions parse_arguments(int argc, char** argv);

int run_visual_stage(const RunOptions& options);
int run_raster_stage(const RunOptions& options);
int run_gpu_stage(const RunOptions& options);

}  // namespace cg
