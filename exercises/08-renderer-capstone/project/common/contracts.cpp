#include "cg/contracts.hpp"

#include <charconv>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace cg {

std::optional<Stage> parse_stage(const std::string_view value) {
  static const std::unordered_map<std::string_view, Stage> stages{
      {"01-transform-trace", Stage::transform_trace},
      {"02-sampling-and-color", Stage::sampling_color},
      {"03-triangle-coverage", Stage::triangle_coverage},
      {"04-perspective-depth-blend", Stage::perspective_depth_blend},
      {"05-textured-lit-scene", Stage::textured_lit_scene},
      {"06-gpu-first-frame", Stage::gpu_first_frame},
      {"07-frame-debugging", Stage::frame_debugging},
      {"08-renderer-capstone", Stage::renderer_capstone},
  };
  const auto found = stages.find(value);
  return found == stages.end() ? std::nullopt : std::optional{found->second};
}

std::optional<Backend> parse_backend(const std::string_view value) {
  if (value == "software") return Backend::software;
  if (value == "lifecycle-sim") return Backend::lifecycle_sim;
  if (value == "sdl-gpu") return Backend::sdl_gpu;
  return std::nullopt;
}

std::string_view stage_id(const Stage stage) {
  switch (stage) {
    case Stage::transform_trace: return "01-transform-trace";
    case Stage::sampling_color: return "02-sampling-and-color";
    case Stage::triangle_coverage: return "03-triangle-coverage";
    case Stage::perspective_depth_blend: return "04-perspective-depth-blend";
    case Stage::textured_lit_scene: return "05-textured-lit-scene";
    case Stage::gpu_first_frame: return "06-gpu-first-frame";
    case Stage::frame_debugging: return "07-frame-debugging";
    case Stage::renderer_capstone: return "08-renderer-capstone";
  }
  throw std::logic_error("unknown stage");
}

std::string_view expected_scene_id(const Stage stage) {
  switch (stage) {
    case Stage::transform_trace: return "identity-triangle";
    case Stage::sampling_color: return "corner-marker";
    case Stage::triangle_coverage: return "shared-edge-rectangle";
    case Stage::perspective_depth_blend: return "perspective-checker";
    case Stage::textured_lit_scene: return "textured-lit-scene";
    case Stage::gpu_first_frame: return "shared-textured-triangle-v1";
    case Stage::frame_debugging: return "lifecycle-and-workloads";
    case Stage::renderer_capstone: return "shared-textured-triangle-v1";
  }
  throw std::logic_error("unknown stage");
}

std::string_view backend_id(const Backend backend) {
  switch (backend) {
    case Backend::software: return "software";
    case Backend::lifecycle_sim: return "lifecycle-sim";
    case Backend::sdl_gpu: return "sdl-gpu";
  }
  throw std::logic_error("unknown backend");
}

RunOptions parse_arguments(const int argc, char** argv) {
  RunOptions options;
  bool have_stage = false;
  bool have_scene = false;
  bool have_output = false;
  for (int index = 1; index < argc; ++index) {
    const std::string_view name = argv[index];
    auto take = [&]() -> std::string_view {
      if (++index >= argc) throw std::invalid_argument(std::string(name) + " requires a value");
      return argv[index];
    };
    if (name == "--stage") {
      const auto parsed = parse_stage(take());
      if (!parsed) throw std::invalid_argument("unknown --stage");
      options.stage = *parsed;
      have_stage = true;
    } else if (name == "--scene") {
      options.scene = take();
      have_scene = !options.scene.empty();
    } else if (name == "--backend") {
      const auto parsed = parse_backend(take());
      if (!parsed) throw std::invalid_argument("unknown --backend");
      options.backend = *parsed;
    } else if (name == "--out") {
      options.output = take();
      have_output = !options.output.empty();
    } else if (name == "--frames") {
      const auto text = take();
      const char* begin = text.data();
      const char* end = begin + text.size();
      const auto result = std::from_chars(begin, end, options.frames);
      if (result.ec != std::errc{} || result.ptr != end || options.frames < 1 || options.frames > 10000) {
        throw std::invalid_argument("--frames must be an integer in 1..10000");
      }
    } else if (name == "--mutation") {
      options.mutation = std::string(take());
    } else {
      throw std::invalid_argument("unknown argument: " + std::string(name));
    }
  }
  if (!have_stage || !have_scene || !have_output) {
    throw std::invalid_argument("--stage, --scene, and --out are required");
  }
  if (options.scene != expected_scene_id(options.stage)) {
    throw std::invalid_argument(
        "--scene must be " + std::string(expected_scene_id(options.stage)) +
        " for " + std::string(stage_id(options.stage)));
  }
  if (options.output == options.output.root_path()) {
    throw std::invalid_argument("--out may not be a filesystem root");
  }
  return options;
}

}  // namespace cg
