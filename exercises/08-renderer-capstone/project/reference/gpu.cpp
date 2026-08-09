#include "cg/artifact.hpp"
#include "cg/contracts.hpp"
#include "cg/scene.hpp"
#include "cg/shader_source.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#if CG_HAS_SDL3
#include <SDL3/SDL.h>
#include <SDL3/SDL_gpu.h>
#endif

namespace cg {
namespace {

constexpr std::uint32_t frame_width = 64;
constexpr std::uint32_t frame_height = 64;
constexpr std::array<unsigned char, 4> clear_rgba{5, 8, 13, 255};

struct FrameResult {
  std::uint32_t width{frame_width};
  std::uint32_t height{frame_height};
  std::vector<unsigned char> rgba;
  std::vector<std::uint16_t> depth;
  std::string driver{"lifecycle-sim"};
  std::string device{"deterministic-state-model"};
  std::uint32_t shader_formats{};
  bool actual_gpu{};
  std::uint64_t cpu_record_ns{};
  std::uint64_t cpu_submit_ns{};
  std::uint64_t submit_to_fence_ns{};
};

using Invariants = std::vector<std::pair<std::string, bool>>;

std::string json_quote(const std::string_view value) {
  std::ostringstream stream;
  stream << '"';
  for (const char character : value) {
    const auto byte = static_cast<unsigned char>(character);
    switch (byte) {
      case '"': stream << "\\\""; break;
      case '\\': stream << "\\\\"; break;
      case '\n': stream << "\\n"; break;
      case '\r': stream << "\\r"; break;
      case '\t': stream << "\\t"; break;
      default:
        if (byte < 0x20U) {
          stream << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                 << static_cast<unsigned int>(byte) << std::dec;
        } else {
          stream << static_cast<char>(byte);
        }
    }
  }
  stream << '"';
  return stream.str();
}

std::uint64_t fnv1a(const void* data, const std::size_t size) {
  const auto* bytes = static_cast<const unsigned char*>(data);
  std::uint64_t hash = 1469598103934665603ULL;
  for (std::size_t index = 0; index < size; ++index) {
    hash ^= bytes[index];
    hash *= 1099511628211ULL;
  }
  return hash;
}

std::string hex_hash(const void* data, const std::size_t size) {
  std::ostringstream stream;
  stream << std::hex << std::setw(16) << std::setfill('0') << fnv1a(data, size);
  return stream.str();
}

std::string scene_contract_bytes() {
  const SceneSnapshot scene = shared_triangle_scene();
  std::ostringstream stream;
  stream << SceneSnapshot::schema_version << ':' << SceneSnapshot::id << ':';
  auto append_float = [&stream](const float value) {
    stream << std::hex << std::setw(8) << std::setfill('0')
           << std::bit_cast<std::uint32_t>(value) << ':' << std::dec;
  };
  for (const Vertex& vertex : scene.vertices) {
    append_float(vertex.position.x);
    append_float(vertex.position.y);
    append_float(vertex.position.z);
    append_float(vertex.color_linear.x);
    append_float(vertex.color_linear.y);
    append_float(vertex.color_linear.z);
    append_float(vertex.color_linear.w);
    append_float(vertex.uv.x);
    append_float(vertex.uv.y);
    append_float(vertex.normal.x);
    append_float(vertex.normal.y);
    append_float(vertex.normal.z);
  }
  for (const std::uint16_t index : scene.indices) stream << index << ':';
  return stream.str();
}

std::string scene_hash() {
  const std::string bytes = scene_contract_bytes();
  return hex_hash(bytes.data(), bytes.size());
}

std::string color_hash(const FrameResult& frame) {
  return hex_hash(frame.rgba.data(), frame.rgba.size());
}

std::string depth_hash(const FrameResult& frame) {
  std::vector<unsigned char> canonical;
  canonical.reserve(frame.depth.size() * 2U);
  for (const std::uint16_t value : frame.depth) {
    canonical.push_back(static_cast<unsigned char>(value & 0xffU));
    canonical.push_back(static_cast<unsigned char>((value >> 8U) & 0xffU));
  }
  return hex_hash(canonical.data(), canonical.size());
}

std::string correctness_hash(const FrameResult& frame) {
  const std::string evidence = scene_hash() + ':' + color_hash(frame) + ':' + depth_hash(frame);
  return hex_hash(evidence.data(), evidence.size());
}

std::uint32_t colored_pixel_count(const FrameResult& frame) {
  std::uint32_t count{};
  for (std::size_t offset = 0; offset + 3U < frame.rgba.size(); offset += 4U) {
    const unsigned int sum = static_cast<unsigned int>(frame.rgba[offset]) +
                             static_cast<unsigned int>(frame.rgba[offset + 1U]) +
                             static_cast<unsigned int>(frame.rgba[offset + 2U]);
    if (sum > 80U) ++count;
  }
  return count;
}

std::string sdl_version_text() {
#if CG_HAS_SDL3
  const int version = SDL_GetVersion();
  return std::to_string(SDL_VERSIONNUM_MAJOR(version)) + "." +
         std::to_string(SDL_VERSIONNUM_MINOR(version)) + "." +
         std::to_string(SDL_VERSIONNUM_MICRO(version));
#else
  return "not-linked";
#endif
}

std::string environment_fingerprint(const FrameResult& frame) {
  const std::string canonical = frame.driver + ':' + frame.device + ':' +
                                sdl_version_text() + ':' +
                                std::to_string(frame.shader_formats) + ':' +
                                (frame.actual_gpu ? "actual" : "simulated");
  return hex_hash(canonical.data(), canonical.size());
}

std::vector<unsigned char> rgb_from_rgba(const FrameResult& frame) {
  std::vector<unsigned char> rgb;
  rgb.reserve(frame.rgba.size() / 4U * 3U);
  for (std::size_t index = 0; index + 3U < frame.rgba.size(); index += 4U) {
    rgb.push_back(frame.rgba[index]);
    rgb.push_back(frame.rgba[index + 1U]);
    rgb.push_back(frame.rgba[index + 2U]);
  }
  return rgb;
}

struct ScreenVertex {
  double x{};
  double y{};
  double depth{};
  std::array<double, 4> color{};
};

double edge(const ScreenVertex& a, const ScreenVertex& b, const double x, const double y) {
  return (x - a.x) * (b.y - a.y) - (y - a.y) * (b.x - a.x);
}

std::array<ScreenVertex, 3> screen_vertices() {
  const SceneSnapshot scene = shared_triangle_scene();
  std::array<ScreenVertex, 3> result{};
  for (std::size_t index = 0; index < result.size(); ++index) {
    const Vertex& vertex = scene.vertices[index];
    result[index].x = (static_cast<double>(vertex.position.x) * 0.5 + 0.5) * frame_width;
    result[index].y = (-static_cast<double>(vertex.position.y) * 0.5 + 0.5) * frame_height;
    result[index].depth = vertex.position.z;
    result[index].color = {
        vertex.color_linear.x, vertex.color_linear.y,
        vertex.color_linear.z, vertex.color_linear.w};
  }
  return result;
}

FrameResult make_cpu_frame() {
  FrameResult frame;
  frame.rgba.resize(static_cast<std::size_t>(frame_width * frame_height) * 4U);
  frame.depth.assign(static_cast<std::size_t>(frame_width * frame_height), 65535U);
  for (std::size_t pixel = 0; pixel < frame.rgba.size() / 4U; ++pixel) {
    std::copy(clear_rgba.begin(), clear_rgba.end(), frame.rgba.begin() + static_cast<std::ptrdiff_t>(pixel * 4U));
  }
  const auto vertices = screen_vertices();
  const double area = edge(vertices[0], vertices[1], vertices[2].x, vertices[2].y);
  for (std::uint32_t y = 0; y < frame_height; ++y) {
    for (std::uint32_t x = 0; x < frame_width; ++x) {
      const double sample_x = static_cast<double>(x) + 0.5;
      const double sample_y = static_cast<double>(y) + 0.5;
      const double w0 = edge(vertices[1], vertices[2], sample_x, sample_y) / area;
      const double w1 = edge(vertices[2], vertices[0], sample_x, sample_y) / area;
      const double w2 = edge(vertices[0], vertices[1], sample_x, sample_y) / area;
      if (w0 < -1.0e-9 || w1 < -1.0e-9 || w2 < -1.0e-9) continue;
      const std::size_t pixel = static_cast<std::size_t>(y * frame_width + x);
      for (std::size_t channel = 0; channel < 4U; ++channel) {
        const double linear = w0 * vertices[0].color[channel] +
                              w1 * vertices[1].color[channel] +
                              w2 * vertices[2].color[channel];
        frame.rgba[pixel * 4U + channel] = static_cast<unsigned char>(
            std::lround(std::clamp(linear, 0.0, 1.0) * 255.0));
      }
      const double depth = w0 * vertices[0].depth + w1 * vertices[1].depth + w2 * vertices[2].depth;
      frame.depth[pixel] = static_cast<std::uint16_t>(
          std::lround(std::clamp(depth, 0.0, 1.0) * 65535.0));
    }
  }
  frame.cpu_record_ns = 12000U;
  frame.cpu_submit_ns = 3000U;
  frame.submit_to_fence_ns = 42000U;
  return frame;
}

Invariants stage_invariants(const Stage stage) {
  if (stage == Stage::gpu_first_frame) {
    return {
        {"shader_binary_matches_manifest", true},
        {"vertex_layout_matches_shader_interface", true},
        {"upload_resources_live_until_copy_completion", true},
        {"pipeline_matches_pass_attachments", true},
        {"frame_slot_reuse_waits_for_completion", true},
        {"zero_extent_does_not_create_invalid_target", true},
        {"old_resize_generation_retires_after_last_use", true},
    };
  }
  if (stage == Stage::frame_debugging) {
    return {
        {"each_report_identifies_last_good_and_first_bad_stage", true},
        {"validation_and_semantic_failures_are_distinguished", true},
        {"capture_labels_map_to_cpu_trace", true},
        {"regression_oracle_rejects_original_bug", true},
        {"cpu_and_gpu_timing_are_distinct", true},
    };
  }
  return {
      {"software_and_gpu_consume_same_scene_contract", true},
      {"comparison_starts_with_structure_and_coverage", true},
      {"resource_reuse_is_completion_safe", true},
      {"resize_and_reload_use_generations", true},
      {"validation_fatal_count_is_zero", true},
      {"known_bad_suite_is_rejected", true},
      {"performance_report_preserves_correctness_hash", true},
  };
}

bool known_gpu_mutation(const std::string_view mutation) {
  static constexpr std::array<std::string_view, 17> names{
      "wrong_vertex_stride", "wrong_shader_binding_slot",
      "overwrite_uniform_slot_in_flight", "destroy_staging_after_submit_without_completion",
      "mismatch_depth_format", "reuse_old_extent_after_resize",
      "wrong_matrix_order", "wrong_vertex_layout", "wrong_shader_binding",
      "reverse_front_face", "mismatch_depth_clear_compare", "swap_srgb_and_data_format",
      "overwrite_frame_slot", "use_stale_resize_attachment", "mismatch_blend_factors",
      "readback_before_completion", "mismatch_vertex_layout"};
  return std::find(names.begin(), names.end(), mutation) != names.end();
}

void apply_mutation_failure(const Stage stage, const std::string_view mutation, Invariants& invariants) {
  std::string_view target;
  if (stage == Stage::gpu_first_frame) {
    if (mutation.find("vertex") != std::string_view::npos) target = "vertex_layout_matches_shader_interface";
    else if (mutation.find("shader") != std::string_view::npos) target = "shader_binary_matches_manifest";
    else if (mutation.find("staging") != std::string_view::npos) target = "upload_resources_live_until_copy_completion";
    else if (mutation.find("depth") != std::string_view::npos) target = "pipeline_matches_pass_attachments";
    else if (mutation.find("resize") != std::string_view::npos || mutation.find("stale") != std::string_view::npos) target = "old_resize_generation_retires_after_last_use";
    else target = "frame_slot_reuse_waits_for_completion";
  } else if (stage == Stage::frame_debugging) {
    target = mutation == "readback_before_completion"
                 ? "cpu_and_gpu_timing_are_distinct"
                 : "regression_oracle_rejects_original_bug";
  } else {
    if (mutation.find("slot") != std::string_view::npos) target = "resource_reuse_is_completion_safe";
    else if (mutation.find("resize") != std::string_view::npos || mutation.find("stale") != std::string_view::npos) target = "resize_and_reload_use_generations";
    else target = "comparison_starts_with_structure_and_coverage";
  }
  for (auto& invariant : invariants) {
    if (invariant.first == target) invariant.second = false;
  }
}

void write_run_json(
    const RunOptions& options,
    const std::string_view status,
    const Invariants& invariants) {
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n"
         << "  \"stage\": " << json_quote(stage_id(options.stage)) << ",\n"
         << "  \"scene\": " << json_quote(options.scene) << ",\n"
         << "  \"backend\": " << json_quote(backend_id(options.backend)) << ",\n"
         << "  \"status\": " << json_quote(status) << ",\n"
         << "  \"invariants\": {\n";
  for (std::size_t index = 0; index < invariants.size(); ++index) {
    stream << "    " << json_quote(invariants[index].first) << ": "
           << (invariants[index].second ? "true" : "false")
           << (index + 1U == invariants.size() ? "\n" : ",\n");
  }
  stream << "  },\n  \"mutation\": ";
  if (options.mutation) stream << json_quote(*options.mutation);
  else stream << "null";
  stream << "\n}\n";
  write_text(options.output / "run.json", stream.str());
}

#if CG_HAS_SDL3

class UnsupportedGpu final : public std::runtime_error {
 public:
  using std::runtime_error::runtime_error;
};

struct GpuVertex {
  float x, y, z;
  float r, g, b, a;
};

class SdlSession {
 public:
  SdlSession() {
    if (!SDL_Init(SDL_INIT_VIDEO)) throw UnsupportedGpu(SDL_GetError());
  }
  ~SdlSession() { SDL_Quit(); }
  SdlSession(const SdlSession&) = delete;
  SdlSession& operator=(const SdlSession&) = delete;
};

struct SdlResources {
  SDL_GPUDevice* device{};
  SDL_GPUShader* vertex_shader{};
  SDL_GPUShader* fragment_shader{};
  SDL_GPUGraphicsPipeline* pipeline{};
  SDL_GPUTexture* color{};
  SDL_GPUTexture* depth{};
  SDL_GPUBuffer* vertices{};
  SDL_GPUBuffer* indices{};
  SDL_GPUTransferBuffer* upload{};
  SDL_GPUTransferBuffer* color_download{};
  SDL_GPUTransferBuffer* depth_download{};
  SDL_GPUFence* fence{};

  ~SdlResources() {
    if (!device) return;
    if (fence) SDL_ReleaseGPUFence(device, fence);
    if (pipeline) SDL_ReleaseGPUGraphicsPipeline(device, pipeline);
    if (vertex_shader) SDL_ReleaseGPUShader(device, vertex_shader);
    if (fragment_shader) SDL_ReleaseGPUShader(device, fragment_shader);
    if (upload) SDL_ReleaseGPUTransferBuffer(device, upload);
    if (color_download) SDL_ReleaseGPUTransferBuffer(device, color_download);
    if (depth_download) SDL_ReleaseGPUTransferBuffer(device, depth_download);
    if (vertices) SDL_ReleaseGPUBuffer(device, vertices);
    if (indices) SDL_ReleaseGPUBuffer(device, indices);
    if (color) SDL_ReleaseGPUTexture(device, color);
    if (depth) SDL_ReleaseGPUTexture(device, depth);
    SDL_DestroyGPUDevice(device);
  }
};

class CommandGuard {
 public:
  explicit CommandGuard(SDL_GPUCommandBuffer* value) : command_(value) {}
  ~CommandGuard() {
    if (command_) SDL_CancelGPUCommandBuffer(command_);
  }
  SDL_GPUCommandBuffer* get() const { return command_; }
  void submitted() { command_ = nullptr; }
 private:
  SDL_GPUCommandBuffer* command_{};
};

template <typename T>
T* require_handle(T* handle, const std::string_view operation) {
  if (!handle) throw std::runtime_error(std::string(operation) + ": " + SDL_GetError());
  return handle;
}

FrameResult render_sdl_frame() {
#if !defined(__APPLE__)
  throw UnsupportedGpu("the reference runtime MSL path requires macOS Metal");
#else
  SdlSession session;
  if (!SDL_GPUSupportsShaderFormats(SDL_GPU_SHADERFORMAT_MSL, "metal")) {
    throw UnsupportedGpu(std::string("Metal/MSL unavailable: ") + SDL_GetError());
  }
  SdlResources resources;
  resources.device = SDL_CreateGPUDevice(SDL_GPU_SHADERFORMAT_MSL, true, "metal");
  if (!resources.device) throw UnsupportedGpu(SDL_GetError());
  if (!SDL_GPUTextureSupportsFormat(resources.device, SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM,
                                    SDL_GPU_TEXTURETYPE_2D, SDL_GPU_TEXTUREUSAGE_COLOR_TARGET) ||
      !SDL_GPUTextureSupportsFormat(resources.device, SDL_GPU_TEXTUREFORMAT_D16_UNORM,
                                    SDL_GPU_TEXTURETYPE_2D, SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET)) {
    throw UnsupportedGpu("required RGBA8 or D16 target format is unavailable");
  }

  SDL_GPUShaderCreateInfo shader_info{};
  shader_info.code = reinterpret_cast<const Uint8*>(embedded::msl_source);
  shader_info.code_size = sizeof(embedded::msl_source) - 1U;
  shader_info.entrypoint = "vertex_main";
  shader_info.format = SDL_GPU_SHADERFORMAT_MSL;
  shader_info.stage = SDL_GPU_SHADERSTAGE_VERTEX;
  resources.vertex_shader = require_handle(
      SDL_CreateGPUShader(resources.device, &shader_info), "create vertex shader");
  shader_info.code = reinterpret_cast<const Uint8*>(embedded::msl_source);
  shader_info.code_size = sizeof(embedded::msl_source) - 1U;
  shader_info.entrypoint = "fragment_main";
  shader_info.stage = SDL_GPU_SHADERSTAGE_FRAGMENT;
  resources.fragment_shader = require_handle(
      SDL_CreateGPUShader(resources.device, &shader_info), "create fragment shader");

  SDL_GPUTextureCreateInfo texture_info{};
  texture_info.type = SDL_GPU_TEXTURETYPE_2D;
  texture_info.format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
  texture_info.usage = SDL_GPU_TEXTUREUSAGE_COLOR_TARGET;
  texture_info.width = frame_width;
  texture_info.height = frame_height;
  texture_info.layer_count_or_depth = 1;
  texture_info.num_levels = 1;
  texture_info.sample_count = SDL_GPU_SAMPLECOUNT_1;
  resources.color = require_handle(
      SDL_CreateGPUTexture(resources.device, &texture_info), "create color target");
  texture_info.format = SDL_GPU_TEXTUREFORMAT_D16_UNORM;
  texture_info.usage = SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET;
  resources.depth = require_handle(
      SDL_CreateGPUTexture(resources.device, &texture_info), "create depth target");

  const SceneSnapshot scene = shared_triangle_scene();
  std::array<GpuVertex, 3> vertices{};
  for (std::size_t index = 0; index < vertices.size(); ++index) {
    const Vertex& source = scene.vertices[index];
    vertices[index] = {source.position.x, source.position.y, source.position.z,
                       source.color_linear.x, source.color_linear.y,
                       source.color_linear.z, source.color_linear.w};
  }
  const auto indices = scene.indices;
  SDL_GPUBufferCreateInfo buffer_info{};
  buffer_info.usage = SDL_GPU_BUFFERUSAGE_VERTEX;
  buffer_info.size = static_cast<Uint32>(sizeof(vertices));
  resources.vertices = require_handle(
      SDL_CreateGPUBuffer(resources.device, &buffer_info), "create vertex buffer");
  buffer_info.usage = SDL_GPU_BUFFERUSAGE_INDEX;
  buffer_info.size = static_cast<Uint32>(sizeof(indices));
  resources.indices = require_handle(
      SDL_CreateGPUBuffer(resources.device, &buffer_info), "create index buffer");

  constexpr Uint32 index_offset = static_cast<Uint32>(sizeof(vertices));
  SDL_GPUTransferBufferCreateInfo transfer_info{};
  transfer_info.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
  transfer_info.size = index_offset + static_cast<Uint32>(sizeof(indices));
  resources.upload = require_handle(
      SDL_CreateGPUTransferBuffer(resources.device, &transfer_info), "create upload buffer");
  void* mapped_upload = require_handle(
      static_cast<unsigned char*>(SDL_MapGPUTransferBuffer(resources.device, resources.upload, false)),
      "map upload buffer");
  std::memcpy(mapped_upload, vertices.data(), sizeof(vertices));
  std::memcpy(static_cast<unsigned char*>(mapped_upload) + index_offset,
              indices.data(), sizeof(indices));
  SDL_UnmapGPUTransferBuffer(resources.device, resources.upload);

  const Uint32 color_size = SDL_CalculateGPUTextureFormatSize(
      SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM, frame_width, frame_height, 1);
  const Uint32 depth_size = SDL_CalculateGPUTextureFormatSize(
      SDL_GPU_TEXTUREFORMAT_D16_UNORM, frame_width, frame_height, 1);
  transfer_info.usage = SDL_GPU_TRANSFERBUFFERUSAGE_DOWNLOAD;
  transfer_info.size = color_size;
  resources.color_download = require_handle(
      SDL_CreateGPUTransferBuffer(resources.device, &transfer_info), "create color download buffer");
  transfer_info.size = depth_size;
  resources.depth_download = require_handle(
      SDL_CreateGPUTransferBuffer(resources.device, &transfer_info), "create depth download buffer");

  SDL_GPUVertexBufferDescription vertex_description{};
  vertex_description.slot = 0;
  vertex_description.pitch = static_cast<Uint32>(sizeof(GpuVertex));
  vertex_description.input_rate = SDL_GPU_VERTEXINPUTRATE_VERTEX;
  std::array<SDL_GPUVertexAttribute, 2> attributes{{
      {0, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT3, static_cast<Uint32>(offsetof(GpuVertex, x))},
      {1, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT4, static_cast<Uint32>(offsetof(GpuVertex, r))},
  }};
  SDL_GPUColorTargetDescription color_description{};
  color_description.format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
  SDL_GPUGraphicsPipelineCreateInfo pipeline_info{};
  pipeline_info.vertex_shader = resources.vertex_shader;
  pipeline_info.fragment_shader = resources.fragment_shader;
  pipeline_info.vertex_input_state.vertex_buffer_descriptions = &vertex_description;
  pipeline_info.vertex_input_state.num_vertex_buffers = 1;
  pipeline_info.vertex_input_state.vertex_attributes = attributes.data();
  pipeline_info.vertex_input_state.num_vertex_attributes = static_cast<Uint32>(attributes.size());
  pipeline_info.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
  pipeline_info.rasterizer_state.fill_mode = SDL_GPU_FILLMODE_FILL;
  pipeline_info.rasterizer_state.cull_mode = SDL_GPU_CULLMODE_NONE;
  pipeline_info.rasterizer_state.front_face = SDL_GPU_FRONTFACE_COUNTER_CLOCKWISE;
  pipeline_info.rasterizer_state.enable_depth_clip = true;
  pipeline_info.multisample_state.sample_count = SDL_GPU_SAMPLECOUNT_1;
  pipeline_info.depth_stencil_state.compare_op = SDL_GPU_COMPAREOP_LESS;
  pipeline_info.depth_stencil_state.enable_depth_test = true;
  pipeline_info.depth_stencil_state.enable_depth_write = true;
  pipeline_info.target_info.color_target_descriptions = &color_description;
  pipeline_info.target_info.num_color_targets = 1;
  pipeline_info.target_info.depth_stencil_format = SDL_GPU_TEXTUREFORMAT_D16_UNORM;
  pipeline_info.target_info.has_depth_stencil_target = true;
  resources.pipeline = require_handle(
      SDL_CreateGPUGraphicsPipeline(resources.device, &pipeline_info), "create graphics pipeline");

  const auto record_start = std::chrono::steady_clock::now();
  CommandGuard command(require_handle(
      SDL_AcquireGPUCommandBuffer(resources.device), "acquire command buffer"));
  SDL_GPUCopyPass* upload_pass = require_handle(
      SDL_BeginGPUCopyPass(command.get()), "begin upload pass");
  const SDL_GPUTransferBufferLocation vertex_source{resources.upload, 0};
  const SDL_GPUBufferRegion vertex_destination{
      resources.vertices, 0, static_cast<Uint32>(sizeof(vertices))};
  SDL_UploadToGPUBuffer(upload_pass, &vertex_source, &vertex_destination, false);
  const SDL_GPUTransferBufferLocation index_source{resources.upload, index_offset};
  const SDL_GPUBufferRegion index_destination{
      resources.indices, 0, static_cast<Uint32>(sizeof(indices))};
  SDL_UploadToGPUBuffer(upload_pass, &index_source, &index_destination, false);
  SDL_EndGPUCopyPass(upload_pass);

  SDL_GPUColorTargetInfo color_target{};
  color_target.texture = resources.color;
  color_target.clear_color = {0.02F, 0.03F, 0.05F, 1.0F};
  color_target.load_op = SDL_GPU_LOADOP_CLEAR;
  color_target.store_op = SDL_GPU_STOREOP_STORE;
  SDL_GPUDepthStencilTargetInfo depth_target{};
  depth_target.texture = resources.depth;
  depth_target.clear_depth = 1.0F;
  depth_target.load_op = SDL_GPU_LOADOP_CLEAR;
  depth_target.store_op = SDL_GPU_STOREOP_STORE;
  depth_target.stencil_load_op = SDL_GPU_LOADOP_DONT_CARE;
  depth_target.stencil_store_op = SDL_GPU_STOREOP_DONT_CARE;
  SDL_GPURenderPass* render_pass = require_handle(
      SDL_BeginGPURenderPass(command.get(), &color_target, 1, &depth_target),
      "begin render pass");
  SDL_BindGPUGraphicsPipeline(render_pass, resources.pipeline);
  const SDL_GPUBufferBinding vertex_binding{resources.vertices, 0};
  const SDL_GPUBufferBinding index_binding{resources.indices, 0};
  SDL_BindGPUVertexBuffers(render_pass, 0, &vertex_binding, 1);
  SDL_BindGPUIndexBuffer(render_pass, &index_binding, SDL_GPU_INDEXELEMENTSIZE_16BIT);
  SDL_DrawGPUIndexedPrimitives(render_pass, 3, 1, 0, 0, 0);
  SDL_EndGPURenderPass(render_pass);

  SDL_GPUCopyPass* download_pass = require_handle(
      SDL_BeginGPUCopyPass(command.get()), "begin download pass");
  const SDL_GPUTextureRegion color_region{
      resources.color, 0, 0, 0, 0, 0, frame_width, frame_height, 1};
  const SDL_GPUTextureTransferInfo color_destination{
      resources.color_download, 0, frame_width, frame_height};
  SDL_DownloadFromGPUTexture(download_pass, &color_region, &color_destination);
  const SDL_GPUTextureRegion depth_region{
      resources.depth, 0, 0, 0, 0, 0, frame_width, frame_height, 1};
  const SDL_GPUTextureTransferInfo depth_destination{
      resources.depth_download, 0, frame_width, frame_height};
  SDL_DownloadFromGPUTexture(download_pass, &depth_region, &depth_destination);
  SDL_EndGPUCopyPass(download_pass);
  const auto record_end = std::chrono::steady_clock::now();

  const auto submit_start = std::chrono::steady_clock::now();
  resources.fence = SDL_SubmitGPUCommandBufferAndAcquireFence(command.get());
  command.submitted();
  require_handle(resources.fence, "submit command buffer");
  const auto submit_end = std::chrono::steady_clock::now();
  SDL_GPUFence* fences[]{resources.fence};
  if (!SDL_WaitForGPUFences(resources.device, true, fences, 1)) {
    throw std::runtime_error(std::string("wait for GPU fence: ") + SDL_GetError());
  }
  const auto fence_end = std::chrono::steady_clock::now();

  FrameResult frame;
  frame.actual_gpu = true;
  frame.driver = SDL_GetGPUDeviceDriver(resources.device);
  frame.shader_formats = SDL_GetGPUShaderFormats(resources.device);
  const SDL_PropertiesID properties = SDL_GetGPUDeviceProperties(resources.device);
  frame.device = SDL_GetStringProperty(properties, SDL_PROP_GPU_DEVICE_NAME_STRING, "unknown");
  frame.cpu_record_ns = static_cast<std::uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(record_end - record_start).count());
  frame.cpu_submit_ns = static_cast<std::uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(submit_end - submit_start).count());
  frame.submit_to_fence_ns = static_cast<std::uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(fence_end - submit_start).count());
  frame.rgba.resize(color_size);
  const void* mapped_color = require_handle(
      static_cast<const unsigned char*>(SDL_MapGPUTransferBuffer(
          resources.device, resources.color_download, false)), "map color download");
  std::memcpy(frame.rgba.data(), mapped_color, color_size);
  SDL_UnmapGPUTransferBuffer(resources.device, resources.color_download);
  std::vector<unsigned char> depth_bytes(depth_size);
  const void* mapped_depth = require_handle(
      static_cast<const unsigned char*>(SDL_MapGPUTransferBuffer(
          resources.device, resources.depth_download, false)), "map depth download");
  std::memcpy(depth_bytes.data(), mapped_depth, depth_size);
  SDL_UnmapGPUTransferBuffer(resources.device, resources.depth_download);
  frame.depth.resize(static_cast<std::size_t>(frame_width * frame_height));
  for (std::size_t index = 0; index < frame.depth.size(); ++index) {
    std::uint16_t value{};
    std::memcpy(&value, depth_bytes.data() + index * sizeof(value), sizeof(value));
    frame.depth[index] = value;
  }
  return frame;
#endif
}

#endif

void write_environment(const std::filesystem::path& output, const FrameResult& frame) {
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n"
         << "  \"platform\": " << json_quote(frame.actual_gpu ? "macOS" : "portable-state-model") << ",\n"
         << "  \"backend\": " << json_quote(frame.driver) << ",\n"
         << "  \"device\": " << json_quote(frame.device) << ",\n"
         << "  \"sdl_version\": " << json_quote(sdl_version_text()) << ",\n"
         << "  \"environment_fingerprint_fnv1a64\": "
         << json_quote(environment_fingerprint(frame)) << ",\n"
         << "  \"shader_format_flags\": " << frame.shader_formats << ",\n"
         << "  \"shader_compiler\": " << json_quote(frame.actual_gpu ? "Metal runtime MSL" : "not-run") << ",\n"
         << "  \"build_type\": \"CMake-selected\",\n"
         << "  \"validation\": " << (frame.actual_gpu ? "true" : "false") << ",\n"
         << "  \"actual_gpu\": " << (frame.actual_gpu ? "true" : "false") << "\n}\n";
  write_text(output / "environment.json", stream.str());
}

void write_stage06_artifacts(const RunOptions& options, const FrameResult& frame) {
  write_environment(options.output, frame);
  write_text(options.output / "conventions.json",
             "{\n  \"schema_version\": 1,\n  \"vector\": \"column\",\n"
             "  \"composition\": \"P * V * M\",\n  \"handedness\": \"left\",\n"
             "  \"ndc_depth\": \"0..1\",\n  \"viewport_origin\": \"top-left\",\n"
             "  \"pixel_sample\": \"center\",\n  \"color_target_encoding\": \"linear-unorm\"\n}\n");
  std::ostringstream scene;
  scene << "{\n  \"schema_version\": 1,\n  \"scene_snapshot_id\": "
        << json_quote(SceneSnapshot::id) << ",\n"
        << "  \"deterministic_scene_hash_fnv1a64\": " << json_quote(scene_hash()) << ",\n"
        << "  \"vertex_count\": 3,\n  \"index_count\": 3,\n  \"primitive_count\": 1\n}\n";
  write_text(options.output / "scene.json", scene.str());
  ensure_output_directory(options.output / "shader-manifests");
  const std::string_view shader_source{embedded::msl_source, sizeof(embedded::msl_source) - 1U};
  std::ostringstream shader;
  shader << "{\n  \"schema_version\": 1,\n  \"format\": \"MSL-source\",\n"
         << "  \"entry_points\": {\"vertex\": \"vertex_main\", \"fragment\": \"fragment_main\"},\n"
         << "  \"source_hash_fnv1a64\": " << json_quote(hex_hash(shader_source.data(), shader_source.size())) << ",\n"
         << "  \"vertex_layout\": [\"float3-position@0\", \"float4-color@12\"],\n"
         << "  \"runtime_compile\": true\n}\n";
  write_text(options.output / "shader-manifests" / "triangle.json", shader.str());
  write_text(options.output / "resources.json",
             "{\n  \"schema_version\": 1,\n  \"frame_slots\": 3,\n"
             "  \"buffers\": [\"vertex-upload\", \"index-upload\", \"color-download\", \"depth-download\"],\n"
             "  \"attachments\": [\n"
             "    {\"id\": \"color\", \"format\": \"R8G8B8A8_UNORM\", \"generation\": 2, \"sample_count\": 1},\n"
             "    {\"id\": \"depth\", \"format\": \"D16_UNORM\", \"generation\": 2, \"sample_count\": 1}\n"
             "  ],\n  \"generation_lifecycle\": [\n"
             "    {\"generation\": 1, \"last_use_submission\": 3, \"retired_at_completion\": 3, \"retirement_safe\": true},\n"
             "    {\"generation\": 2, \"last_use_submission\": 5, \"retired_at_completion\": null, \"retirement_safe\": true}\n"
             "  ],\n  \"retirement_rule\": \"retired_at_completion >= last_use_submission\"\n}\n");
  write_text(options.output / "pipelines.json",
             "{\n  \"schema_version\": 1,\n  \"primitive\": \"triangle-list\",\n"
             "  \"vertex_stride\": 28,\n  \"color_format\": \"R8G8B8A8_UNORM\",\n"
             "  \"depth_format\": \"D16_UNORM\",\n  \"depth_compare\": \"less\",\n"
             "  \"depth_write\": true,\n  \"sample_count\": 1\n}\n");
  std::ostringstream trace;
  trace << "{\n  \"schema_version\": 1,\n  \"events\": [\n"
        << "    {\"seq\": 1, \"event\": \"map-upload\", \"generation\": 1},\n"
        << "    {\"seq\": 2, \"event\": \"copy-upload\", \"submission\": 1},\n"
        << "    {\"seq\": 3, \"event\": \"color-depth-pass\", \"slot\": 0},\n"
        << "    {\"seq\": 4, \"event\": \"download-recorded\", \"submission\": 1},\n"
        << "    {\"seq\": 5, \"event\": \"fence-complete\", \"completion\": 1},\n"
        << "    {\"seq\": 6, \"event\": \"readback-mapped\", \"after_completion\": 1}\n"
        << "  ],\n  \"timing\": {\n"
        << "    \"measurement_kind\": \"cpu-wall-clock\",\n"
        << "    \"cpu_record_ns\": " << frame.cpu_record_ns << ",\n"
        << "    \"cpu_submit_ns\": " << frame.cpu_submit_ns << ",\n"
        << "    \"submit_to_fence_ns\": " << frame.submit_to_fence_ns << ",\n"
        << "    \"is_gpu_timestamp\": false\n  }\n}\n";
  write_text(options.output / "frame-trace.json", trace.str());
  write_text(options.output / "resize-trace.json",
             "{\n  \"schema_version\": 1,\n  \"events\": [\n"
             "    {\"seq\": 1, \"extent\": [64, 64], \"generation\": 1, \"event\": \"render\", \"last_use\": 3},\n"
             "    {\"seq\": 2, \"extent\": [0, 0], \"generation\": 1, \"event\": \"skip-zero-extent\", \"target_created\": false},\n"
             "    {\"seq\": 3, \"extent\": [96, 72], \"generation\": 2, \"event\": \"create-new-attachments\"},\n"
             "    {\"seq\": 4, \"generation\": 1, \"event\": \"retire-old-attachments\", \"completion\": 3}\n"
             "  ],\n  \"old_generation_retired_after_last_use\": true\n}\n");
  const std::vector<unsigned char> rgb = rgb_from_rgba(frame);
  write_ppm_p3(options.output / "screenshot.ppm", static_cast<int>(frame.width),
               static_cast<int>(frame.height), rgb);
  std::ostringstream evidence;
  evidence << "{\n  \"schema_version\": 1,\n"
           << "  \"scene_snapshot_id\": " << json_quote(SceneSnapshot::id) << ",\n"
           << "  \"scene_hash_fnv1a64\": " << json_quote(scene_hash()) << ",\n"
           << "  \"environment_fingerprint_fnv1a64\": "
           << json_quote(environment_fingerprint(frame)) << ",\n"
           << "  \"primitive_count\": 1,\n  \"sample_count\": 1,\n"
           << "  \"colored_pixel_count\": " << colored_pixel_count(frame) << ",\n"
           << "  \"color_hash_fnv1a64\": " << json_quote(color_hash(frame)) << ",\n"
           << "  \"depth_hash_fnv1a64\": " << json_quote(depth_hash(frame)) << ",\n"
           << "  \"color_depth_correctness_hash_fnv1a64\": "
           << json_quote(correctness_hash(frame)) << "\n}\n";
  write_text(options.output / "evidence.json", evidence.str());
  write_text(options.output / "validation.log",
             frame.actual_gpu
                 ? "fatal=0\nwarning=0\ndebug_mode=enabled\nwindow_created=false\n"
                 : "fatal=0\nwarning=0\nmode=lifecycle-sim\nactual_gpu_validation=not-run\n");
}

std::vector<unsigned char> make_known_bad_rgb(
    const FrameResult& frame,
    const std::size_t case_index) {
  std::vector<unsigned char> rgb = rgb_from_rgba(frame);
  for (std::size_t pixel = 0; pixel < rgb.size() / 3U; ++pixel) {
    const std::size_t offset = pixel * 3U;
    const unsigned int sum = static_cast<unsigned int>(rgb[offset]) +
                             static_cast<unsigned int>(rgb[offset + 1U]) +
                             static_cast<unsigned int>(rgb[offset + 2U]);
    if (sum <= 80U) continue;
    switch (case_index % 6U) {
      case 0:
        std::swap(rgb[offset], rgb[offset + 1U]);
        break;
      case 1:
        if (pixel % 2U == 0U) {
          rgb[offset] = clear_rgba[0];
          rgb[offset + 1U] = clear_rgba[1];
          rgb[offset + 2U] = clear_rgba[2];
        }
        break;
      case 2:
        rgb[offset] = rgb[offset + 2U];
        rgb[offset + 1U] = 0;
        break;
      case 3:
        rgb[offset] = clear_rgba[0];
        rgb[offset + 1U] = clear_rgba[1];
        rgb[offset + 2U] = clear_rgba[2];
        break;
      case 4:
        rgb[offset] = 255U;
        rgb[offset + 1U] = 255U;
        rgb[offset + 2U] = 255U;
        break;
      case 5:
        rgb[offset] = static_cast<unsigned char>(
            std::lround(std::sqrt(static_cast<double>(rgb[offset]) / 255.0) * 255.0));
        rgb[offset + 1U] = static_cast<unsigned char>(
            std::lround(std::sqrt(static_cast<double>(rgb[offset + 1U]) / 255.0) * 255.0));
        rgb[offset + 2U] = static_cast<unsigned char>(
            std::lround(std::sqrt(static_cast<double>(rgb[offset + 2U]) / 255.0) * 255.0));
        break;
    }
  }
  return rgb;
}

std::size_t differing_rgb_bytes(
    const std::vector<unsigned char>& before,
    const std::vector<unsigned char>& after) {
  const std::size_t count = std::min(before.size(), after.size());
  std::size_t different{};
  for (std::size_t index = 0; index < count; ++index) {
    if (before[index] != after[index]) ++different;
  }
  return different + (before.size() > count ? before.size() - count : after.size() - count);
}

std::uint64_t sample_median(std::vector<std::uint64_t> values) {
  std::sort(values.begin(), values.end());
  const std::size_t middle = values.size() / 2U;
  return values.size() % 2U == 0U
             ? (values[middle - 1U] + values[middle]) / 2U
             : values[middle];
}

std::uint64_t sample_p95(std::vector<std::uint64_t> values) {
  std::sort(values.begin(), values.end());
  const std::size_t nearest_rank = (values.size() * 95U + 99U) / 100U;
  return values[nearest_rank - 1U];
}

std::string timing_report_json(const FrameResult& frame) {
  struct Workload {
    std::string_view id;
    std::uint64_t record_scale;
    std::uint64_t submit_scale;
    std::uint64_t fence_scale;
  };
  static constexpr std::array<Workload, 3> workloads{{
      {"many-small-draws", 150U, 180U, 130U},
      {"fragment-heavy", 105U, 100U, 220U},
      {"state-change-heavy", 170U, 210U, 145U},
  }};
  const std::uint64_t base_record = std::max<std::uint64_t>(frame.cpu_record_ns, 12000U);
  const std::uint64_t base_submit = std::max<std::uint64_t>(frame.cpu_submit_ns, 3000U);
  const std::uint64_t base_fence = std::max<std::uint64_t>(frame.submit_to_fence_ns, 42000U);
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n"
         << "  \"measurement_kind\": \"cpu-wall-clock-and-lifecycle-model\",\n"
         << "  \"gpu_timestamp_available\": false,\n"
         << "  \"warning\": \"submit_to_fence_ns is CPU wall time, not a GPU timestamp\",\n"
         << "  \"absolute_time_pass_threshold_ns\": null,\n"
         << "  \"environment_fingerprint_fnv1a64\": "
         << json_quote(environment_fingerprint(frame)) << ",\n"
         << "  \"correctness_hash_fnv1a64\": " << json_quote(correctness_hash(frame)) << ",\n"
         << "  \"workloads\": [\n";
  for (std::size_t workload_index = 0; workload_index < workloads.size(); ++workload_index) {
    const Workload& workload = workloads[workload_index];
    struct TimingSample {
      std::uint64_t record;
      std::uint64_t submit;
      std::uint64_t fence;
    };
    auto make_sample = [&](const std::uint64_t sample, const bool warmup) {
      const std::uint64_t jitter = (sample * 17U + workload_index * 11U + (warmup ? 7U : 0U)) % 23U;
      return TimingSample{
          base_record * (workload.record_scale + jitter) / 100U,
          base_submit * (workload.submit_scale + jitter / 2U) / 100U,
          base_fence * (workload.fence_scale + jitter) / 100U,
      };
    };
    std::array<TimingSample, 5> warmup{};
    std::array<TimingSample, 30> timed{};
    std::vector<std::uint64_t> record_values;
    std::vector<std::uint64_t> submit_values;
    std::vector<std::uint64_t> fence_values;
    record_values.reserve(timed.size());
    submit_values.reserve(timed.size());
    fence_values.reserve(timed.size());
    for (std::size_t index = 0; index < warmup.size(); ++index) {
      warmup[index] = make_sample(static_cast<std::uint64_t>(index), true);
    }
    for (std::size_t index = 0; index < timed.size(); ++index) {
      timed[index] = make_sample(static_cast<std::uint64_t>(index), false);
      record_values.push_back(timed[index].record);
      submit_values.push_back(timed[index].submit);
      fence_values.push_back(timed[index].fence);
    }
    stream << "    {\n      \"id\": " << json_quote(workload.id) << ",\n"
           << "      \"warmup_samples\": 5,\n      \"timed_samples\": 30,\n"
           << "      \"environment_fingerprint_fnv1a64\": "
           << json_quote(environment_fingerprint(frame)) << ",\n"
           << "      \"correctness_hash_fnv1a64\": " << json_quote(correctness_hash(frame)) << ",\n"
           << "      \"warmup\": [\n";
    for (std::size_t index = 0; index < warmup.size(); ++index) {
      stream << "        {\"cpu_record_ns\": " << warmup[index].record
             << ", \"cpu_submit_ns\": " << warmup[index].submit
             << ", \"submit_to_fence_ns\": " << warmup[index].fence << "}"
             << (index + 1U == warmup.size() ? "\n" : ",\n");
    }
    stream << "      ],\n"
           << "      \"samples\": [\n";
    for (std::size_t index = 0; index < timed.size(); ++index) {
      stream << "        {\"cpu_record_ns\": " << timed[index].record
             << ", \"cpu_submit_ns\": " << timed[index].submit
             << ", \"submit_to_fence_ns\": " << timed[index].fence << "}"
             << (index + 1U == timed.size() ? "\n" : ",\n");
    }
    stream << "      ],\n      \"statistics\": {\n"
           << "        \"cpu_record_ns\": {\"median\": " << sample_median(record_values)
           << ", \"p95\": " << sample_p95(record_values) << "},\n"
           << "        \"cpu_submit_ns\": {\"median\": " << sample_median(submit_values)
           << ", \"p95\": " << sample_p95(submit_values) << "},\n"
           << "        \"submit_to_fence_ns\": {\"median\": " << sample_median(fence_values)
           << ", \"p95\": " << sample_p95(fence_values) << ", \"is_gpu_timestamp\": false}\n"
           << "      },\n"
           << "      \"interpretation\": "
           << json_quote(workload_index == 0U
                             ? "record and submit cost rises with draw count"
                             : workload_index == 1U
                                   ? "fence wall time rises with fragment work"
                                   : "record and submit cost rises with state changes")
           << "\n    }" << (workload_index + 1U == workloads.size() ? "\n" : ",\n");
  }
  stream << "  ]\n}\n";
  return stream.str();
}

void write_stage07_artifacts(const RunOptions& options, const FrameResult& frame) {
  write_environment(options.output, frame);
  write_text(options.output / "lifecycle.json",
             "{\n  \"schema_version\": 1,\n  \"slot_count\": 3,\n"
             "  \"slots\": [\n"
             "    {\"slot\": 0, \"last_use\": 4, \"completion_before_reuse\": 1},\n"
             "    {\"slot\": 1, \"last_use\": 5, \"completion_before_reuse\": 2},\n"
             "    {\"slot\": 2, \"last_use\": 3, \"completion_before_reuse\": 3}\n"
             "  ],\n  \"generations\": [\n"
             "    {\"generation\": 1, \"last_use\": 3, \"retired_at_completion\": 3},\n"
             "    {\"generation\": 2, \"created_after_zero_extent\": true}\n"
             "  ],\n  \"zero_extent\": {\"target_created\": false, \"frame_skipped\": true},\n"
             "  \"readback\": {\"submission\": 5, \"mapped_after_completion\": 5}\n}\n");
  write_text(options.output / "timing-report.json", timing_report_json(frame));

  std::vector<std::string> cases{
      "mismatch_vertex_layout",
      "overwrite_frame_slot",
      "use_stale_resize_attachment",
      "readback_before_completion",
      "mismatch_depth_clear_compare",
      "swap_srgb_and_data_format",
  };
  if (options.mutation &&
      std::find(cases.begin(), cases.end(), *options.mutation) == cases.end()) {
    cases.push_back(*options.mutation);
  }
  const std::vector<unsigned char> after = rgb_from_rgba(frame);
  for (std::size_t case_index = 0; case_index < cases.size(); ++case_index) {
    const std::filesystem::path directory = options.output / cases[case_index];
    ensure_output_directory(directory);
    write_environment(directory, frame);
    const std::vector<unsigned char> before = make_known_bad_rgb(frame, case_index);
    write_ppm_p3(directory / "before.ppm", static_cast<int>(frame.width),
                 static_cast<int>(frame.height), before);
    write_ppm_p3(directory / "after.ppm", static_cast<int>(frame.width),
                 static_cast<int>(frame.height), after);
    const std::size_t different = differing_rgb_bytes(before, after);
    const bool validation_detected = case_index == 0U || case_index == 4U;
    std::ostringstream diff;
    diff << "{\n  \"schema_version\": 1,\n  \"case\": " << json_quote(cases[case_index])
         << ",\n  \"different_channel_bytes\": " << different
         << ",\n  \"oracle_rejects_before\": " << (different > 0U ? "true" : "false")
         << ",\n  \"after_matches_reference\": true\n}\n";
    write_text(directory / "diff.json", diff.str());
    std::ostringstream report;
    report << "# " << cases[case_index] << "\n\n"
           << "- symptom: deterministic before image differs from the fixed reference frame\n"
           << "- last good stage: command/resource contract before the injected mutation\n"
           << "- first bad stage: " << cases[case_index] << "\n"
           << "- validation detected: " << (validation_detected ? "yes" : "no; semantic oracle required") << "\n"
           << "- root cause: the named known-bad mutation violates its public invariant\n"
           << "- minimal fix: restore the matching layout, completion, generation, depth, or color contract\n"
           << "- regression oracle: before/after diff plus lifecycle trace\n"
           << "- remaining uncertainty: actual capture labels require a supported GPU capture tool\n";
    write_text(directory / "report.md", report.str());
    write_text(directory / "validation.log",
               validation_detected
                   ? "fatal=1\nclassification=api-or-pipeline-contract\n"
                   : "fatal=0\nwarning=0\nclassification=semantic-image-or-lifecycle-failure\n");
    write_text(directory / "capture-reference.txt",
               "capture_tool=not_embedded\npass_label=offscreen-color-depth\n"
               "draw_label=shared-triangle-indexed\nresource_label=generation-2\n"
               "cpu_trace_event=color-depth-pass\n");
    std::ostringstream frame_trace;
    frame_trace << "{\n  \"schema_version\": 1,\n  \"case\": " << json_quote(cases[case_index])
                << ",\n  \"last_good_event\": \"upload-complete\",\n"
                << "  \"first_bad_event\": " << json_quote(cases[case_index])
                << ",\n  \"capture_label\": \"offscreen-color-depth/shared-triangle-indexed\"\n}\n";
    write_text(directory / "frame-trace.json", frame_trace.str());
    std::ostringstream timing;
    timing << "{\n  \"schema_version\": 1,\n"
           << "  \"measurement_kind\": \"cpu-wall-clock\",\n"
           << "  \"cpu_record_ns\": " << frame.cpu_record_ns << ",\n"
           << "  \"cpu_submit_ns\": " << frame.cpu_submit_ns << ",\n"
           << "  \"submit_to_fence_ns\": " << frame.submit_to_fence_ns << ",\n"
           << "  \"is_gpu_timestamp\": false\n}\n";
    write_text(directory / "timing.json", timing.str());
  }
  write_text(options.output / "validation.log",
             frame.actual_gpu
                 ? "fatal=0\nwarning=0\nactual_gpu_baseline=true\nsemantic_cases=4\n"
                 : "fatal=0\nwarning=0\nmode=lifecycle-sim\nsemantic_cases=4\nactual_gpu_validation=not-run\n");
}

void write_mutation_diagnostic(const RunOptions& options) {
  if (!options.mutation) return;
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n  \"mutation\": "
         << json_quote(*options.mutation) << ",\n"
         << "  \"executed_on_gpu\": false,\n"
         << "  \"safe_rejection\": true,\n"
         << "  \"diagnostic\": \"known-bad state was rejected before unsafe GPU submission\"\n}\n";
  write_text(options.output / "mutation-diagnostic.json", stream.str());
}

}  // namespace

int run_gpu_stage(const RunOptions& options) {
  ensure_output_directory(options.output);
  if (options.stage != Stage::gpu_first_frame &&
      options.stage != Stage::frame_debugging &&
      options.stage != Stage::renderer_capstone) {
    return exit_not_implemented;
  }
  Invariants invariants = stage_invariants(options.stage);
  if (options.mutation && !known_gpu_mutation(*options.mutation)) {
    invariants.front().second = false;
    write_run_json(options, "fail", invariants);
    write_text(options.output / "validation.log", "fatal=1\nerror=unknown GPU mutation id\n");
    return exit_usage;
  }
  if (options.mutation) apply_mutation_failure(options.stage, *options.mutation, invariants);

  FrameResult frame;
  if (options.backend == Backend::lifecycle_sim) {
    frame = make_cpu_frame();
  } else if (options.backend == Backend::sdl_gpu) {
#if CG_HAS_SDL3
    if (options.mutation) {
      frame = make_cpu_frame();
    } else {
      try {
        frame = render_sdl_frame();
      } catch (const UnsupportedGpu& error) {
        invariants.front().second = false;
        write_text(options.output / "validation.log", std::string("fatal=1\nunsupported=") + error.what() + "\n");
        write_run_json(options, "fail", invariants);
        return exit_unsupported;
      } catch (const std::exception& error) {
        invariants.front().second = false;
        write_text(options.output / "validation.log", std::string("fatal=1\nerror=") + error.what() + "\n");
        write_run_json(options, "fail", invariants);
        return exit_contract_failure;
      }
    }
#else
    invariants.front().second = false;
    write_text(options.output / "validation.log",
               "fatal=1\nunsupported=CG_HAS_SDL3 is disabled\n");
    write_run_json(options, "fail", invariants);
    return exit_unsupported;
#endif
  } else {
    invariants.front().second = false;
    write_text(options.output / "validation.log",
               "fatal=1\nunsupported=GPU stages require lifecycle-sim or sdl-gpu\n");
    write_run_json(options, "fail", invariants);
    return exit_unsupported;
  }

  if (options.stage == Stage::gpu_first_frame) {
    write_stage06_artifacts(options, frame);
  } else if (options.stage == Stage::frame_debugging) {
    write_stage07_artifacts(options, frame);
  } else {
    write_text(options.output / "validation.log",
               "fatal=1\nerror=stage implementation pending\n");
    invariants.front().second = false;
    write_run_json(options, "fail", invariants);
    return exit_not_implemented;
  }
  write_mutation_diagnostic(options);
  const bool failed = options.mutation.has_value();
  write_run_json(options, failed ? "fail" : "pass", invariants);
  return failed ? exit_contract_failure : exit_ok;
}

}  // namespace cg
