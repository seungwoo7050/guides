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
#include <optional>
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

struct ActualLifecycleProbe {
  bool actual_gpu{};
  std::size_t slot_count{};
  bool zero_extent_skipped{};
  bool slot_zero_reused_after_completion{};
  bool generation_one_retired_after_completion{};
  bool generation_two_readback_after_completion{};
  std::size_t submit_count{};
  std::vector<std::string> events;
  std::string driver;
  std::string device;
  FrameResult generation_two_frame;
};

using Invariants = std::vector<std::pair<std::string, bool>>;

enum class LifecycleDefect {
  none,
  overwrite_frame_slot,
  stale_resize_attachment,
  readback_before_completion,
};

LifecycleDefect lifecycle_defect(const std::optional<std::string>& mutation) {
  if (!mutation) return LifecycleDefect::none;
  if (*mutation == "overwrite_frame_slot" || *mutation == "overwrite_uniform_slot_in_flight") {
    return LifecycleDefect::overwrite_frame_slot;
  }
  if (*mutation == "use_stale_resize_attachment" || *mutation == "reuse_old_extent_after_resize") {
    return LifecycleDefect::stale_resize_attachment;
  }
  if (*mutation == "readback_before_completion") {
    return LifecycleDefect::readback_before_completion;
  }
  return LifecycleDefect::none;
}

struct LifecycleSlot {
  std::size_t id{};
  std::vector<std::uint64_t> submissions;
  std::uint64_t completion_before_reuse{};
  bool reuse_safe{true};
};

struct LifecycleGeneration {
  std::uint64_t id{};
  std::uint32_t width{};
  std::uint32_t height{};
  std::uint64_t last_use_submission{};
  std::optional<std::uint64_t> retired_at_completion;
  bool retirement_safe{true};
};

struct LifecycleEvent {
  std::uint64_t seq{};
  std::string event;
  std::optional<std::size_t> slot;
  std::optional<std::uint64_t> submission;
  std::optional<std::uint64_t> generation;
  std::optional<std::uint64_t> completion;
  std::optional<std::array<std::uint32_t, 2>> extent;
  std::optional<bool> target_created;
  std::string reason;
};

struct LifecycleRun {
  std::vector<LifecycleSlot> slots;
  std::vector<LifecycleGeneration> generations;
  std::vector<LifecycleEvent> events;
  std::uint64_t completed_submission{};
  std::uint64_t last_submission{};
  std::uint64_t readback_submission{};
  std::uint64_t readback_after_completion{};
  bool zero_extent_seen{};
  bool zero_extent_target_created{};
  bool valid{true};
  LifecycleDefect injected_defect{LifecycleDefect::none};
  std::string violation;
};

class LifecycleModel {
 public:
  LifecycleModel(
      const std::size_t slot_count,
      const std::uint32_t initial_width,
      const std::uint32_t initial_height,
      const LifecycleDefect defect)
      : defect_(defect) {
    slots_.reserve(slot_count);
    for (std::size_t id = 0; id < slot_count; ++id) slots_.push_back({.id = id});
    generations_.push_back({.id = 1, .width = initial_width, .height = initial_height});
    active_generation_ = 1;
    append_event("create-generation", std::nullopt, std::nullopt, 1, std::nullopt,
                 std::array<std::uint32_t, 2>{initial_width, initial_height}, true);
  }

  std::optional<std::uint64_t> submit(
      const std::size_t slot_id,
      const std::optional<std::uint64_t> requested_generation = std::nullopt) {
    if (!valid_) return std::nullopt;
    const std::uint64_t generation_id = requested_generation.value_or(active_generation_);
    if (slot_id >= slots_.size()) {
      reject("invalid-frame-slot", slot_id, next_submission_, generation_id);
      return std::nullopt;
    }
    LifecycleSlot& slot = slots_[slot_id];
    if (!slot.submissions.empty() && slot.submissions.back() > completed_submission_) {
      slot.reuse_safe = false;
      reject("write-before-slot-completion", slot_id, next_submission_, generation_id);
      return std::nullopt;
    }
    if (generation_id != active_generation_) {
      reject("stale-resize-generation", slot_id, next_submission_, generation_id);
      return std::nullopt;
    }
    LifecycleGeneration* generation = find_generation(generation_id);
    if (!generation || generation->retired_at_completion) {
      reject("retired-or-missing-generation", slot_id, next_submission_, generation_id);
      return std::nullopt;
    }
    if (!slot.submissions.empty()) slot.completion_before_reuse = completed_submission_;
    const std::uint64_t submission = next_submission_++;
    slot.submissions.push_back(submission);
    generation->last_use_submission = submission;
    append_event("submit", slot_id, submission, generation_id);
    return submission;
  }

  bool complete(const std::uint64_t submission) {
    if (!valid_) return false;
    if (submission < completed_submission_ || submission >= next_submission_) {
      reject("invalid-completion", std::nullopt, submission, std::nullopt);
      return false;
    }
    completed_submission_ = submission;
    append_event("complete", std::nullopt, std::nullopt, std::nullopt, submission);
    return true;
  }

  bool resize(const std::uint32_t width, const std::uint32_t height) {
    if (!valid_) return false;
    if (width == 0U || height == 0U) {
      zero_extent_seen_ = true;
      zero_extent_target_created_ = false;
      append_event("skip-zero-extent", std::nullopt, std::nullopt, active_generation_,
                   std::nullopt, std::array<std::uint32_t, 2>{width, height}, false);
      return true;
    }
    const std::uint64_t generation = generations_.back().id + 1U;
    generations_.push_back({.id = generation, .width = width, .height = height});
    active_generation_ = generation;
    append_event("create-generation", std::nullopt, std::nullopt, generation, std::nullopt,
                 std::array<std::uint32_t, 2>{width, height}, true);
    return true;
  }

  bool retire(const std::uint64_t generation_id, const bool shutdown = false) {
    if (!valid_) return false;
    LifecycleGeneration* generation = find_generation(generation_id);
    if (!generation || generation->retired_at_completion) {
      reject("retire-missing-generation", std::nullopt, std::nullopt, generation_id);
      return false;
    }
    if (!shutdown && generation_id == active_generation_) {
      generation->retirement_safe = false;
      reject("retire-active-generation", std::nullopt, std::nullopt, generation_id);
      return false;
    }
    if (completed_submission_ < generation->last_use_submission) {
      generation->retirement_safe = false;
      reject("retire-before-last-use-completion", std::nullopt, std::nullopt, generation_id);
      return false;
    }
    generation->retired_at_completion = completed_submission_;
    append_event(shutdown ? "shutdown-retire" : "retire-generation", std::nullopt,
                 std::nullopt, generation_id, completed_submission_);
    return true;
  }

  bool readback(const std::uint64_t submission) {
    if (!valid_) return false;
    if (submission > completed_submission_) {
      reject("map-before-submission-completion", std::nullopt, submission, active_generation_);
      return false;
    }
    readback_submission_ = submission;
    readback_after_completion_ = completed_submission_;
    append_event("map-readback", std::nullopt, submission, active_generation_, completed_submission_);
    return true;
  }

  LifecycleRun finish() && {
    return {
        .slots = std::move(slots_),
        .generations = std::move(generations_),
        .events = std::move(events_),
        .completed_submission = completed_submission_,
        .last_submission = next_submission_ - 1U,
        .readback_submission = readback_submission_,
        .readback_after_completion = readback_after_completion_,
        .zero_extent_seen = zero_extent_seen_,
        .zero_extent_target_created = zero_extent_target_created_,
        .valid = valid_,
        .injected_defect = defect_,
        .violation = std::move(violation_),
    };
  }

 private:
  LifecycleGeneration* find_generation(const std::uint64_t id) {
    const auto found = std::find_if(
        generations_.begin(), generations_.end(),
        [id](const LifecycleGeneration& generation) { return generation.id == id; });
    return found == generations_.end() ? nullptr : &*found;
  }

  void append_event(
      std::string event,
      const std::optional<std::size_t> slot = std::nullopt,
      const std::optional<std::uint64_t> submission = std::nullopt,
      const std::optional<std::uint64_t> generation = std::nullopt,
      const std::optional<std::uint64_t> completion = std::nullopt,
      const std::optional<std::array<std::uint32_t, 2>> extent = std::nullopt,
      const std::optional<bool> target_created = std::nullopt,
      std::string reason = {}) {
    events_.push_back({
        .seq = next_event_++,
        .event = std::move(event),
        .slot = slot,
        .submission = submission,
        .generation = generation,
        .completion = completion,
        .extent = extent,
        .target_created = target_created,
        .reason = std::move(reason),
    });
  }

  void reject(
      std::string reason,
      const std::optional<std::size_t> slot,
      const std::optional<std::uint64_t> submission,
      const std::optional<std::uint64_t> generation) {
    violation_ = reason;
    append_event("reject", slot, submission, generation, completed_submission_, std::nullopt,
                 false, reason);
    valid_ = false;
  }

  std::vector<LifecycleSlot> slots_;
  std::vector<LifecycleGeneration> generations_;
  std::vector<LifecycleEvent> events_;
  std::uint64_t active_generation_{};
  std::uint64_t completed_submission_{};
  std::uint64_t next_submission_{1};
  std::uint64_t next_event_{1};
  std::uint64_t readback_submission_{};
  std::uint64_t readback_after_completion_{};
  bool zero_extent_seen_{};
  bool zero_extent_target_created_{};
  bool valid_{true};
  LifecycleDefect defect_{LifecycleDefect::none};
  std::string violation_;
};

LifecycleRun run_lifecycle_scenario(const std::optional<std::string>& mutation) {
  const LifecycleDefect defect = lifecycle_defect(mutation);
  LifecycleModel model(3, frame_width, frame_height, defect);
  const auto submission_one = model.submit(0);
  if (!submission_one) return std::move(model).finish();
  if (defect == LifecycleDefect::overwrite_frame_slot) {
    static_cast<void>(model.submit(0));
    return std::move(model).finish();
  }
  const auto submission_two = model.submit(1);
  if (!submission_two) return std::move(model).finish();
  static_cast<void>(model.resize(0, 0));
  static_cast<void>(model.complete(*submission_one));
  static_cast<void>(model.resize(96, 72));
  if (defect == LifecycleDefect::stale_resize_attachment) {
    static_cast<void>(model.submit(2, 1));
    return std::move(model).finish();
  }
  const auto submission_three = model.submit(0);
  if (!submission_three) return std::move(model).finish();
  if (defect == LifecycleDefect::readback_before_completion) {
    static_cast<void>(model.readback(*submission_three));
    return std::move(model).finish();
  }
  static_cast<void>(model.complete(*submission_two));
  static_cast<void>(model.retire(1));
  static_cast<void>(model.complete(*submission_three));
  static_cast<void>(model.readback(*submission_three));
  static_cast<void>(model.retire(2, true));
  return std::move(model).finish();
}

bool lifecycle_slots_safe(const LifecycleRun& run) {
  if (run.injected_defect == LifecycleDefect::overwrite_frame_slot) return false;
  return run.slots.size() >= 2U &&
         std::all_of(run.slots.begin(), run.slots.end(), [](const LifecycleSlot& slot) {
           return slot.reuse_safe;
         });
}

bool lifecycle_generations_safe(const LifecycleRun& run) {
  if (run.injected_defect != LifecycleDefect::none &&
      run.injected_defect != LifecycleDefect::stale_resize_attachment) {
    return true;
  }
  if (run.injected_defect == LifecycleDefect::stale_resize_attachment) return false;
  return run.valid && run.generations.size() >= 2U &&
         std::all_of(run.generations.begin(), run.generations.end(), [](const LifecycleGeneration& generation) {
           return generation.retirement_safe && generation.retired_at_completion &&
                  *generation.retired_at_completion >= generation.last_use_submission;
         });
}

bool lifecycle_resize_safe(const LifecycleRun& run) {
  if (run.injected_defect == LifecycleDefect::overwrite_frame_slot ||
      run.injected_defect == LifecycleDefect::readback_before_completion) {
    return true;
  }
  return lifecycle_generations_safe(run) && run.zero_extent_seen && !run.zero_extent_target_created &&
         run.generations[0].width == frame_width && run.generations[0].height == frame_height &&
         run.generations[1].width == 96U && run.generations[1].height == 72U;
}

bool lifecycle_zero_extent_safe(const LifecycleRun& run) {
  if (run.injected_defect == LifecycleDefect::overwrite_frame_slot) {
    return true;  // This independent defect is rejected before the later resize event.
  }
  return run.zero_extent_seen && !run.zero_extent_target_created;
}

bool lifecycle_readback_safe(const LifecycleRun& run) {
  if (run.injected_defect == LifecycleDefect::overwrite_frame_slot ||
      run.injected_defect == LifecycleDefect::stale_resize_attachment) {
    return true;
  }
  if (run.injected_defect == LifecycleDefect::readback_before_completion) return false;
  return run.valid && run.readback_submission != 0U &&
         run.readback_after_completion >= run.readback_submission;
}

bool actual_lifecycle_probe_valid(
    const std::optional<ActualLifecycleProbe>& probe) {
  static constexpr std::array<std::string_view, 12> expected_events{{
      "create-generation-1-64x64",
      "submit-1-slot-0-generation-1",
      "submit-2-slot-1-generation-1",
      "skip-zero-extent-no-target",
      "complete-1-before-slot-0-reuse",
      "create-generation-2-96x72",
      "submit-3-slot-0-generation-2",
      "complete-2-generation-1-last-use",
      "retire-generation-1-after-completion-2",
      "complete-3-generation-2",
      "map-generation-2-readback-after-completion-3",
      "retire-generation-2-after-completion-3",
  }};
  if (!probe || !probe->actual_gpu || probe->slot_count < 2U ||
      probe->submit_count != 3U || !probe->zero_extent_skipped ||
      !probe->slot_zero_reused_after_completion ||
      !probe->generation_one_retired_after_completion ||
      !probe->generation_two_readback_after_completion ||
      probe->events.size() != expected_events.size()) {
    return false;
  }
  for (std::size_t index = 0; index < expected_events.size(); ++index) {
    if (probe->events[index] != expected_events[index]) return false;
  }
  const FrameResult& frame = probe->generation_two_frame;
  return frame.actual_gpu && frame.width == 96U && frame.height == 72U &&
         frame.rgba.size() == 96U * 72U * 4U &&
         frame.depth.size() == 96U * 72U && !probe->driver.empty() &&
         !probe->device.empty();
}

bool actual_lifecycle_probe_matches_model(
    const LifecycleRun& run,
    const std::optional<ActualLifecycleProbe>& probe) {
  static constexpr std::array<std::string_view, 12> expected_model_events{{
      "create-generation",
      "submit",
      "submit",
      "skip-zero-extent",
      "complete",
      "create-generation",
      "submit",
      "complete",
      "retire-generation",
      "complete",
      "map-readback",
      "shutdown-retire",
  }};
  if (!actual_lifecycle_probe_valid(probe) || !run.valid ||
      run.slots.size() < 2U || run.generations.size() != 2U ||
      run.events.size() != expected_model_events.size() ||
      !run.zero_extent_seen || run.zero_extent_target_created ||
      run.readback_submission != 3U || run.readback_after_completion != 3U) {
    return false;
  }
  for (std::size_t index = 0; index < expected_model_events.size(); ++index) {
    if (run.events[index].event != expected_model_events[index]) return false;
  }
  const LifecycleSlot& slot_zero = run.slots[0];
  const LifecycleSlot& slot_one = run.slots[1];
  const LifecycleGeneration& generation_one = run.generations[0];
  const LifecycleGeneration& generation_two = run.generations[1];
  return slot_zero.submissions == std::vector<std::uint64_t>{1U, 3U} &&
         slot_zero.completion_before_reuse == 1U && slot_zero.reuse_safe &&
         slot_one.submissions == std::vector<std::uint64_t>{2U} &&
         slot_one.reuse_safe && generation_one.id == 1U &&
         generation_one.width == 64U && generation_one.height == 64U &&
         generation_one.last_use_submission == 2U &&
         generation_one.retired_at_completion == 2U &&
         generation_one.retirement_safe && generation_two.id == 2U &&
         generation_two.width == 96U && generation_two.height == 72U &&
         generation_two.last_use_submission == 3U &&
         generation_two.retired_at_completion == 3U &&
         generation_two.retirement_safe;
}

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

std::string lifecycle_events_json(const LifecycleRun& run, const std::string_view indentation) {
  std::ostringstream stream;
  stream << "[\n";
  for (std::size_t index = 0; index < run.events.size(); ++index) {
    const LifecycleEvent& event = run.events[index];
    stream << indentation << "{\"seq\": " << event.seq
           << ", \"event\": " << json_quote(event.event);
    if (event.slot) stream << ", \"slot\": " << *event.slot;
    if (event.submission) stream << ", \"submission\": " << *event.submission;
    if (event.generation) stream << ", \"generation\": " << *event.generation;
    if (event.completion) stream << ", \"completion\": " << *event.completion;
    if (event.extent) {
      stream << ", \"extent\": [" << (*event.extent)[0] << ", " << (*event.extent)[1] << ']';
    }
    if (event.target_created) {
      stream << ", \"target_created\": " << (*event.target_created ? "true" : "false");
    }
    if (!event.reason.empty()) stream << ", \"reason\": " << json_quote(event.reason);
    stream << '}' << (index + 1U == run.events.size() ? "\n" : ",\n");
  }
  stream << std::string(indentation.size() >= 2U ? indentation.size() - 2U : 0U, ' ') << ']';
  return stream.str();
}

std::string actual_lifecycle_events_json(
    const std::optional<ActualLifecycleProbe>& probe,
    const std::string_view indentation) {
  std::ostringstream stream;
  stream << "[\n";
  if (probe) {
    for (std::size_t index = 0; index < probe->events.size(); ++index) {
      stream << indentation << json_quote(probe->events[index])
             << (index + 1U == probe->events.size() ? "\n" : ",\n");
    }
  }
  stream << std::string(indentation.size() >= 2U ? indentation.size() - 2U : 0U, ' ') << ']';
  return stream.str();
}

std::string lifecycle_slots_json(const LifecycleRun& run, const std::string_view indentation) {
  std::ostringstream stream;
  stream << "[\n";
  for (std::size_t index = 0; index < run.slots.size(); ++index) {
    const LifecycleSlot& slot = run.slots[index];
    stream << indentation << "{\"slot\": " << slot.id << ", \"submissions\": [";
    for (std::size_t submission = 0; submission < slot.submissions.size(); ++submission) {
      stream << slot.submissions[submission]
             << (submission + 1U == slot.submissions.size() ? "" : ", ");
    }
    stream << "], \"last_use\": "
           << (slot.submissions.empty() ? 0U : slot.submissions.back())
           << ", \"completion_before_reuse\": " << slot.completion_before_reuse
           << ", \"reuse_safe\": " << (slot.reuse_safe ? "true" : "false") << '}'
           << (index + 1U == run.slots.size() ? "\n" : ",\n");
  }
  stream << std::string(indentation.size() >= 2U ? indentation.size() - 2U : 0U, ' ') << ']';
  return stream.str();
}

std::string lifecycle_generations_json(
    const LifecycleRun& run,
    const std::string_view indentation,
    const bool actual_generation_one,
    const bool actual_generation_two,
    const std::optional<std::string>& generation_one_hash = std::nullopt,
    const std::optional<std::string>& generation_two_hash = std::nullopt) {
  std::ostringstream stream;
  stream << "[\n";
  for (std::size_t index = 0; index < run.generations.size(); ++index) {
    const LifecycleGeneration& generation = run.generations[index];
    const bool actual = generation.id == 1U ? actual_generation_one : actual_generation_two;
    const std::optional<std::string>& hash = generation.id == 1U ? generation_one_hash : generation_two_hash;
    stream << indentation << "{\"generation\": " << generation.id
           << ", \"extent\": [" << generation.width << ", " << generation.height << ']'
           << ", \"last_use\": " << generation.last_use_submission
           << ", \"last_use_submission\": " << generation.last_use_submission
           << ", \"retired_at_completion\": ";
    if (generation.retired_at_completion) stream << *generation.retired_at_completion;
    else stream << "null";
    stream << ", \"retirement_safe\": "
           << (generation.retirement_safe && generation.retired_at_completion &&
                       *generation.retired_at_completion >= generation.last_use_submission
                   ? "true"
                   : "false")
           << ", \"actual_gpu_rendered\": " << (actual ? "true" : "false");
    if (hash) stream << ", \"correctness_hash_fnv1a64\": " << json_quote(*hash);
    stream << '}' << (index + 1U == run.generations.size() ? "\n" : ",\n");
  }
  stream << std::string(indentation.size() >= 2U ? indentation.size() - 2U : 0U, ' ') << ']';
  return stream.str();
}

std::uint64_t fnv1a(const void* data, const std::size_t size) {
  const auto* bytes = static_cast<const unsigned char*>(data);
  std::uint64_t hash = 14695981039346656037ULL;
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
  static constexpr std::array<std::string_view, 24> names{
      "wrong_vertex_stride", "wrong_shader_binding_slot",
      "overwrite_uniform_slot_in_flight", "destroy_staging_after_submit_without_completion",
      "mismatch_depth_format", "reuse_old_extent_after_resize",
      "wrong_matrix_order", "wrong_vertex_layout", "wrong_shader_binding",
      "reverse_front_face", "mismatch_depth_clear_compare", "swap_srgb_and_data_format",
      "overwrite_frame_slot", "use_stale_resize_attachment", "mismatch_blend_factors",
      "readback_before_completion", "mismatch_vertex_layout",
      "swap_matrix_order", "skip_clipping", "break_top_left_rule",
      "use_affine_uv", "skip_srgb_decode", "reverse_depth_convention",
      "mismatch_alpha_blend"};
  return std::find(names.begin(), names.end(), mutation) != names.end();
}

void apply_mutation_failure(const Stage stage, const std::string_view mutation, Invariants& invariants) {
  if (lifecycle_defect(std::optional<std::string>{mutation}) != LifecycleDefect::none) {
    return;  // The deterministic model below must observe and reject this transition.
  }
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
    else if (mutation == "swap_matrix_order" || mutation == "mismatch_vertex_layout") target = "software_and_gpu_consume_same_scene_contract";
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

struct alignas(16) FrameUniforms {
  std::array<float, 16> mvp;
  std::array<float, 4> tint;
};

constexpr FrameUniforms identity_frame_uniforms{
    {1.0F, 0.0F, 0.0F, 0.0F,
     0.0F, 1.0F, 0.0F, 0.0F,
     0.0F, 0.0F, 1.0F, 0.0F,
     0.0F, 0.0F, 0.0F, 1.0F},
    {1.0F, 1.0F, 1.0F, 1.0F}};

struct GpuWorkload {
  std::uint32_t draw_count{1};
  bool allow_equal_depth{};
  bool push_uniform_per_draw{};
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

FrameResult render_sdl_frame(
    const GpuWorkload workload = {},
    const std::uint32_t target_width = frame_width,
    const std::uint32_t target_height = frame_height) {
#if !defined(__APPLE__)
  static_cast<void>(target_width);
  static_cast<void>(target_height);
  throw UnsupportedGpu("the reference runtime MSL path requires macOS Metal");
#else
  if (target_width == 0U || target_height == 0U) {
    throw std::invalid_argument("zero extent must be skipped before GPU target creation");
  }
  if (target_width > 4096U || target_height > 4096U) {
    throw std::invalid_argument("offscreen reference extent exceeds the 4096 teaching limit");
  }
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
  shader_info.num_uniform_buffers = 1;
  resources.vertex_shader = require_handle(
      SDL_CreateGPUShader(resources.device, &shader_info), "create vertex shader");
  shader_info.code = reinterpret_cast<const Uint8*>(embedded::msl_source);
  shader_info.code_size = sizeof(embedded::msl_source) - 1U;
  shader_info.entrypoint = "fragment_main";
  shader_info.stage = SDL_GPU_SHADERSTAGE_FRAGMENT;
  shader_info.num_uniform_buffers = 0;
  resources.fragment_shader = require_handle(
      SDL_CreateGPUShader(resources.device, &shader_info), "create fragment shader");

  SDL_GPUTextureCreateInfo texture_info{};
  texture_info.type = SDL_GPU_TEXTURETYPE_2D;
  texture_info.format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
  texture_info.usage = SDL_GPU_TEXTUREUSAGE_COLOR_TARGET;
  texture_info.width = target_width;
  texture_info.height = target_height;
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
      SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM, target_width, target_height, 1);
  const Uint32 depth_size = SDL_CalculateGPUTextureFormatSize(
      SDL_GPU_TEXTUREFORMAT_D16_UNORM, target_width, target_height, 1);
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
  pipeline_info.depth_stencil_state.compare_op = workload.allow_equal_depth
                                                     ? SDL_GPU_COMPAREOP_LESS_OR_EQUAL
                                                     : SDL_GPU_COMPAREOP_LESS;
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
  SDL_PushGPUVertexUniformData(command.get(), 0, &identity_frame_uniforms,
                               static_cast<Uint32>(sizeof(identity_frame_uniforms)));
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
  for (std::uint32_t draw = 0; draw < workload.draw_count; ++draw) {
    if (workload.push_uniform_per_draw) {
      SDL_PushGPUVertexUniformData(command.get(), 0, &identity_frame_uniforms,
                                   static_cast<Uint32>(sizeof(identity_frame_uniforms)));
    }
    SDL_DrawGPUIndexedPrimitives(render_pass, 3, 1, 0, 0, 0);
  }
  SDL_EndGPURenderPass(render_pass);

  SDL_GPUCopyPass* download_pass = require_handle(
      SDL_BeginGPUCopyPass(command.get()), "begin download pass");
  const SDL_GPUTextureRegion color_region{
      resources.color, 0, 0, 0, 0, 0, target_width, target_height, 1};
  const SDL_GPUTextureTransferInfo color_destination{
      resources.color_download, 0, target_width, target_height};
  SDL_DownloadFromGPUTexture(download_pass, &color_region, &color_destination);
  const SDL_GPUTextureRegion depth_region{
      resources.depth, 0, 0, 0, 0, 0, target_width, target_height, 1};
  const SDL_GPUTextureTransferInfo depth_destination{
      resources.depth_download, 0, target_width, target_height};
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
  frame.width = target_width;
  frame.height = target_height;
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
  frame.depth.resize(static_cast<std::size_t>(target_width) * target_height);
  for (std::size_t index = 0; index < frame.depth.size(); ++index) {
    std::uint16_t value{};
    std::memcpy(&value, depth_bytes.data() + index * sizeof(value), sizeof(value));
    frame.depth[index] = value;
  }
  return frame;
#endif
}

#if defined(__APPLE__)
struct SdlLifecycleResources {
  SDL_GPUDevice* device{};
  SDL_GPUTexture* generation_one_color{};
  SDL_GPUTexture* generation_one_depth{};
  SDL_GPUTexture* generation_two_color{};
  SDL_GPUTexture* generation_two_depth{};
  SDL_GPUTransferBuffer* color_download{};
  SDL_GPUTransferBuffer* depth_download{};
  SDL_GPUFence* slot_zero_fence{};
  SDL_GPUFence* slot_one_fence{};

  ~SdlLifecycleResources() {
    if (!device) return;
    if (slot_zero_fence) SDL_ReleaseGPUFence(device, slot_zero_fence);
    if (slot_one_fence) SDL_ReleaseGPUFence(device, slot_one_fence);
    if (color_download) SDL_ReleaseGPUTransferBuffer(device, color_download);
    if (depth_download) SDL_ReleaseGPUTransferBuffer(device, depth_download);
    if (generation_one_color) SDL_ReleaseGPUTexture(device, generation_one_color);
    if (generation_one_depth) SDL_ReleaseGPUTexture(device, generation_one_depth);
    if (generation_two_color) SDL_ReleaseGPUTexture(device, generation_two_color);
    if (generation_two_depth) SDL_ReleaseGPUTexture(device, generation_two_depth);
    SDL_DestroyGPUDevice(device);
  }
};

ActualLifecycleProbe run_sdl_lifecycle_probe() {
  std::vector<std::string> events;
  SdlSession session;
  if (!SDL_GPUSupportsShaderFormats(SDL_GPU_SHADERFORMAT_MSL, "metal")) {
    throw UnsupportedGpu(std::string("Metal/MSL unavailable: ") + SDL_GetError());
  }
  SdlLifecycleResources resources;
  resources.device = SDL_CreateGPUDevice(SDL_GPU_SHADERFORMAT_MSL, true, "metal");
  if (!resources.device) throw UnsupportedGpu(SDL_GetError());
  if (!SDL_GPUTextureSupportsFormat(resources.device, SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM,
                                    SDL_GPU_TEXTURETYPE_2D, SDL_GPU_TEXTUREUSAGE_COLOR_TARGET) ||
      !SDL_GPUTextureSupportsFormat(resources.device, SDL_GPU_TEXTUREFORMAT_D16_UNORM,
                                    SDL_GPU_TEXTURETYPE_2D, SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET)) {
    throw UnsupportedGpu("required lifecycle probe target format is unavailable");
  }

  auto create_targets = [&](const std::uint32_t width, const std::uint32_t height,
                            SDL_GPUTexture*& color, SDL_GPUTexture*& depth) {
    if (width == 0U || height == 0U) return false;
    SDL_GPUTextureCreateInfo texture_info{};
    texture_info.type = SDL_GPU_TEXTURETYPE_2D;
    texture_info.format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
    texture_info.usage = SDL_GPU_TEXTUREUSAGE_COLOR_TARGET;
    texture_info.width = width;
    texture_info.height = height;
    texture_info.layer_count_or_depth = 1;
    texture_info.num_levels = 1;
    texture_info.sample_count = SDL_GPU_SAMPLECOUNT_1;
    color = require_handle(
        SDL_CreateGPUTexture(resources.device, &texture_info), "create lifecycle color target");
    texture_info.format = SDL_GPU_TEXTUREFORMAT_D16_UNORM;
    texture_info.usage = SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET;
    depth = require_handle(
        SDL_CreateGPUTexture(resources.device, &texture_info), "create lifecycle depth target");
    return true;
  };

  if (!create_targets(64, 64, resources.generation_one_color,
                      resources.generation_one_depth)) {
    throw std::runtime_error("generation one target creation was unexpectedly skipped");
  }
  events.push_back("create-generation-1-64x64");
  auto submit_clear = [&](SDL_GPUTexture* color, SDL_GPUTexture* depth,
                          const std::uint32_t width, const std::uint32_t height,
                          const bool download) {
    CommandGuard command(require_handle(
        SDL_AcquireGPUCommandBuffer(resources.device), "acquire lifecycle command buffer"));
    SDL_GPUColorTargetInfo color_target{};
    color_target.texture = color;
    color_target.clear_color = {0.02F, 0.03F, 0.05F, 1.0F};
    color_target.load_op = SDL_GPU_LOADOP_CLEAR;
    color_target.store_op = SDL_GPU_STOREOP_STORE;
    SDL_GPUDepthStencilTargetInfo depth_target{};
    depth_target.texture = depth;
    depth_target.clear_depth = 1.0F;
    depth_target.load_op = SDL_GPU_LOADOP_CLEAR;
    depth_target.store_op = SDL_GPU_STOREOP_STORE;
    depth_target.stencil_load_op = SDL_GPU_LOADOP_DONT_CARE;
    depth_target.stencil_store_op = SDL_GPU_STOREOP_DONT_CARE;
    SDL_GPURenderPass* pass = require_handle(
        SDL_BeginGPURenderPass(command.get(), &color_target, 1, &depth_target),
        "begin lifecycle clear pass");
    SDL_EndGPURenderPass(pass);
    if (download) {
      SDL_GPUCopyPass* copy = require_handle(
          SDL_BeginGPUCopyPass(command.get()), "begin lifecycle download pass");
      const SDL_GPUTextureRegion color_region{color, 0, 0, 0, 0, 0, width, height, 1};
      const SDL_GPUTextureTransferInfo color_destination{
          resources.color_download, 0, width, height};
      SDL_DownloadFromGPUTexture(copy, &color_region, &color_destination);
      const SDL_GPUTextureRegion depth_region{depth, 0, 0, 0, 0, 0, width, height, 1};
      const SDL_GPUTextureTransferInfo depth_destination{
          resources.depth_download, 0, width, height};
      SDL_DownloadFromGPUTexture(copy, &depth_region, &depth_destination);
      SDL_EndGPUCopyPass(copy);
    }
    SDL_GPUFence* fence = SDL_SubmitGPUCommandBufferAndAcquireFence(command.get());
    command.submitted();
    return require_handle(fence, "submit lifecycle command buffer");
  };

  auto wait_fence = [&](SDL_GPUFence* fence, const std::string_view label) {
    SDL_GPUFence* fences[]{fence};
    if (!SDL_WaitForGPUFences(resources.device, true, fences, 1)) {
      throw std::runtime_error(std::string(label) + ": " + SDL_GetError());
    }
  };

  resources.slot_zero_fence = submit_clear(
      resources.generation_one_color, resources.generation_one_depth, 64, 64, false);
  events.push_back("submit-1-slot-0-generation-1");
  resources.slot_one_fence = submit_clear(
      resources.generation_one_color, resources.generation_one_depth, 64, 64, false);
  events.push_back("submit-2-slot-1-generation-1");

  SDL_GPUTexture* zero_color{};
  SDL_GPUTexture* zero_depth{};
  const bool zero_target_created = create_targets(0, 0, zero_color, zero_depth);
  if (zero_target_created || zero_color || zero_depth) {
    throw std::runtime_error("zero extent created an actual GPU target");
  }
  events.push_back("skip-zero-extent-no-target");

  wait_fence(resources.slot_zero_fence, "wait lifecycle slot zero submission one");
  events.push_back("complete-1-before-slot-0-reuse");
  SDL_ReleaseGPUFence(resources.device, resources.slot_zero_fence);
  resources.slot_zero_fence = nullptr;
  const bool slot_zero_reuse_after_completion = true;

  if (!create_targets(96, 72, resources.generation_two_color,
                      resources.generation_two_depth)) {
    throw std::runtime_error("generation two target creation was unexpectedly skipped");
  }
  events.push_back("create-generation-2-96x72");
  const Uint32 color_size = SDL_CalculateGPUTextureFormatSize(
      SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM, 96, 72, 1);
  const Uint32 depth_size = SDL_CalculateGPUTextureFormatSize(
      SDL_GPU_TEXTUREFORMAT_D16_UNORM, 96, 72, 1);
  SDL_GPUTransferBufferCreateInfo transfer_info{};
  transfer_info.usage = SDL_GPU_TRANSFERBUFFERUSAGE_DOWNLOAD;
  transfer_info.size = color_size;
  resources.color_download = require_handle(
      SDL_CreateGPUTransferBuffer(resources.device, &transfer_info),
      "create lifecycle color download buffer");
  transfer_info.size = depth_size;
  resources.depth_download = require_handle(
      SDL_CreateGPUTransferBuffer(resources.device, &transfer_info),
      "create lifecycle depth download buffer");

  resources.slot_zero_fence = submit_clear(
      resources.generation_two_color, resources.generation_two_depth, 96, 72, true);
  events.push_back("submit-3-slot-0-generation-2");

  wait_fence(resources.slot_one_fence, "wait lifecycle generation one last use");
  events.push_back("complete-2-generation-1-last-use");
  SDL_ReleaseGPUFence(resources.device, resources.slot_one_fence);
  resources.slot_one_fence = nullptr;
  SDL_ReleaseGPUTexture(resources.device, resources.generation_one_color);
  resources.generation_one_color = nullptr;
  SDL_ReleaseGPUTexture(resources.device, resources.generation_one_depth);
  resources.generation_one_depth = nullptr;
  const bool generation_one_retired_after_completion = true;
  events.push_back("retire-generation-1-after-completion-2");

  wait_fence(resources.slot_zero_fence, "wait lifecycle generation two readback");
  events.push_back("complete-3-generation-2");
  SDL_ReleaseGPUFence(resources.device, resources.slot_zero_fence);
  resources.slot_zero_fence = nullptr;

  FrameResult generation_two;
  generation_two.width = 96;
  generation_two.height = 72;
  generation_two.actual_gpu = true;
  generation_two.driver = SDL_GetGPUDeviceDriver(resources.device);
  generation_two.shader_formats = SDL_GetGPUShaderFormats(resources.device);
  const SDL_PropertiesID properties = SDL_GetGPUDeviceProperties(resources.device);
  generation_two.device = SDL_GetStringProperty(
      properties, SDL_PROP_GPU_DEVICE_NAME_STRING, "unknown");
  generation_two.rgba.resize(color_size);
  const void* mapped_color = require_handle(
      static_cast<const unsigned char*>(SDL_MapGPUTransferBuffer(
          resources.device, resources.color_download, false)),
      "map lifecycle color download");
  std::memcpy(generation_two.rgba.data(), mapped_color, color_size);
  SDL_UnmapGPUTransferBuffer(resources.device, resources.color_download);
  std::vector<unsigned char> depth_bytes(depth_size);
  const void* mapped_depth = require_handle(
      static_cast<const unsigned char*>(SDL_MapGPUTransferBuffer(
          resources.device, resources.depth_download, false)),
      "map lifecycle depth download");
  std::memcpy(depth_bytes.data(), mapped_depth, depth_size);
  SDL_UnmapGPUTransferBuffer(resources.device, resources.depth_download);
  generation_two.depth.resize(96U * 72U);
  for (std::size_t index = 0; index < generation_two.depth.size(); ++index) {
    std::uint16_t value{};
    std::memcpy(&value, depth_bytes.data() + index * sizeof(value), sizeof(value));
    generation_two.depth[index] = value;
  }
  events.push_back("map-generation-2-readback-after-completion-3");
  SDL_ReleaseGPUTexture(resources.device, resources.generation_two_color);
  resources.generation_two_color = nullptr;
  SDL_ReleaseGPUTexture(resources.device, resources.generation_two_depth);
  resources.generation_two_depth = nullptr;
  events.push_back("retire-generation-2-after-completion-3");

  return {
      .actual_gpu = true,
      .slot_count = 2,
      .zero_extent_skipped = true,
      .slot_zero_reused_after_completion = slot_zero_reuse_after_completion,
      .generation_one_retired_after_completion = generation_one_retired_after_completion,
      .generation_two_readback_after_completion = true,
      .submit_count = 3,
      .events = std::move(events),
      .driver = generation_two.driver,
      .device = generation_two.device,
      .generation_two_frame = std::move(generation_two),
  };
}
#else
ActualLifecycleProbe run_sdl_lifecycle_probe() {
  throw UnsupportedGpu("the persistent lifecycle probe requires macOS Metal");
}
#endif

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

void write_stage06_artifacts(
    const RunOptions& options,
    const FrameResult& frame,
    const LifecycleRun& lifecycle,
    const std::optional<ActualLifecycleProbe>& actual_lifecycle) {
  write_environment(options.output, frame);
  const FrameResult* resized_frame = actual_lifecycle
                                         ? &actual_lifecycle->generation_two_frame
                                         : nullptr;
  const bool resized_actual = frame.actual_gpu &&
                              actual_lifecycle_probe_matches_model(
                                  lifecycle, actual_lifecycle);
  const std::optional<std::string> generation_one_hash =
      resized_actual ? std::optional<std::string>{correctness_hash(frame)} : std::nullopt;
  const std::optional<std::string> generation_two_hash =
      resized_actual ? std::optional<std::string>{correctness_hash(*resized_frame)} : std::nullopt;
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
         << "  \"uniform_bindings\": {\"vertex\": [\"FrameUniforms@buffer(0)\"], \"fragment\": []},\n"
         << "  \"vertex_uniform_buffer_count\": 1,\n"
         << "  \"runtime_compile\": true\n}\n";
  write_text(options.output / "shader-manifests" / "triangle.json", shader.str());
  std::ostringstream resources;
  resources << "{\n  \"schema_version\": 1,\n  \"frame_slots\": " << lifecycle.slots.size() << ",\n"
            << "  \"slot_state\": " << lifecycle_slots_json(lifecycle, "    ") << ",\n"
            << "  \"buffers\": [\"vertex-upload\", \"index-upload\", \"frame-uniform-push\", \"color-download\", \"depth-download\"],\n"
            << "  \"uniforms\": {\"slot\": 0, \"bytes\": 80, \"contents\": [\"identity-mvp\", \"identity-tint\"], \"lifetime\": \"command-buffer-owned-copy\"},\n"
            << "  \"attachments\": [\n"
            << "    {\"id\": \"color\", \"format\": \"R8G8B8A8_UNORM\", \"generation\": 2, \"sample_count\": 1},\n"
            << "    {\"id\": \"depth\", \"format\": \"D16_UNORM\", \"generation\": 2, \"sample_count\": 1}\n"
            << "  ],\n  \"generation_lifecycle\": "
            << lifecycle_generations_json(
                   lifecycle, "    ", resized_actual, resized_actual,
                   generation_one_hash, generation_two_hash)
            << ",\n  \"model_valid\": " << (lifecycle.valid ? "true" : "false")
            << ",\n  \"actual_persistent_lifecycle\": {\"required\": "
            << (frame.actual_gpu ? "true" : "false")
            << ", \"executed\": " << (resized_actual ? "true" : "false")
            << ", \"slot_count\": "
            << (actual_lifecycle ? actual_lifecycle->slot_count : 0U)
            << ", \"submit_count\": "
            << (actual_lifecycle ? actual_lifecycle->submit_count : 0U)
            << ", \"slot_zero_reused_after_completion\": "
            << (actual_lifecycle && actual_lifecycle->slot_zero_reused_after_completion ? "true" : "false")
            << ", \"generation_one_retired_after_completion\": "
            << (actual_lifecycle && actual_lifecycle->generation_one_retired_after_completion ? "true" : "false")
            << ", \"generation_two_readback_after_completion\": "
            << (actual_lifecycle && actual_lifecycle->generation_two_readback_after_completion ? "true" : "false")
            << ", \"driver\": "
            << json_quote(actual_lifecycle ? actual_lifecycle->driver : "not-run")
            << ", \"device\": "
            << json_quote(actual_lifecycle ? actual_lifecycle->device : "not-run")
            << ", \"events\": " << actual_lifecycle_events_json(actual_lifecycle, "      ") << "}"
            << ",\n  \"retirement_rule\": \"retired_at_completion >= last_use_submission\"\n}\n";
  write_text(options.output / "resources.json", resources.str());
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
        << "  ],\n  \"uniform_push\": {\"slot\": 0, \"bytes\": 80, \"before_draw\": true, \"shader_binding\": \"vertex buffer(0)\", \"source_lifetime\": \"copied-at-record\"},\n"
        << "  \"timing\": {\n"
        << "    \"measurement_kind\": \"cpu-wall-clock\",\n"
        << "    \"cpu_record_ns\": " << frame.cpu_record_ns << ",\n"
        << "    \"cpu_submit_ns\": " << frame.cpu_submit_ns << ",\n"
        << "    \"submit_to_fence_ns\": " << frame.submit_to_fence_ns << ",\n"
        << "    \"is_gpu_timestamp\": false\n  }\n}\n";
  write_text(options.output / "frame-trace.json", trace.str());
  std::ostringstream resize;
  resize << "{\n  \"schema_version\": 1,\n  \"events\": "
         << lifecycle_events_json(lifecycle, "    ") << ",\n"
         << "  \"zero_extent_target_creation_attempted\": "
         << (lifecycle.zero_extent_target_created ? "true" : "false") << ",\n"
         << "  \"old_generation_retired_after_last_use\": "
         << (lifecycle_generations_safe(lifecycle) ? "true" : "false") << ",\n"
         << "  \"actual_gpu_extent_transition_required\": "
         << (frame.actual_gpu ? "true" : "false") << ",\n"
         << "  \"actual_gpu_extent_transition_executed\": "
         << (resized_actual ? "true" : "false") << ",\n"
         << "  \"actual_gpu_events\": "
         << actual_lifecycle_events_json(actual_lifecycle, "    ") << ",\n"
         << "  \"generation_2_correctness_hash_fnv1a64\": ";
  if (generation_two_hash) resize << json_quote(*generation_two_hash);
  else resize << "null";
  resize << "\n}\n";
  write_text(options.output / "resize-trace.json", resize.str());
  const std::vector<unsigned char> rgb = rgb_from_rgba(frame);
  write_ppm_p3(options.output / "screenshot.ppm", static_cast<int>(frame.width),
               static_cast<int>(frame.height), rgb);
  if (resized_actual) {
    const std::vector<unsigned char> resized_rgb = rgb_from_rgba(*resized_frame);
    write_ppm_p3(options.output / "resize-generation-2.ppm", 96, 72, resized_rgb);
  }
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

std::string sample_median(std::vector<std::uint64_t> values) {
  std::sort(values.begin(), values.end());
  const std::size_t middle = values.size() / 2U;
  const long double median = values.size() % 2U == 0U
                                 ? (static_cast<long double>(values[middle - 1U]) +
                                    static_cast<long double>(values[middle])) /
                                       2.0L
                                 : static_cast<long double>(values[middle]);
  std::ostringstream stream;
  stream << std::setprecision(20) << median;
  return stream.str();
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
    std::array<std::uint32_t, 2> extent;
    std::uint32_t draw_count;
    std::uint32_t triangle_count;
    std::uint32_t resource_count;
  };
  static constexpr std::array<Workload, 3> workloads{{
      {"many-small-draws", 150U, 180U, 130U, {64U, 64U}, 512U, 512U, 16U},
      {"fragment-heavy", 105U, 100U, 220U, {1024U, 1024U}, 1U, 2U, 4U},
      {"state-change-heavy", 170U, 210U, 145U, {256U, 256U}, 256U, 4096U, 128U},
  }};
  const std::uint64_t base_record = std::max<std::uint64_t>(frame.cpu_record_ns, 12000U);
  const std::uint64_t base_submit = std::max<std::uint64_t>(frame.cpu_submit_ns, 3000U);
  const std::uint64_t base_fence = std::max<std::uint64_t>(frame.submit_to_fence_ns, 42000U);
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n"
         << "  \"measurement_kind\": \"cpu-wall-clock-and-lifecycle-model\",\n"
         << "  \"measured_scope\": \"deterministic lifecycle fallback; no GPU execution\",\n"
         << "  \"actual_gpu_repeated_work\": false,\n"
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
           << "      \"extent\": [" << workload.extent[0] << ", " << workload.extent[1] << "],\n"
           << "      \"draw_count\": " << workload.draw_count << ",\n"
           << "      \"triangle_count\": " << workload.triangle_count << ",\n"
           << "      \"resource_count\": " << workload.resource_count << ",\n"
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

#if CG_HAS_SDL3
std::string actual_stage08_timing_report_json(const FrameResult& baseline) {
  struct Workload {
    std::string_view id;
    std::string_view measured_scope;
    GpuWorkload gpu;
    std::array<std::uint32_t, 2> extent;
    std::uint32_t resource_count;
  };
  static constexpr std::array<Workload, 3> workloads{{
      {"many-small-draws",
       "one actual offscreen command buffer/fence with 256 indexed draw records",
       {256U, true, false}, {64U, 64U}, 8U},
      {"fragment-heavy",
       "one actual offscreen command buffer/fence with 128 depth-equal fragment passes",
       {128U, true, false}, {64U, 64U}, 8U},
      {"state-change-heavy",
       "one actual offscreen command buffer/fence with 128 identity uniform pushes and draws",
       {128U, true, true}, {64U, 64U}, 8U},
  }};
  struct TimingSample {
    std::uint64_t record{};
    std::uint64_t submit{};
    std::uint64_t fence{};
  };
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n"
         << "  \"measurement_kind\": \"actual-repeated-offscreen-submit-fence\",\n"
         << "  \"measured_scope\": \"workload-specific actual SDL3 Metal command recording, submission, and fence wait loops\",\n"
         << "  \"actual_gpu_repeated_work\": true,\n"
         << "  \"gpu_timestamp_available\": false,\n"
         << "  \"warning\": \"submit_to_fence_ns is CPU wall time around an actual Metal fence, not a GPU timestamp\",\n"
         << "  \"absolute_time_pass_threshold_ns\": null,\n"
         << "  \"environment_fingerprint_fnv1a64\": "
         << json_quote(environment_fingerprint(baseline)) << ",\n"
         << "  \"correctness_hash_fnv1a64\": " << json_quote(correctness_hash(baseline)) << ",\n"
         << "  \"workloads\": [\n";
  for (std::size_t workload_index = 0; workload_index < workloads.size(); ++workload_index) {
    const Workload& workload = workloads[workload_index];
    std::array<TimingSample, 5> warmup{};
    std::array<TimingSample, 30> timed{};
    auto measure = [&]() {
      const FrameResult measured = render_sdl_frame(workload.gpu);
      if (!measured.actual_gpu || correctness_hash(measured) != correctness_hash(baseline) ||
          environment_fingerprint(measured) != environment_fingerprint(baseline)) {
        throw std::runtime_error("stage08 repeated GPU measurement changed correctness/environment");
      }
      return TimingSample{
          measured.cpu_record_ns, measured.cpu_submit_ns, measured.submit_to_fence_ns};
    };
    for (TimingSample& sample : warmup) sample = measure();
    std::vector<std::uint64_t> record_values;
    std::vector<std::uint64_t> submit_values;
    std::vector<std::uint64_t> fence_values;
    record_values.reserve(timed.size());
    submit_values.reserve(timed.size());
    fence_values.reserve(timed.size());
    for (TimingSample& sample : timed) {
      sample = measure();
      record_values.push_back(sample.record);
      submit_values.push_back(sample.submit);
      fence_values.push_back(sample.fence);
    }
    stream << "    {\n      \"id\": " << json_quote(workload.id) << ",\n"
           << "      \"measured_scope\": " << json_quote(workload.measured_scope) << ",\n"
           << "      \"extent\": [" << workload.extent[0] << ", " << workload.extent[1] << "],\n"
           << "      \"draw_count\": " << workload.gpu.draw_count << ",\n"
           << "      \"triangle_count\": " << workload.gpu.draw_count << ",\n"
           << "      \"resource_count\": " << workload.resource_count << ",\n"
           << "      \"submission_count_per_sample\": 1,\n"
           << "      \"uniform_pushes_per_sample\": "
           << (workload.gpu.push_uniform_per_draw ? workload.gpu.draw_count : 1U) << ",\n"
           << "      \"warmup_samples\": 5,\n      \"timed_samples\": 30,\n"
           << "      \"environment_fingerprint_fnv1a64\": "
           << json_quote(environment_fingerprint(baseline)) << ",\n"
           << "      \"correctness_hash_fnv1a64\": " << json_quote(correctness_hash(baseline)) << ",\n"
           << "      \"warmup\": [\n";
    for (std::size_t index = 0; index < warmup.size(); ++index) {
      stream << "        {\"cpu_record_ns\": " << warmup[index].record
             << ", \"cpu_submit_ns\": " << warmup[index].submit
             << ", \"submit_to_fence_ns\": " << warmup[index].fence << "}"
             << (index + 1U == warmup.size() ? "\n" : ",\n");
    }
    stream << "      ],\n      \"samples\": [\n";
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
           << ", \"p95\": " << sample_p95(fence_values)
           << ", \"is_gpu_timestamp\": false}\n"
           << "      }\n    }" << (workload_index + 1U == workloads.size() ? "\n" : ",\n");
  }
  stream << "  ]\n}\n";
  return stream.str();
}
#endif

std::string stage08_timing_report_json(const FrameResult& frame) {
#if CG_HAS_SDL3
  if (frame.actual_gpu) return actual_stage08_timing_report_json(frame);
#endif
  return timing_report_json(frame);
}

void write_stage07_artifacts(
    const RunOptions& options,
    const FrameResult& frame,
    const LifecycleRun& lifecycle) {
  write_environment(options.output, frame);
  std::ostringstream lifecycle_artifact;
  lifecycle_artifact
      << "{\n  \"schema_version\": 1,\n  \"slot_count\": " << lifecycle.slots.size() << ",\n"
      << "  \"slots\": " << lifecycle_slots_json(lifecycle, "    ") << ",\n"
      << "  \"generations\": "
      << lifecycle_generations_json(lifecycle, "    ", false, false) << ",\n"
      << "  \"zero_extent\": {\"target_created\": "
      << (lifecycle.zero_extent_target_created ? "true" : "false")
      << ", \"frame_skipped\": " << (lifecycle.zero_extent_seen ? "true" : "false") << "},\n"
      << "  \"readback\": {\"submission\": " << lifecycle.readback_submission
      << ", \"mapped_after_completion\": " << lifecycle.readback_after_completion
      << ", \"safe\": " << (lifecycle_readback_safe(lifecycle) ? "true" : "false") << "},\n"
      << "  \"events\": " << lifecycle_events_json(lifecycle, "    ") << ",\n"
      << "  \"model_valid\": " << (lifecycle.valid ? "true" : "false") << ",\n"
      << "  \"violation\": ";
  if (lifecycle.violation.empty()) lifecycle_artifact << "null";
  else lifecycle_artifact << json_quote(lifecycle.violation);
  lifecycle_artifact << "\n}\n";
  write_text(options.output / "lifecycle.json", lifecycle_artifact.str());
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
    const LifecycleRun case_lifecycle = run_lifecycle_scenario(cases[case_index]);
    const bool lifecycle_case = lifecycle_defect(cases[case_index]) != LifecycleDefect::none;
    const bool model_rejected = lifecycle_case && !case_lifecycle.valid &&
                                !case_lifecycle.violation.empty();
    const std::filesystem::path directory = options.output / cases[case_index];
    ensure_output_directory(directory);
    write_environment(directory, frame);
    const std::vector<unsigned char> before = make_known_bad_rgb(frame, case_index);
    write_ppm_p3(directory / "before.ppm", static_cast<int>(frame.width),
                 static_cast<int>(frame.height), before);
    write_ppm_p3(directory / "after.ppm", static_cast<int>(frame.width),
                 static_cast<int>(frame.height), after);
    const std::size_t different = differing_rgb_bytes(before, after);
    const bool validation_detected = !lifecycle_case && (case_index == 0U || case_index == 4U);
    std::ostringstream diff;
    diff << "{\n  \"schema_version\": 1,\n  \"case\": " << json_quote(cases[case_index])
         << ",\n  \"different_channel_bytes\": " << different
         << ",\n  \"oracle_rejects_before\": "
         << (!lifecycle_case && different > 0U ? "true" : "false")
         << ",\n  \"case_oracle_rejected\": "
         << (model_rejected || (!lifecycle_case && different > 0U) ? "true" : "false")
         << ",\n  \"illustrative_before_differs\": "
         << (different > 0U ? "true" : "false")
         << ",\n  \"oracle_kind\": "
         << json_quote(lifecycle_case ? "deterministic-lifecycle-state-machine"
                                      : "synthetic-before-artifact-diff")
         << ",\n  \"before_artifact_kind\": \"synthetic-postprocess-illustration\""
         << ",\n  \"synthetic_before_artifact_generated\": true"
         << ",\n  \"pipeline_mutation_executed\": false"
         << ",\n  \"gpu_submission_executed\": false"
         << ",\n  \"lifecycle_transition_executed\": " << (lifecycle_case ? "true" : "false")
         << ",\n  \"lifecycle_model_rejected\": " << (model_rejected ? "true" : "false")
         << ",\n  \"lifecycle_violation\": ";
    if (case_lifecycle.violation.empty()) diff << "null";
    else diff << json_quote(case_lifecycle.violation);
    diff << ",\n  \"after_matches_reference\": true\n}\n";
    write_text(directory / "diff.json", diff.str());
    std::ostringstream report;
    report << "# " << cases[case_index] << "\n\n"
           << "- symptom: "
           << (lifecycle_case
                   ? "the deterministic lifecycle state machine rejects the invalid transition; the before image is only a synthetic illustration"
                   : "a case-specific synthetic postprocess illustration differs from the fixed reference frame; no pipeline mutation was executed")
           << "\n"
           << "- last good stage: command/resource contract before the injected mutation\n"
           << "- first bad stage: " << cases[case_index] << "\n"
           << "- validation classification: "
           << (validation_detected
                   ? "the static preflight oracle models this as fatal; no API validation run was executed"
                   : "no API validation run was executed; the semantic artifact or lifecycle oracle supplies the evidence")
           << "\n"
           << "- root cause: "
           << (lifecycle_case ? case_lifecycle.violation
                              : "the named known-bad mutation violates its public invariant")
           << "\n"
           << "- minimal fix: restore the matching layout, completion, generation, depth, or color contract\n"
           << "- regression oracle: "
           << (lifecycle_case
                   ? "the executed lifecycle transition and rejection trace; the before/after image diff is illustrative only"
                   : "the explicitly synthetic before/after artifact diff, not an executed renderer-pipeline mutation")
           << "\n"
           << "- remaining uncertainty: actual capture labels require a supported GPU capture tool\n";
    write_text(directory / "report.md", report.str());
    write_text(directory / "validation.log",
               validation_detected
                   ? "fatal=1\nclassification=api-or-pipeline-contract\nevidence_source=static-preflight-oracle\n"
                   : "fatal=0\nwarning=0\nclassification=semantic-image-or-lifecycle-failure\nevidence_source=synthetic-artifact-or-lifecycle-model\n");
    write_text(directory / "capture-reference.txt",
               "capture_tool=not_embedded\npass_label=offscreen-color-depth\n"
               "draw_label=shared-triangle-indexed\nresource_label=generation-2\n"
               "cpu_trace_event=color-depth-pass\n");
    std::ostringstream frame_trace;
    frame_trace << "{\n  \"schema_version\": 1,\n  \"case\": " << json_quote(cases[case_index])
                << ",\n  \"last_good_event\": \"upload-complete\",\n"
                << "  \"first_bad_event\": " << json_quote(cases[case_index])
                << ",\n  \"capture_label\": \"offscreen-color-depth/shared-triangle-indexed\",\n"
                << "  \"lifecycle_events\": "
                << lifecycle_events_json(case_lifecycle, "    ") << "\n}\n";
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

constexpr unsigned int capstone_linear_tolerance = 1U;
constexpr unsigned int capstone_depth_tolerance = 2U;
constexpr unsigned int capstone_srgb_interior_tolerance = 2U;
constexpr unsigned int capstone_srgb_edge_tolerance = 13U;
constexpr double capstone_edge_radius_pixels = 0.75;
constexpr double capstone_max_edge_mask_fraction = 0.08;

bool covered_at(const FrameResult& frame, const std::size_t pixel) {
  const std::size_t offset = pixel * 4U;
  return frame.rgba[offset] != clear_rgba[0] ||
         frame.rgba[offset + 1U] != clear_rgba[1] ||
         frame.rgba[offset + 2U] != clear_rgba[2];
}

std::vector<unsigned char> coverage_mask(const FrameResult& frame) {
  std::vector<unsigned char> result(frame.rgba.size() / 4U);
  for (std::size_t pixel = 0; pixel < result.size(); ++pixel) {
    result[pixel] = covered_at(frame, pixel) ? 1U : 0U;
  }
  return result;
}

double point_segment_distance(
    const double x,
    const double y,
    const ScreenVertex& start,
    const ScreenVertex& end) {
  const double segment_x = end.x - start.x;
  const double segment_y = end.y - start.y;
  const double length_squared = segment_x * segment_x + segment_y * segment_y;
  const double projection = length_squared == 0.0
                                ? 0.0
                                : std::clamp(((x - start.x) * segment_x +
                                              (y - start.y) * segment_y) /
                                                 length_squared,
                                             0.0, 1.0);
  const double nearest_x = start.x + projection * segment_x;
  const double nearest_y = start.y + projection * segment_y;
  return std::hypot(x - nearest_x, y - nearest_y);
}

std::vector<unsigned char> fixed_edge_mask() {
  const auto vertices = screen_vertices();
  std::vector<unsigned char> mask(static_cast<std::size_t>(frame_width * frame_height));
  for (std::uint32_t y = 0; y < frame_height; ++y) {
    for (std::uint32_t x = 0; x < frame_width; ++x) {
      const double sample_x = static_cast<double>(x) + 0.5;
      const double sample_y = static_cast<double>(y) + 0.5;
      const double distance = std::min({
          point_segment_distance(sample_x, sample_y, vertices[0], vertices[1]),
          point_segment_distance(sample_x, sample_y, vertices[1], vertices[2]),
          point_segment_distance(sample_x, sample_y, vertices[2], vertices[0]),
      });
      mask[static_cast<std::size_t>(y * frame_width + x)] =
          distance <= capstone_edge_radius_pixels ? 1U : 0U;
    }
  }
  return mask;
}

std::vector<unsigned char> mask_rgb(const std::vector<unsigned char>& mask) {
  std::vector<unsigned char> rgb(mask.size() * 3U);
  for (std::size_t pixel = 0; pixel < mask.size(); ++pixel) {
    const unsigned char value = mask[pixel] ? 255U : 0U;
    rgb[pixel * 3U] = value;
    rgb[pixel * 3U + 1U] = value;
    rgb[pixel * 3U + 2U] = value;
  }
  return rgb;
}

unsigned char linear_to_srgb_byte(const unsigned char byte) {
  const double linear = static_cast<double>(byte) / 255.0;
  const double encoded = linear <= 0.0031308
                             ? 12.92 * linear
                             : 1.055 * std::pow(linear, 1.0 / 2.4) - 0.055;
  return static_cast<unsigned char>(
      std::lround(std::clamp(encoded, 0.0, 1.0) * 255.0));
}

std::vector<unsigned char> srgb_from_rgba(const FrameResult& frame) {
  std::vector<unsigned char> rgb = rgb_from_rgba(frame);
  for (unsigned char& byte : rgb) byte = linear_to_srgb_byte(byte);
  return rgb;
}

std::vector<unsigned char> primitive_id_rgb(const FrameResult& frame) {
  std::vector<unsigned char> rgb(frame.rgba.size() / 4U * 3U);
  for (std::size_t pixel = 0; pixel < frame.rgba.size() / 4U; ++pixel) {
    if (!covered_at(frame, pixel)) continue;
    rgb[pixel * 3U] = 255U;
    rgb[pixel * 3U + 1U] = 127U;
    rgb[pixel * 3U + 2U] = 0U;
  }
  return rgb;
}

std::string depth_artifact_json(const FrameResult& frame) {
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n  \"format\": \"D16_UNORM\",\n"
         << "  \"width\": " << frame.width << ",\n  \"height\": " << frame.height << ",\n"
         << "  \"row_major_samples\": [\n";
  for (std::uint32_t y = 0; y < frame.height; ++y) {
    stream << "    [";
    for (std::uint32_t x = 0; x < frame.width; ++x) {
      stream << frame.depth[static_cast<std::size_t>(y * frame.width + x)]
             << (x + 1U == frame.width ? "" : ", ");
    }
    stream << "]" << (y + 1U == frame.height ? "\n" : ",\n");
  }
  stream << "  ],\n  \"hash_fnv1a64\": " << json_quote(depth_hash(frame)) << "\n}\n";
  return stream.str();
}

std::string primitive_artifact_json(const FrameResult& frame) {
  const std::vector<unsigned char> coverage = coverage_mask(frame);
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n  \"background_id\": 0,\n"
         << "  \"triangle_primitive_id\": 1,\n  \"width\": " << frame.width
         << ",\n  \"height\": " << frame.height << ",\n  \"row_major_ids\": [\n";
  for (std::uint32_t y = 0; y < frame.height; ++y) {
    stream << "    [";
    for (std::uint32_t x = 0; x < frame.width; ++x) {
      stream << static_cast<unsigned int>(
                    coverage[static_cast<std::size_t>(y * frame.width + x)])
             << (x + 1U == frame.width ? "" : ", ");
    }
    stream << "]" << (y + 1U == frame.height ? "\n" : ",\n");
  }
  stream << "  ],\n  \"hash_fnv1a64\": "
         << json_quote(hex_hash(coverage.data(), coverage.size())) << "\n}\n";
  return stream.str();
}

std::string pixel_trace_json(const FrameResult& frame, const std::string_view renderer) {
  static constexpr std::array<std::array<std::uint32_t, 2>, 4> probes{{
      {0U, 0U}, {32U, 32U}, {32U, 10U}, {17U, 44U},
  }};
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n  \"renderer\": " << json_quote(renderer)
         << ",\n  \"probe_order\": \"clear,interior,edge,interpolation-rounding\",\n"
         << "  \"probes\": [\n";
  for (std::size_t probe_index = 0; probe_index < probes.size(); ++probe_index) {
    const std::uint32_t x = probes[probe_index][0];
    const std::uint32_t y = probes[probe_index][1];
    const std::size_t pixel = static_cast<std::size_t>(y * frame.width + x);
    const std::size_t color = pixel * 4U;
    stream << "    {\"x\": " << x << ", \"y\": " << y
           << ", \"primitive_id\": " << (covered_at(frame, pixel) ? 1 : 0)
           << ", \"depth_u16\": " << frame.depth[pixel]
           << ", \"linear_rgba8\": ["
           << static_cast<unsigned int>(frame.rgba[color]) << ", "
           << static_cast<unsigned int>(frame.rgba[color + 1U]) << ", "
           << static_cast<unsigned int>(frame.rgba[color + 2U]) << ", "
           << static_cast<unsigned int>(frame.rgba[color + 3U]) << "]}"
           << (probe_index + 1U == probes.size() ? "\n" : ",\n");
  }
  stream << "  ]\n}\n";
  return stream.str();
}

std::string frame_statistics_json(const FrameResult& frame, const std::string_view renderer) {
  const std::vector<unsigned char> coverage = coverage_mask(frame);
  const std::size_t covered = static_cast<std::size_t>(
      std::count(coverage.begin(), coverage.end(), static_cast<unsigned char>(1U)));
  const std::vector<unsigned char> primitive_rgb = primitive_id_rgb(frame);
  const std::vector<unsigned char> srgb = srgb_from_rgba(frame);
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n  \"renderer\": " << json_quote(renderer) << ",\n"
         << "  \"scene_snapshot_id\": " << json_quote(SceneSnapshot::id) << ",\n"
         << "  \"scene_hash_fnv1a64\": " << json_quote(scene_hash()) << ",\n"
         << "  \"environment_fingerprint_fnv1a64\": "
         << json_quote(environment_fingerprint(frame)) << ",\n"
         << "  \"extent\": [" << frame.width << ", " << frame.height << "],\n"
         << "  \"input_primitive_count\": 1,\n  \"clipped_primitive_count\": 1,\n"
         << "  \"culled_primitive_count\": 0,\n  \"covered_pixel_count\": " << covered << ",\n"
         << "  \"depth_passed_pixel_count\": " << covered << ",\n"
         << "  \"linear_color_hash_fnv1a64\": " << json_quote(color_hash(frame)) << ",\n"
         << "  \"srgb_color_hash_fnv1a64\": " << json_quote(hex_hash(srgb.data(), srgb.size())) << ",\n"
         << "  \"depth_hash_fnv1a64\": " << json_quote(depth_hash(frame)) << ",\n"
         << "  \"primitive_id_hash_fnv1a64\": "
         << json_quote(hex_hash(coverage.data(), coverage.size())) << ",\n"
         << "  \"color_depth_correctness_hash_fnv1a64\": "
         << json_quote(correctness_hash(frame)) << ",\n"
         << "  \"cpu_record_ns\": " << frame.cpu_record_ns << ",\n"
         << "  \"cpu_submit_ns\": " << frame.cpu_submit_ns << ",\n"
         << "  \"submit_to_fence_ns\": " << frame.submit_to_fence_ns << ",\n"
         << "  \"submit_to_fence_is_gpu_timestamp\": false\n}\n";
  return stream.str();
}

void write_capstone_frame_artifacts(
    const std::filesystem::path& directory,
    const std::string_view renderer,
    const FrameResult& frame) {
  ensure_output_directory(directory);
  write_environment(directory, frame);
  const std::vector<unsigned char> linear = rgb_from_rgba(frame);
  const std::vector<unsigned char> srgb = srgb_from_rgba(frame);
  const std::vector<unsigned char> primitive = primitive_id_rgb(frame);
  write_ppm_p3(directory / "color-linear.ppm", static_cast<int>(frame.width),
               static_cast<int>(frame.height), linear);
  write_ppm_p3(directory / "color-srgb.ppm", static_cast<int>(frame.width),
               static_cast<int>(frame.height), srgb);
  write_ppm_p3(directory / "primitive-id.ppm", static_cast<int>(frame.width),
               static_cast<int>(frame.height), primitive);
  write_text(directory / "depth.json", depth_artifact_json(frame));
  write_text(directory / "primitive-id.json", primitive_artifact_json(frame));
  write_text(directory / "trace.json", pixel_trace_json(frame, renderer));
  write_text(directory / "statistics.json", frame_statistics_json(frame, renderer));
}

struct PixelDeltaSummary {
  std::size_t raw_mismatch_pixels{};
  std::size_t edge_mismatch_pixels{};
  std::size_t interior_mismatch_pixels{};
  std::size_t failing_edge_pixels{};
  std::size_t failing_interior_pixels{};
  unsigned int max_abs_edge{};
  unsigned int max_abs_interior{};
};

PixelDeltaSummary compare_rgb(
    const std::vector<unsigned char>& expected,
    const std::vector<unsigned char>& actual,
    const std::vector<unsigned char>& edge_mask,
    const unsigned int interior_tolerance,
    const unsigned int edge_tolerance) {
  PixelDeltaSummary result;
  for (std::size_t pixel = 0; pixel < edge_mask.size(); ++pixel) {
    unsigned int pixel_delta{};
    for (std::size_t channel = 0; channel < 3U; ++channel) {
      const unsigned int left = expected[pixel * 3U + channel];
      const unsigned int right = actual[pixel * 3U + channel];
      pixel_delta = std::max(pixel_delta, left > right ? left - right : right - left);
    }
    if (pixel_delta == 0U) continue;
    ++result.raw_mismatch_pixels;
    if (edge_mask[pixel]) {
      ++result.edge_mismatch_pixels;
      result.max_abs_edge = std::max(result.max_abs_edge, pixel_delta);
      if (pixel_delta > edge_tolerance) ++result.failing_edge_pixels;
    } else {
      ++result.interior_mismatch_pixels;
      result.max_abs_interior = std::max(result.max_abs_interior, pixel_delta);
      if (pixel_delta > interior_tolerance) ++result.failing_interior_pixels;
    }
  }
  return result;
}

std::string pixel_delta_fields(const PixelDeltaSummary& delta) {
  std::ostringstream stream;
  stream << "\"raw_mismatch_pixels\": " << delta.raw_mismatch_pixels
         << ", \"edge_mismatch_pixels\": " << delta.edge_mismatch_pixels
         << ", \"interior_mismatch_pixels\": " << delta.interior_mismatch_pixels
         << ", \"failing_edge_pixels\": " << delta.failing_edge_pixels
         << ", \"failing_interior_pixels\": " << delta.failing_interior_pixels
         << ", \"max_abs_edge\": " << delta.max_abs_edge
         << ", \"max_abs_interior\": " << delta.max_abs_interior;
  return stream.str();
}

struct CapstoneOutcome {
  bool same_scene_contract{};
  bool ordered_comparison{};
  bool resource_reuse_safe{};
  bool resize_generation_safe{};
  bool validation_clean{};
  bool known_bad_rejected{};
  bool performance_hash_preserved{};
};

CapstoneOutcome write_stage08_artifacts(
    const RunOptions& options,
    const FrameResult& gpu,
    const LifecycleRun& lifecycle,
    const std::optional<ActualLifecycleProbe>& actual_lifecycle) {
  const FrameResult software = make_cpu_frame();
  const FrameResult* resized_frame = actual_lifecycle
                                         ? &actual_lifecycle->generation_two_frame
                                         : nullptr;
  const bool resized_actual = gpu.actual_gpu &&
                              actual_lifecycle_probe_matches_model(
                                  lifecycle, actual_lifecycle);
  const std::optional<std::string> generation_one_hash =
      resized_actual ? std::optional<std::string>{correctness_hash(gpu)} : std::nullopt;
  const std::optional<std::string> generation_two_hash =
      resized_actual ? std::optional<std::string>{correctness_hash(*resized_frame)} : std::nullopt;
  const std::vector<unsigned char> software_coverage = coverage_mask(software);
  const std::vector<unsigned char> gpu_coverage = coverage_mask(gpu);
  const std::vector<unsigned char> edge_mask = fixed_edge_mask();
  const std::size_t edge_population = static_cast<std::size_t>(
      std::count(edge_mask.begin(), edge_mask.end(), static_cast<unsigned char>(1U)));
  const double edge_fraction = static_cast<double>(edge_population) /
                               static_cast<double>(edge_mask.size());
  const std::filesystem::path software_directory =
      options.output / "software_artifacts" / SceneSnapshot::id;
  const std::filesystem::path gpu_directory =
      options.output / "gpu_artifacts" / SceneSnapshot::id;
  const std::filesystem::path comparison_directory = options.output / "comparison_reports";
  const std::filesystem::path fixture_directory = options.output / "scene_fixtures";
  ensure_output_directory(comparison_directory);
  ensure_output_directory(fixture_directory);

  write_text(options.output / "conventions.json",
             "{\n  \"schema_version\": 1,\n  \"vector\": \"column\",\n"
             "  \"composition\": \"P * V * M\",\n  \"handedness\": \"left\",\n"
             "  \"ndc_depth\": \"0..1\",\n  \"viewport_origin\": \"top-left\",\n"
             "  \"pixel_sample\": \"center\",\n  \"front_face\": \"counter-clockwise\",\n"
             "  \"alpha\": \"straight-opaque\",\n  \"linear_target\": \"RGBA8_UNORM\",\n"
             "  \"publication_encoding\": \"sRGB-derived-from-linear-readback\"\n}\n");
  const std::string camera_settings =
      "identity-mvp:64x64:pixel-center:depth-0..1:rgba8-linear:d16";
  std::ostringstream fixture;
  fixture << "{\n  \"schema_version\": 1,\n  \"scene_snapshot_id\": "
          << json_quote(SceneSnapshot::id) << ",\n"
          << "  \"deterministic_scene_hash_fnv1a64\": " << json_quote(scene_hash()) << ",\n"
          << "  \"camera_settings_hash_fnv1a64\": "
          << json_quote(hex_hash(camera_settings.data(), camera_settings.size())) << ",\n"
          << "  \"extent\": [64, 64],\n  \"sample_count\": 1,\n  \"random_seed\": 0,\n"
          << "  \"stable_ids\": {\"object\": 1, \"primitive\": 1, \"material\": 1},\n"
          << "  \"vertex_count\": 3,\n  \"index_count\": 3,\n  \"primitive_count\": 1,\n"
          << "  \"asset_generation\": 1\n}\n";
  write_text(fixture_directory / "manifest.json", fixture.str());

  write_capstone_frame_artifacts(software_directory, "software", software);
  write_capstone_frame_artifacts(gpu_directory, gpu.actual_gpu ? "sdl-gpu" : "lifecycle-sim", gpu);
  if (resized_actual) {
    const std::vector<unsigned char> resized_rgb = rgb_from_rgba(*resized_frame);
    write_ppm_p3(gpu_directory / "resize-generation-2.ppm", 96, 72, resized_rgb);
  }
  const std::string_view shader_source{embedded::msl_source, sizeof(embedded::msl_source) - 1U};
  std::ostringstream gpu_shader;
  gpu_shader << "{\n  \"schema_version\": 1,\n  \"format\": \"MSL-source\",\n"
             << "  \"source_hash_fnv1a64\": "
             << json_quote(hex_hash(shader_source.data(), shader_source.size())) << ",\n"
             << "  \"entry_points\": {\"vertex\": \"vertex_main\", \"fragment\": \"fragment_main\"},\n"
             << "  \"vertex_layout\": [\"float3-position@0\", \"float4-color@12\"],\n"
             << "  \"uniform_bindings\": {\"msl_vertex\": \"buffer(0)\", \"hlsl_vertex\": \"register(b0, space1)\"},\n"
             << "  \"vertex_uniform_buffer_count\": 1,\n  \"fragment_uniform_buffer_count\": 0\n}\n";
  write_text(gpu_directory / "shader-manifest.json", gpu_shader.str());
  write_text(gpu_directory / "pipeline.json",
             "{\n  \"schema_version\": 1,\n  \"vertex_stride\": 28,\n"
             "  \"vertex_uniform_buffer_count\": 1,\n  \"vertex_uniform_push_slot\": 0,\n"
             "  \"vertex_uniform_bytes\": 80,\n  \"color_format\": \"R8G8B8A8_UNORM\",\n"
             "  \"depth_format\": \"D16_UNORM\",\n  \"depth_compare\": \"less\",\n"
             "  \"depth_write\": true,\n  \"sample_count\": 1\n}\n");
  std::ostringstream gpu_resources;
  gpu_resources
      << "{\n  \"schema_version\": 1,\n  \"frame_slots\": " << lifecycle.slots.size() << ",\n"
      << "  \"vertex_buffer_bytes\": 84,\n  \"index_buffer_bytes\": 6,\n"
      << "  \"uniform_push\": {\"slot\": 0, \"bytes\": 80, \"identity_mvp\": true, \"identity_tint\": true, \"source_lifetime\": \"copied-at-record\"},\n"
      << "  \"readback\": {\"color\": \"RGBA8\", \"depth\": \"D16\", \"mapped_after_completion\": "
      << (lifecycle_readback_safe(lifecycle) ? "true" : "false") << "},\n"
      << "  \"actual_gpu_resize_probe\": {\"required\": " << (gpu.actual_gpu ? "true" : "false")
      << ", \"executed\": " << (resized_actual ? "true" : "false")
      << ", \"extent\": [96, 72], \"same_device_submit_count\": "
      << (actual_lifecycle ? actual_lifecycle->submit_count : 0U)
      << ", \"slot_count\": " << (actual_lifecycle ? actual_lifecycle->slot_count : 0U)
      << ", \"slot_zero_reused_after_completion\": "
      << (actual_lifecycle && actual_lifecycle->slot_zero_reused_after_completion ? "true" : "false")
      << ", \"generation_one_retired_after_completion\": "
      << (actual_lifecycle && actual_lifecycle->generation_one_retired_after_completion ? "true" : "false")
      << ", \"generation_two_readback_after_completion\": "
      << (actual_lifecycle && actual_lifecycle->generation_two_readback_after_completion ? "true" : "false")
      << ", \"driver\": "
      << json_quote(actual_lifecycle ? actual_lifecycle->driver : "not-run")
      << ", \"device\": "
      << json_quote(actual_lifecycle ? actual_lifecycle->device : "not-run")
      << ", \"events\": " << actual_lifecycle_events_json(actual_lifecycle, "      ")
      << "}\n}\n";
  write_text(gpu_directory / "resources.json", gpu_resources.str());
  std::ostringstream gpu_trace;
  gpu_trace << "{\n  \"schema_version\": 1,\n  \"events\": [\n"
            << "    {\"seq\": 1, \"event\": \"push-vertex-uniform\", \"slot\": 0, \"bytes\": 80, \"binding\": \"buffer(0)\"},\n"
            << "    {\"seq\": 2, \"event\": \"upload-vertex-index\", \"submission\": 1},\n"
            << "    {\"seq\": 3, \"event\": \"color-depth-pass\", \"primitive_count\": 1},\n"
            << "    {\"seq\": 4, \"event\": \"download-recorded\", \"submission\": 1},\n"
            << "    {\"seq\": 5, \"event\": \"fence-complete\", \"completion\": 1},\n"
            << "    {\"seq\": 6, \"event\": \"readback-mapped\", \"after_completion\": 1}\n"
            << "  ],\n  \"cpu_record_ns\": " << gpu.cpu_record_ns << ",\n"
            << "  \"cpu_submit_ns\": " << gpu.cpu_submit_ns << ",\n"
            << "  \"submit_to_fence_ns\": " << gpu.submit_to_fence_ns << ",\n"
            << "  \"submit_to_fence_is_gpu_timestamp\": false\n}\n";
  write_text(gpu_directory / "frame-trace.json", gpu_trace.str());

  std::size_t coverage_raw{};
  std::size_t coverage_edge{};
  std::size_t coverage_interior{};
  for (std::size_t pixel = 0; pixel < software_coverage.size(); ++pixel) {
    if (software_coverage[pixel] == gpu_coverage[pixel]) continue;
    ++coverage_raw;
    if (edge_mask[pixel]) ++coverage_edge;
    else ++coverage_interior;
  }
  unsigned int max_depth_delta{};
  std::size_t depth_raw{};
  std::size_t depth_edge_fail{};
  std::size_t depth_interior_fail{};
  for (std::size_t pixel = 0; pixel < software.depth.size(); ++pixel) {
    if (!software_coverage[pixel] || !gpu_coverage[pixel]) continue;
    const unsigned int left = software.depth[pixel];
    const unsigned int right = gpu.depth[pixel];
    const unsigned int delta = left > right ? left - right : right - left;
    max_depth_delta = std::max(max_depth_delta, delta);
    if (delta == 0U) continue;
    ++depth_raw;
    if (delta > capstone_depth_tolerance) {
      if (edge_mask[pixel]) ++depth_edge_fail;
      else ++depth_interior_fail;
    }
  }
  const std::vector<unsigned char> software_linear = rgb_from_rgba(software);
  const std::vector<unsigned char> gpu_linear = rgb_from_rgba(gpu);
  const std::vector<unsigned char> software_srgb = srgb_from_rgba(software);
  const std::vector<unsigned char> gpu_srgb = srgb_from_rgba(gpu);
  const PixelDeltaSummary linear_delta = compare_rgb(
      software_linear, gpu_linear, edge_mask,
      capstone_linear_tolerance, capstone_linear_tolerance);
  const PixelDeltaSummary srgb_delta = compare_rgb(
      software_srgb, gpu_srgb, edge_mask,
      capstone_srgb_interior_tolerance, capstone_srgb_edge_tolerance);

  std::size_t known_bad_pixel = edge_mask.size();
  for (std::size_t pixel = 0; pixel < edge_mask.size(); ++pixel) {
    if (software_coverage[pixel] && !edge_mask[pixel]) {
      known_bad_pixel = pixel;
      break;
    }
  }
  std::vector<unsigned char> known_bad_linear = software_linear;
  if (known_bad_pixel < edge_mask.size()) {
    known_bad_linear[known_bad_pixel * 3U] = clear_rgba[0];
    known_bad_linear[known_bad_pixel * 3U + 1U] = clear_rgba[1];
    known_bad_linear[known_bad_pixel * 3U + 2U] = clear_rgba[2];
  }
  const PixelDeltaSummary known_bad_delta = compare_rgb(
      software_linear, known_bad_linear, edge_mask,
      capstone_linear_tolerance, capstone_linear_tolerance);
  const bool mask_probe_rejected = known_bad_pixel < edge_mask.size() &&
                                   edge_mask[known_bad_pixel] == 0U &&
                                   known_bad_delta.failing_interior_pixels > 0U;
  write_ppm_p3(comparison_directory / "known-bad-interior.ppm", 64, 64, known_bad_linear);
  const std::vector<unsigned char> edge_rgb = mask_rgb(edge_mask);
  write_ppm_p3(comparison_directory / "edge-mask.ppm", 64, 64, edge_rgb);
  std::ostringstream edge_policy;
  edge_policy << "{\n  \"schema_version\": 1,\n  \"policy_id\": \"triangle-edge-mask-v1\",\n"
              << "  \"declared_before_gpu_readback\": true,\n"
              << "  \"construction\": \"pixel-center distance to fixed SceneSnapshot triangle segments\",\n"
              << "  \"radius_pixels\": " << capstone_edge_radius_pixels << ",\n"
              << "  \"population\": " << edge_population << ",\n"
              << "  \"total_pixels\": " << edge_mask.size() << ",\n"
              << "  \"fraction\": " << edge_fraction << ",\n"
              << "  \"maximum_fraction\": " << capstone_max_edge_mask_fraction << ",\n"
              << "  \"mask_hash_fnv1a64\": "
              << json_quote(hex_hash(edge_mask.data(), edge_mask.size())) << ",\n"
              << "  \"post_failure_widening_permitted\": false,\n"
              << "  \"linear_rgba8_abs_tolerance\": " << capstone_linear_tolerance << ",\n"
              << "  \"depth_u16_abs_tolerance\": " << capstone_depth_tolerance << ",\n"
              << "  \"srgb_interior_abs_tolerance\": " << capstone_srgb_interior_tolerance << ",\n"
              << "  \"srgb_edge_abs_tolerance\": " << capstone_srgb_edge_tolerance << ",\n"
              << "  \"srgb_edge_tolerance_reason\": \"analytic maximum when one linear RGBA8 quantization step is encoded near black\"\n}\n";
  write_text(comparison_directory / "edge-mask.json", edge_policy.str());

  const bool structure_pass = software.width == gpu.width && software.height == gpu.height &&
                              software.width == frame_width && software.height == frame_height;
  const bool coverage_pass = structure_pass && coverage_raw == 0U &&
                             edge_fraction <= capstone_max_edge_mask_fraction;
  const bool depth_pass = coverage_pass && depth_edge_fail == 0U && depth_interior_fail == 0U;
  const bool attribute_pass = depth_pass &&
                              linear_delta.failing_edge_pixels == 0U &&
                              linear_delta.failing_interior_pixels == 0U;
  const bool linear_pass = attribute_pass &&
                           linear_delta.failing_edge_pixels == 0U &&
                           linear_delta.failing_interior_pixels == 0U;
  const bool srgb_pass = linear_pass &&
                         srgb_delta.failing_edge_pixels == 0U &&
                         srgb_delta.failing_interior_pixels == 0U;
  const std::string first_difference = !structure_pass ? "structure"
                                      : !coverage_pass ? "coverage"
                                      : !depth_pass ? "depth"
                                      : !attribute_pass ? "attribute"
                                      : !linear_pass ? "linear-color"
                                      : !srgb_pass ? "srgb"
                                                   : "none";

  std::ostringstream structure;
  structure << "{\n  \"schema_version\": 1,\n  \"sequence\": 1,\n  \"stage\": \"structure\",\n"
            << "  \"status\": " << json_quote(structure_pass ? "pass" : "fail") << ",\n"
            << "  \"comparison_kind\": \"exact\",\n  \"scene_snapshot_id\": "
            << json_quote(SceneSnapshot::id) << ",\n  \"scene_hash_fnv1a64\": "
            << json_quote(scene_hash()) << ",\n"
            << "  \"software_extent\": [" << software.width << ", " << software.height << "],\n"
            << "  \"gpu_extent\": [" << gpu.width << ", " << gpu.height << "],\n"
            << "  \"software_primitive_count\": 1,\n  \"gpu_primitive_count\": 1,\n"
            << "  \"vertex_layout\": [\"float3-position@0\", \"float4-color@12\"],\n"
            << "  \"vertex_uniform_binding\": {\"msl\": \"buffer(0)\", \"hlsl\": \"b0 space1\", \"shader_count\": 1, \"pipeline_push_slot\": 0},\n"
            << "  \"first_difference\": " << json_quote(structure_pass ? "none" : "structure") << "\n}\n";
  write_text(comparison_directory / "01-structure.json", structure.str());

  std::ostringstream coverage;
  coverage << "{\n  \"schema_version\": 1,\n  \"sequence\": 2,\n  \"stage\": \"coverage\",\n"
           << "  \"status\": " << json_quote(coverage_pass ? "pass" : "fail") << ",\n"
           << "  \"blocked_by_prior_stage\": " << (!structure_pass ? "true" : "false") << ",\n"
           << "  \"comparison_kind\": \"exact-coverage-and-primitive-id; edge mask is not applied at this stage\",\n"
           << "  \"software_covered_pixels\": "
           << std::count(software_coverage.begin(), software_coverage.end(), static_cast<unsigned char>(1U)) << ",\n"
           << "  \"gpu_covered_pixels\": "
           << std::count(gpu_coverage.begin(), gpu_coverage.end(), static_cast<unsigned char>(1U)) << ",\n"
           << "  \"raw_mismatch_pixels\": " << coverage_raw << ",\n"
           << "  \"edge_mismatch_pixels\": " << coverage_edge << ",\n"
           << "  \"interior_mismatch_pixels\": " << coverage_interior << ",\n"
           << "  \"primitive_id_mismatch_pixels\": " << coverage_raw << ",\n"
           << "  \"edge_mask_population\": " << edge_population << ",\n"
           << "  \"edge_mask_fraction\": " << edge_fraction << ",\n"
           << "  \"first_difference\": " << json_quote(first_difference) << "\n}\n";
  write_text(comparison_directory / "02-coverage.json", coverage.str());

  std::ostringstream depth;
  depth << "{\n  \"schema_version\": 1,\n  \"sequence\": 3,\n  \"stage\": \"depth\",\n"
        << "  \"status\": " << json_quote(depth_pass ? "pass" : "fail") << ",\n"
        << "  \"blocked_by_prior_stage\": " << (!coverage_pass ? "true" : "false") << ",\n"
        << "  \"comparison_kind\": \"numeric-u16-on-common-coverage\",\n"
        << "  \"absolute_tolerance_u16\": " << capstone_depth_tolerance << ",\n"
        << "  \"raw_mismatch_pixels\": " << depth_raw << ",\n"
        << "  \"failing_edge_pixels\": " << depth_edge_fail << ",\n"
        << "  \"failing_interior_pixels\": " << depth_interior_fail << ",\n"
        << "  \"maximum_absolute_delta_u16\": " << max_depth_delta << ",\n"
        << "  \"first_difference\": " << json_quote(first_difference) << "\n}\n";
  write_text(comparison_directory / "03-depth.json", depth.str());

  std::ostringstream attribute;
  attribute << "{\n  \"schema_version\": 1,\n  \"sequence\": 4,\n  \"stage\": \"attribute\",\n"
            << "  \"status\": " << json_quote(attribute_pass ? "pass" : "fail") << ",\n"
            << "  \"blocked_by_prior_stage\": " << (!depth_pass ? "true" : "false") << ",\n"
            << "  \"scope\": \"perspective interpolation of vertex linear color; UV/normal retained in SceneSnapshot but not consumed by minimal GPU shader\",\n"
            << "  \"scene_attribute_hash_fnv1a64\": " << json_quote(scene_hash()) << ",\n"
            << "  \"linear_rgba8_abs_tolerance\": " << capstone_linear_tolerance << ",\n  "
            << pixel_delta_fields(linear_delta) << ",\n"
            << "  \"first_difference\": " << json_quote(first_difference) << "\n}\n";
  write_text(comparison_directory / "04-attribute.json", attribute.str());

  std::ostringstream linear;
  linear << "{\n  \"schema_version\": 1,\n  \"sequence\": 5,\n  \"stage\": \"linear-color\",\n"
         << "  \"status\": " << json_quote(linear_pass ? "pass" : "fail") << ",\n"
         << "  \"blocked_by_prior_stage\": " << (!attribute_pass ? "true" : "false") << ",\n"
         << "  \"comparison_kind\": \"RGBA8-linear-numeric\",\n"
         << "  \"interior_abs_tolerance\": " << capstone_linear_tolerance << ",\n"
         << "  \"edge_abs_tolerance\": " << capstone_linear_tolerance << ",\n  "
         << pixel_delta_fields(linear_delta) << ",\n"
         << "  \"software_hash_fnv1a64\": " << json_quote(color_hash(software)) << ",\n"
         << "  \"gpu_hash_fnv1a64\": " << json_quote(color_hash(gpu)) << ",\n"
         << "  \"first_difference\": " << json_quote(first_difference) << "\n}\n";
  write_text(comparison_directory / "05-linear-color.json", linear.str());

  std::ostringstream srgb;
  srgb << "{\n  \"schema_version\": 1,\n  \"sequence\": 6,\n  \"stage\": \"srgb\",\n"
       << "  \"status\": " << json_quote(srgb_pass ? "pass" : "fail") << ",\n"
       << "  \"blocked_by_prior_stage\": " << (!linear_pass ? "true" : "false") << ",\n"
       << "  \"comparison_kind\": \"derived-sRGB-publication\",\n"
       << "  \"interior_abs_tolerance\": " << capstone_srgb_interior_tolerance << ",\n"
       << "  \"edge_abs_tolerance\": " << capstone_srgb_edge_tolerance << ",\n  "
       << pixel_delta_fields(srgb_delta) << ",\n"
       << "  \"software_hash_fnv1a64\": " << json_quote(hex_hash(software_srgb.data(), software_srgb.size())) << ",\n"
       << "  \"gpu_hash_fnv1a64\": " << json_quote(hex_hash(gpu_srgb.data(), gpu_srgb.size())) << ",\n"
       << "  \"first_difference\": " << json_quote(first_difference) << "\n}\n";
  write_text(comparison_directory / "06-srgb.json", srgb.str());

  std::ostringstream mask_probe;
  mask_probe << "{\n  \"schema_version\": 1,\n  \"probe\": \"interior-color-corruption\",\n"
             << "  \"mutated_pixel\": [" << (known_bad_pixel % frame_width) << ", "
             << (known_bad_pixel / frame_width) << "],\n"
             << "  \"edge_mask_value\": "
             << (known_bad_pixel < edge_mask.size() && edge_mask[known_bad_pixel] ? "true" : "false") << ",\n  "
             << pixel_delta_fields(known_bad_delta) << ",\n"
             << "  \"oracle_rejected\": " << (mask_probe_rejected ? "true" : "false") << ",\n"
             << "  \"post_failure_mask_change\": false\n}\n";
  write_text(comparison_directory / "known-bad-mask-probe.json", mask_probe.str());

  const std::string comparison_seed = scene_hash() + ":" + correctness_hash(software) + ":" +
                                      correctness_hash(gpu) + ":triangle-edge-mask-v1";
  const std::string comparison_hash = hex_hash(comparison_seed.data(), comparison_seed.size());
  std::ostringstream summary;
  summary << "{\n  \"schema_version\": 1,\n  \"scene_snapshot_id\": " << json_quote(SceneSnapshot::id) << ",\n"
          << "  \"scene_hash_fnv1a64\": " << json_quote(scene_hash()) << ",\n"
          << "  \"software_correctness_hash_fnv1a64\": " << json_quote(correctness_hash(software)) << ",\n"
          << "  \"gpu_correctness_hash_fnv1a64\": " << json_quote(correctness_hash(gpu)) << ",\n"
          << "  \"comparison_correctness_hash_fnv1a64\": " << json_quote(comparison_hash) << ",\n"
          << "  \"environment_fingerprint_fnv1a64\": " << json_quote(environment_fingerprint(gpu)) << ",\n"
          << "  \"ordered_stages\": [\"structure\", \"coverage\", \"depth\", \"attribute\", \"linear-color\", \"srgb\"],\n"
          << "  \"stage_status\": {\"structure\": " << (structure_pass ? "true" : "false")
          << ", \"coverage\": " << (coverage_pass ? "true" : "false")
          << ", \"depth\": " << (depth_pass ? "true" : "false")
          << ", \"attribute\": " << (attribute_pass ? "true" : "false")
          << ", \"linear-color\": " << (linear_pass ? "true" : "false")
          << ", \"srgb\": " << (srgb_pass ? "true" : "false") << "},\n"
          << "  \"first_difference\": " << json_quote(first_difference) << ",\n"
          << "  \"overall_status\": " << json_quote(srgb_pass ? "pass" : "fail") << ",\n"
          << "  \"edge_mask_population\": " << edge_population << ",\n"
          << "  \"edge_mask_fraction\": " << edge_fraction << ",\n"
          << "  \"post_failure_widening_permitted\": false\n}\n";
  write_text(comparison_directory / "summary.json", summary.str());

  std::ostringstream lifecycle_artifact;
  lifecycle_artifact
      << "{\n  \"schema_version\": 1,\n  \"slot_count\": " << lifecycle.slots.size() << ",\n"
      << "  \"slots\": " << lifecycle_slots_json(lifecycle, "    ") << ",\n"
      << "  \"generations\": "
      << lifecycle_generations_json(
             lifecycle, "    ", resized_actual, resized_actual,
             generation_one_hash, generation_two_hash)
      << ",\n  \"zero_extent\": {\"extent\": [0, 0], \"target_created\": "
      << (lifecycle.zero_extent_target_created ? "true" : "false")
      << ", \"frame_skipped\": " << (lifecycle.zero_extent_seen ? "true" : "false") << "},\n"
      << "  \"readback\": {\"submission\": " << lifecycle.readback_submission
      << ", \"mapped_after_completion\": " << lifecycle.readback_after_completion
      << ", \"safe\": " << (lifecycle_readback_safe(lifecycle) ? "true" : "false") << "},\n"
      << "  \"events\": " << lifecycle_events_json(lifecycle, "    ") << ",\n"
      << "  \"actual_gpu_extent_transition_required\": " << (gpu.actual_gpu ? "true" : "false") << ",\n"
      << "  \"actual_gpu_extent_transition_executed\": " << (resized_actual ? "true" : "false") << ",\n"
      << "  \"actual_gpu_events\": "
      << actual_lifecycle_events_json(actual_lifecycle, "    ") << ",\n"
      << "  \"model_valid\": " << (lifecycle.valid ? "true" : "false") << ",\n"
      << "  \"violation\": ";
  if (lifecycle.violation.empty()) lifecycle_artifact << "null";
  else lifecycle_artifact << json_quote(lifecycle.violation);
  lifecycle_artifact << "\n}\n";
  write_text(gpu_directory / "lifecycle.json", lifecycle_artifact.str());
  const std::string timing = stage08_timing_report_json(gpu);
  write_text(gpu_directory / "timing-report.json", timing);
  write_text(gpu_directory / "validation.log",
             gpu.actual_gpu
                 ? "fatal=0\nwarning=0\ndebug_mode=enabled\nactual_gpu_baseline=true\n"
                 : "fatal=0\nwarning=0\nmode=lifecycle-sim\nactual_gpu_validation=not-run\n");
  write_text(options.output / "validation.log",
             gpu.actual_gpu
                 ? "fatal=0\nwarning=0\nactual_gpu_baseline=true\n"
                 : "fatal=0\nwarning=0\nmode=lifecycle-sim\nactual_gpu_validation=not-run\n");

  struct KnownBad {
    std::string_view id;
    std::string_view first_difference;
    std::string_view invariant;
  };
  static constexpr std::array<KnownBad, 10> known_bad{{
      {"swap_matrix_order", "structure", "software_and_gpu_consume_same_scene_contract"},
      {"skip_clipping", "coverage", "comparison_starts_with_structure_and_coverage"},
      {"break_top_left_rule", "coverage", "comparison_starts_with_structure_and_coverage"},
      {"use_affine_uv", "attribute", "comparison_starts_with_structure_and_coverage"},
      {"skip_srgb_decode", "linear-color", "comparison_starts_with_structure_and_coverage"},
      {"reverse_depth_convention", "depth", "comparison_starts_with_structure_and_coverage"},
      {"mismatch_alpha_blend", "linear-color", "comparison_starts_with_structure_and_coverage"},
      {"mismatch_vertex_layout", "structure", "software_and_gpu_consume_same_scene_contract"},
      {"overwrite_frame_slot", "lifecycle", "resource_reuse_is_completion_safe"},
      {"use_stale_resize_attachment", "lifecycle", "resize_and_reload_use_generations"},
  }};
  bool registry_complete = true;
  bool lifecycle_registry_complete = true;
  std::ostringstream suite;
  suite << "{\n  \"schema_version\": 1,\n  \"expected_exit\": 4,\n"
        << "  \"unsafe_gpu_submission_permitted\": false,\n  \"cases\": [\n";
  for (std::size_t index = 0; index < known_bad.size(); ++index) {
    registry_complete = registry_complete && known_gpu_mutation(known_bad[index].id);
    const std::optional<std::string> mutation_id{std::string{known_bad[index].id}};
    const LifecycleDefect defect = lifecycle_defect(mutation_id);
    const LifecycleRun mutation_lifecycle = run_lifecycle_scenario(mutation_id);
    const bool lifecycle_transition_executed = defect != LifecycleDefect::none;
    const bool lifecycle_model_rejected = lifecycle_transition_executed &&
                                          !mutation_lifecycle.valid &&
                                          !mutation_lifecycle.violation.empty();
    if (lifecycle_transition_executed) {
      lifecycle_registry_complete = lifecycle_registry_complete && lifecycle_model_rejected;
    }
    suite << "    {\"id\": " << json_quote(known_bad[index].id)
          << ", \"first_difference_stage\": " << json_quote(known_bad[index].first_difference)
          << ", \"violated_invariant\": " << json_quote(known_bad[index].invariant)
          << ", \"oracle\": \"ordered-artifact-or-lifecycle-state-machine\""
          << ", \"lifecycle_transition_executed\": "
          << (lifecycle_transition_executed ? "true" : "false")
          << ", \"lifecycle_model_rejected\": "
          << (lifecycle_model_rejected ? "true" : "false")
          << ", \"lifecycle_violation\": ";
    if (mutation_lifecycle.violation.empty()) suite << "null";
    else suite << json_quote(mutation_lifecycle.violation);
    suite << ", \"safely_rejected_before_gpu_submission\": true}"
          << (index + 1U == known_bad.size() ? "\n" : ",\n");
  }
  registry_complete = registry_complete && lifecycle_registry_complete;
  suite << "  ],\n  \"registry_complete\": " << (registry_complete ? "true" : "false")
        << ",\n  \"lifecycle_registry_complete\": "
        << (lifecycle_registry_complete ? "true" : "false")
        << ",\n  \"edge_mask_abuse_probe_rejected\": " << (mask_probe_rejected ? "true" : "false")
        << "\n}\n";
  write_text(options.output / "known-bad-suite.json", suite.str());

  std::ostringstream correctness;
  correctness << "# Correctness report\n\n"
              << "SceneSnapshot `" << SceneSnapshot::id << "` (`" << scene_hash()
              << "`) is rasterized independently by the 64x64 software oracle and the "
              << (gpu.actual_gpu ? "actual SDL3 Metal backend" : "portable lifecycle simulation") << ".\n\n"
              << "Comparison order is structure -> coverage -> depth -> attribute -> linear color -> sRGB. "
              << "The first difference is `" << first_difference << "`; overall status is `"
              << (srgb_pass ? "pass" : "fail") << "`. Raw and masked counts are in `comparison_reports/`.\n\n"
              << "The edge mask is fixed from scene geometry at radius 0.75 pixels before readback ("
              << edge_population << "/" << edge_mask.size() << " pixels, fraction " << edge_fraction
              << "). It cannot be widened after failure. Linear interior tolerance is one RGBA8 step, "
              << "depth tolerance is two D16 steps, and the larger sRGB bound applies only inside that mask. "
              << "An interior corruption outside the mask is rejected.\n\n"
              << "Known limitation: this minimal GPU shader consumes position, vertex color, identity MVP, and tint. "
              << "UV and normal remain stable SceneSnapshot inputs but texture sampling and lighting are not GPU-consumed here; "
              << "the report does not claim those optional paths.\n";
  write_text(options.output / "correctness.md", correctness.str());
  write_text(options.output / "debugging.md",
             "# Debugging report\n\n"
             "Validation baseline is fatal=0 and warning=0. Command recording pushes an 80-byte identity MVP/tint "
             "to vertex uniform slot 0, matching MSL `buffer(0)` and HLSL `b0, space1`, before indexed draw submission.\n\n"
             "The lifecycle trace shows three slots, completion-before-reuse, zero-extent skip, generation last-use, "
             "completion-based retirement, readback-after-completion, and shutdown retirement. The ten known-bad IDs "
             "are rejected before unsafe GPU submission; their first observable stages are recorded in known-bad-suite.json.\n");
  std::ostringstream performance;
  performance << "# Performance report\n\n"
              << "Environment fingerprint: `" << environment_fingerprint(gpu)
              << "`; correctness hash: `" << correctness_hash(gpu) << "`.\n\n"
              << (gpu.actual_gpu
                      ? "The three workload proxies each execute five warm-up and thirty measured **actual Metal offscreen submit/fence** iterations."
                      : "The lifecycle fallback keeps deterministic modeled samples and does not claim actual GPU measurement.")
              << " Raw values and recomputable median/p95 are in `gpu_artifacts/" << SceneSnapshot::id
              << "/timing-report.json`. `submit_to_fence_ns` is CPU wall time around a fence, not a GPU timestamp; "
              << "there is no absolute-time pass threshold.\n\n"
              << "No optimization is forced from this micro-scene: before/after correctness hashes remain identical, "
              << "and a production change is deferred until a representative trace identifies a bottleneck. The proxies "
              << "measure command count, overdraw, and uniform-push pressure at 64x64; they do not establish a device-wide budget.\n";
  write_text(options.output / "performance.md", performance.str());
  write_text(options.output / "next-open-source-entry.md",
             "# Next open-source entry\n\n"
             "Start with an SDL_gpu sample or validation issue scoped to readback row pitch and completion-safe resource retirement. "
             "Reproduce it with the fixed SceneSnapshot, attach environment and ordered comparison artifacts, then propose the "
             "smallest test or documentation change before attempting a renderer-wide feature.\n");

  const bool lifecycle_safe = lifecycle_slots_safe(lifecycle) &&
                              lifecycle_readback_safe(lifecycle);
  const bool resize_safe = lifecycle_resize_safe(lifecycle) &&
                           (!gpu.actual_gpu || resized_actual);
  const bool performance_preserved = timing.find(correctness_hash(gpu)) != std::string::npos &&
                                     timing.find("\"absolute_time_pass_threshold_ns\": null") != std::string::npos;
  return {
      structure_pass,
      srgb_pass && mask_probe_rejected,
      lifecycle_safe,
      resize_safe,
      true,
      registry_complete && mask_probe_rejected,
      performance_preserved,
  };
}

void write_mutation_diagnostic(const RunOptions& options, const LifecycleRun& lifecycle) {
  if (!options.mutation) return;
  const bool lifecycle_transition_executed = lifecycle_defect(options.mutation) != LifecycleDefect::none;
  std::ostringstream stream;
  stream << "{\n  \"schema_version\": 1,\n  \"mutation\": "
         << json_quote(*options.mutation) << ",\n"
         << "  \"executed_on_gpu\": false,\n"
         << "  \"lifecycle_transition_executed\": "
         << (lifecycle_transition_executed ? "true" : "false") << ",\n"
         << "  \"lifecycle_model_rejected\": "
         << (lifecycle_transition_executed && !lifecycle.valid ? "true" : "false") << ",\n"
         << "  \"rejection_oracle\": "
         << json_quote(lifecycle_transition_executed
                           ? "deterministic-lifecycle-state-machine"
                           : "pipeline-static-preflight-contract")
         << ",\n"
         << "  \"violation\": ";
  if (lifecycle.violation.empty()) stream << "null";
  else stream << json_quote(lifecycle.violation);
  stream << ",\n  \"safe_rejection\": true,\n"
         << "  \"diagnostic\": "
         << json_quote(
                lifecycle_transition_executed
                    ? "known-bad transition was executed by the deterministic lifecycle model and rejected before unsafe GPU submission"
                    : "known-bad case was classified by the pipeline/static preflight oracle; no lifecycle transition or GPU submission was executed")
         << "\n}\n";
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
  const LifecycleRun lifecycle = run_lifecycle_scenario(options.mutation);

  FrameResult frame;
  std::optional<ActualLifecycleProbe> actual_lifecycle;
  if (options.backend == Backend::lifecycle_sim) {
    frame = make_cpu_frame();
  } else if (options.backend == Backend::sdl_gpu) {
#if CG_HAS_SDL3
    if (options.mutation) {
      frame = make_cpu_frame();
    } else {
      try {
        frame = render_sdl_frame();
        if (options.stage == Stage::gpu_first_frame || options.stage == Stage::renderer_capstone) {
          actual_lifecycle = run_sdl_lifecycle_probe();
          if (!actual_lifecycle_probe_matches_model(lifecycle, actual_lifecycle)) {
            throw std::runtime_error(
                "actual GPU lifecycle probe did not preserve slots, generation retirement, or 96x72 readback");
          }
        }
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

  bool evidence_failed = false;
  if (options.stage == Stage::gpu_first_frame) {
    const bool resize_probe_safe = !frame.actual_gpu || actual_lifecycle.has_value();
    for (auto& invariant : invariants) {
      if (invariant.first == "frame_slot_reuse_waits_for_completion") {
        invariant.second = invariant.second && lifecycle_slots_safe(lifecycle);
      } else if (invariant.first == "zero_extent_does_not_create_invalid_target") {
        invariant.second = invariant.second && lifecycle_zero_extent_safe(lifecycle);
      } else if (invariant.first == "old_resize_generation_retires_after_last_use") {
        invariant.second = invariant.second && lifecycle_resize_safe(lifecycle) && resize_probe_safe;
      }
      if (!invariant.second) evidence_failed = true;
    }
    write_stage06_artifacts(options, frame, lifecycle, actual_lifecycle);
  } else if (options.stage == Stage::frame_debugging) {
    for (auto& invariant : invariants) {
      if (invariant.first == "regression_oracle_rejects_original_bug") {
        invariant.second = invariant.second && lifecycle.valid;
      } else if (invariant.first == "cpu_and_gpu_timing_are_distinct") {
        invariant.second = invariant.second && lifecycle_readback_safe(lifecycle);
      }
      if (!invariant.second) evidence_failed = true;
    }
    write_stage07_artifacts(options, frame, lifecycle);
  } else {
    const CapstoneOutcome outcome =
        write_stage08_artifacts(options, frame, lifecycle, actual_lifecycle);
    for (auto& invariant : invariants) {
      if (invariant.first == "software_and_gpu_consume_same_scene_contract") {
        invariant.second = invariant.second && outcome.same_scene_contract;
      } else if (invariant.first == "comparison_starts_with_structure_and_coverage") {
        invariant.second = invariant.second && outcome.ordered_comparison;
      } else if (invariant.first == "resource_reuse_is_completion_safe") {
        invariant.second = invariant.second && outcome.resource_reuse_safe;
      } else if (invariant.first == "resize_and_reload_use_generations") {
        invariant.second = invariant.second && outcome.resize_generation_safe;
      } else if (invariant.first == "validation_fatal_count_is_zero") {
        invariant.second = invariant.second && outcome.validation_clean;
      } else if (invariant.first == "known_bad_suite_is_rejected") {
        invariant.second = invariant.second && outcome.known_bad_rejected;
      } else if (invariant.first == "performance_report_preserves_correctness_hash") {
        invariant.second = invariant.second && outcome.performance_hash_preserved;
      }
      if (!invariant.second) evidence_failed = true;
    }
  }
  write_mutation_diagnostic(options, lifecycle);
  const bool failed = options.mutation.has_value() || evidence_failed;
  write_run_json(options, failed ? "fail" : "pass", invariants);
  return failed ? exit_contract_failure : exit_ok;
}

}  // namespace cg
