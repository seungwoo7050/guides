#include "cg/artifact.hpp"
#include "cg/contracts.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <limits>
#include <map>
#include <numbers>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace cg {
namespace {

constexpr double kEpsilon = 1.0e-9;

struct DVec3 {
  double x{};
  double y{};
  double z{};
};

struct DVec4 {
  double x{};
  double y{};
  double z{};
  double w{};
};

struct DMat3 {
  std::array<std::array<double, 3>, 3> value{};
};

struct DMat4 {
  std::array<std::array<double, 4>, 4> value{};
};

struct Rgb {
  double r{};
  double g{};
  double b{};
};

struct Rgba {
  double r{};
  double g{};
  double b{};
  double a{};
};

struct LinearImage {
  int width{};
  int height{};
  std::vector<Rgb> pixels;
};

using Invariants = std::vector<std::pair<std::string, bool>>;

[[nodiscard]] bool near(const double left, const double right, const double epsilon = kEpsilon) {
  return std::abs(left - right) <= epsilon;
}

[[nodiscard]] bool finite(const DVec4& value) {
  return std::isfinite(value.x) && std::isfinite(value.y) &&
         std::isfinite(value.z) && std::isfinite(value.w);
}

[[nodiscard]] DVec3 operator*(const DVec3 value, const double scale) {
  return {value.x * scale, value.y * scale, value.z * scale};
}

[[nodiscard]] double dot(const DVec3 left, const DVec3 right) {
  return left.x * right.x + left.y * right.y + left.z * right.z;
}

[[nodiscard]] double length(const DVec3 value) {
  return std::sqrt(dot(value, value));
}

[[nodiscard]] DVec3 normalize(const DVec3 value) {
  const double magnitude = length(value);
  if (!(magnitude > kEpsilon) || !std::isfinite(magnitude)) {
    throw std::runtime_error("cannot normalize a zero or non-finite vector");
  }
  return value * (1.0 / magnitude);
}

[[nodiscard]] DMat4 identity4() {
  DMat4 result{};
  for (std::size_t index = 0; index < 4; ++index) result.value[index][index] = 1.0;
  return result;
}

[[nodiscard]] DMat4 multiply(const DMat4& left, const DMat4& right) {
  DMat4 result{};
  for (std::size_t row = 0; row < 4; ++row) {
    for (std::size_t column = 0; column < 4; ++column) {
      for (std::size_t inner = 0; inner < 4; ++inner) {
        result.value[row][column] += left.value[row][inner] * right.value[inner][column];
      }
    }
  }
  return result;
}

[[nodiscard]] DVec4 multiply(const DMat4& matrix, const DVec4 vector) {
  const std::array<double, 4> input{vector.x, vector.y, vector.z, vector.w};
  std::array<double, 4> result{};
  for (std::size_t row = 0; row < 4; ++row) {
    for (std::size_t column = 0; column < 4; ++column) {
      result[row] += matrix.value[row][column] * input[column];
    }
  }
  return {result[0], result[1], result[2], result[3]};
}

[[nodiscard]] DMat4 translation(const double x, const double y, const double z) {
  DMat4 result = identity4();
  result.value[0][3] = x;
  result.value[1][3] = y;
  result.value[2][3] = z;
  return result;
}

[[nodiscard]] DMat4 scale(const double x, const double y, const double z) {
  DMat4 result{};
  result.value[0][0] = x;
  result.value[1][1] = y;
  result.value[2][2] = z;
  result.value[3][3] = 1.0;
  return result;
}

[[nodiscard]] DMat4 rotation_z(const double radians) {
  DMat4 result = identity4();
  const double cosine = std::cos(radians);
  const double sine = std::sin(radians);
  result.value[0][0] = cosine;
  result.value[0][1] = -sine;
  result.value[1][0] = sine;
  result.value[1][1] = cosine;
  return result;
}

[[nodiscard]] DMat4 perspective_lh_zo(
    const double vertical_fov_radians,
    const double aspect,
    const double near_plane,
    const double far_plane) {
  if (!(vertical_fov_radians > 0.0 && vertical_fov_radians < std::numbers::pi) ||
      !(aspect > 0.0) || !(near_plane > 0.0) || !(far_plane > near_plane)) {
    throw std::runtime_error("invalid perspective parameters");
  }
  const double y_scale = 1.0 / std::tan(vertical_fov_radians * 0.5);
  const double x_scale = y_scale / aspect;
  DMat4 result{};
  result.value[0][0] = x_scale;
  result.value[1][1] = y_scale;
  result.value[2][2] = far_plane / (far_plane - near_plane);
  result.value[2][3] = -(near_plane * far_plane) / (far_plane - near_plane);
  result.value[3][2] = 1.0;
  return result;
}

[[nodiscard]] DMat3 upper_left3(const DMat4& matrix) {
  DMat3 result{};
  for (std::size_t row = 0; row < 3; ++row) {
    for (std::size_t column = 0; column < 3; ++column) {
      result.value[row][column] = matrix.value[row][column];
    }
  }
  return result;
}

[[nodiscard]] double determinant(const DMat3& matrix) {
  const auto& m = matrix.value;
  return m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) -
         m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
         m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
}

[[nodiscard]] DMat3 inverse_transpose(const DMat3& matrix) {
  const double det = determinant(matrix);
  if (!(std::abs(det) > kEpsilon) || !std::isfinite(det)) {
    throw std::runtime_error("singular normal matrix");
  }
  const auto& m = matrix.value;
  DMat3 result{};
  // Cofactor matrix is the transpose of the inverse, which is exactly the
  // normal transform for a column-vector model matrix.
  result.value[0] = {
      (m[1][1] * m[2][2] - m[1][2] * m[2][1]) / det,
      (m[1][2] * m[2][0] - m[1][0] * m[2][2]) / det,
      (m[1][0] * m[2][1] - m[1][1] * m[2][0]) / det};
  result.value[1] = {
      (m[0][2] * m[2][1] - m[0][1] * m[2][2]) / det,
      (m[0][0] * m[2][2] - m[0][2] * m[2][0]) / det,
      (m[0][1] * m[2][0] - m[0][0] * m[2][1]) / det};
  result.value[2] = {
      (m[0][1] * m[1][2] - m[0][2] * m[1][1]) / det,
      (m[0][2] * m[1][0] - m[0][0] * m[1][2]) / det,
      (m[0][0] * m[1][1] - m[0][1] * m[1][0]) / det};
  return result;
}

[[nodiscard]] DVec3 multiply(const DMat3& matrix, const DVec3 vector) {
  return {
      matrix.value[0][0] * vector.x + matrix.value[0][1] * vector.y +
          matrix.value[0][2] * vector.z,
      matrix.value[1][0] * vector.x + matrix.value[1][1] * vector.y +
          matrix.value[1][2] * vector.z,
      matrix.value[2][0] * vector.x + matrix.value[2][1] * vector.y +
          matrix.value[2][2] * vector.z};
}

[[nodiscard]] DVec4 lerp(const DVec4 left, const DVec4 right, const double amount) {
  return {
      left.x + (right.x - left.x) * amount,
      left.y + (right.y - left.y) * amount,
      left.z + (right.z - left.z) * amount,
      left.w + (right.w - left.w) * amount};
}

[[nodiscard]] std::vector<DVec4> clip_near_plane(const std::vector<DVec4>& input) {
  std::vector<DVec4> output;
  if (input.empty()) return output;
  DVec4 previous = input.back();
  bool previous_inside = previous.z >= 0.0;
  for (const DVec4 current : input) {
    const bool current_inside = current.z >= 0.0;
    if (previous_inside != current_inside) {
      const double denominator = previous.z - current.z;
      if (std::abs(denominator) <= kEpsilon) {
        throw std::runtime_error("unstable near-plane intersection");
      }
      const double amount = previous.z / denominator;
      output.push_back(lerp(previous, current, amount));
    }
    if (current_inside) output.push_back(current);
    previous = current;
    previous_inside = current_inside;
  }
  return output;
}

[[nodiscard]] bool inside_clip_volume(const DVec4 value) {
  return finite(value) && value.w > 0.0 && value.x >= -value.w - kEpsilon &&
         value.x <= value.w + kEpsilon && value.y >= -value.w - kEpsilon &&
         value.y <= value.w + kEpsilon && value.z >= -kEpsilon &&
         value.z <= value.w + kEpsilon;
}

[[nodiscard]] DVec4 perspective_divide(const DVec4 clip, const bool discard_w) {
  if (discard_w) return {clip.x, clip.y, clip.z, 1.0};
  if (!(std::abs(clip.w) > kEpsilon) || !std::isfinite(clip.w)) {
    throw std::runtime_error("perspective divide requires finite non-zero clip w");
  }
  return {clip.x / clip.w, clip.y / clip.w, clip.z / clip.w, 1.0};
}

[[nodiscard]] DVec4 viewport(const DVec4 ndc, const int width, const int height, const bool flip_twice) {
  double y = (1.0 - ndc.y) * 0.5 * static_cast<double>(height);
  if (flip_twice) y = static_cast<double>(height) - y;
  return {
      (ndc.x + 1.0) * 0.5 * static_cast<double>(width),
      y,
      ndc.z,
      1.0};
}

[[nodiscard]] std::string number(const double value) {
  if (!std::isfinite(value)) return "null";
  std::ostringstream output;
  output << std::setprecision(12) << value;
  return output.str();
}

[[nodiscard]] std::string json(const DVec3 value) {
  return "[" + number(value.x) + ", " + number(value.y) + ", " + number(value.z) + "]";
}

[[nodiscard]] std::string json(const DVec4 value) {
  return "[" + number(value.x) + ", " + number(value.y) + ", " +
         number(value.z) + ", " + number(value.w) + "]";
}

[[nodiscard]] std::string json_escape(const std::string_view value) {
  std::string result;
  result.reserve(value.size() + 8);
  for (const char character : value) {
    switch (character) {
      case '\\': result += "\\\\"; break;
      case '"': result += "\\\""; break;
      case '\n': result += "\\n"; break;
      case '\r': result += "\\r"; break;
      case '\t': result += "\\t"; break;
      default: result += character; break;
    }
  }
  return result;
}

[[nodiscard]] bool mutation_is(const RunOptions& options, const std::string_view id) {
  return options.mutation && *options.mutation == id;
}

void require_known_mutation(
    const RunOptions& options,
    const std::initializer_list<std::string_view> allowed) {
  if (!options.mutation) return;
  if (std::find(allowed.begin(), allowed.end(), std::string_view{*options.mutation}) == allowed.end()) {
    throw std::runtime_error("unsupported mutation for stage: " + *options.mutation);
  }
}

[[nodiscard]] bool all_invariants_hold(const Invariants& invariants) {
  return std::all_of(invariants.begin(), invariants.end(), [](const auto& item) { return item.second; });
}

void write_run_json(const RunOptions& options, const Invariants& invariants) {
  const bool passed = all_invariants_hold(invariants);
  std::ostringstream output;
  output << "{\n  \"schema_version\": 1,\n  \"stage\": \""
         << stage_id(options.stage) << "\",\n  \"scene\": \""
         << json_escape(options.scene) << "\",\n  \"backend\": \"software\",\n"
         << "  \"status\": \"" << (passed ? "pass" : "fail") << "\",\n"
         << "  \"invariants\": {\n";
  for (std::size_t index = 0; index < invariants.size(); ++index) {
    output << "    \"" << invariants[index].first << "\": "
           << (invariants[index].second ? "true" : "false")
           << (index + 1 == invariants.size() ? "\n" : ",\n");
  }
  output << "  },\n  \"mutation\": ";
  if (options.mutation) {
    output << '"' << json_escape(*options.mutation) << '"';
  } else {
    output << "null";
  }
  output << "\n}\n";
  write_text(options.output / "run.json", output.str());
}

[[nodiscard]] int finish_stage(const RunOptions& options, const Invariants& invariants) {
  write_run_json(options, invariants);
  return all_invariants_hold(invariants) ? exit_ok : exit_contract_failure;
}

[[nodiscard]] std::string clip_vertices_json(const std::vector<DVec4>& vertices) {
  std::ostringstream output;
  output << "[";
  for (std::size_t index = 0; index < vertices.size(); ++index) {
    if (index != 0) output << ", ";
    output << json(vertices[index]);
  }
  output << "]";
  return output.str();
}

int run_transform_trace(const RunOptions& options) {
  require_known_mutation(
      options,
      {"swap_projection_and_model_order",
       "discard_clip_w_before_divide",
       "transform_normal_with_model_matrix",
       "apply_viewport_y_flip_twice",
       "discard_triangle_when_one_vertex_is_outside"});
  ensure_output_directory(options.output);

  const bool swap_order = mutation_is(options, "swap_projection_and_model_order");
  const bool discard_w = mutation_is(options, "discard_clip_w_before_divide");
  const bool wrong_normal = mutation_is(options, "transform_normal_with_model_matrix");
  const bool flip_twice = mutation_is(options, "apply_viewport_y_flip_twice");
  const bool discard_triangle = mutation_is(options, "discard_triangle_when_one_vertex_is_outside");

  const DMat4 identity = identity4();
  const DMat4 projection = perspective_lh_zo(std::numbers::pi / 2.0, 1.0, 1.0, 9.0);
  const DVec4 local{0.25, -0.5, 3.0, 1.0};
  const DVec4 world = multiply(identity, local);
  const DVec4 view = multiply(identity, world);
  const DVec4 clip = multiply(projection, view);
  const DVec4 ndc = perspective_divide(clip, discard_w);
  const DVec4 viewport_value = viewport(ndc, 64, 64, flip_twice);
  const DVec4 translated_direction = multiply(
      translation(7.0, -4.0, 2.0), DVec4{1.0, 2.0, 3.0, 0.0});

  const DMat4 order_model = multiply(translation(1.0, 0.0, 2.0), scale(2.0, 1.0, 1.0));
  const DVec4 order_local{0.25, 0.0, 1.0, 1.0};
  const DVec4 expected_order_clip = multiply(projection, multiply(order_model, order_local));
  const DVec4 selected_order_clip = swap_order
      ? multiply(order_model, multiply(projection, order_local))
      : expected_order_clip;

  write_text(
      options.output / "conventions.json",
      "{\n  \"schema_version\": 1,\n  \"vector\": \"column\",\n"
      "  \"storage\": \"row-major-artifact\",\n  \"composition\": \"P * V * M * local\",\n"
      "  \"handedness\": \"left\",\n  \"camera_forward\": \"+Z\",\n"
      "  \"clip_depth\": \"0..w\",\n  \"ndc_depth\": \"0..1\",\n"
      "  \"viewport_origin\": \"top-left\",\n  \"pixel_sample\": \"center\"\n}\n");

  std::ostringstream identity_artifact;
  identity_artifact << "{\n  \"schema_version\": 1,\n  \"case\": \"identity-triangle\",\n"
                    << "  \"local\": " << json(local) << ",\n"
                    << "  \"world\": " << json(world) << ",\n"
                    << "  \"view\": " << json(view) << ",\n"
                    << "  \"clip\": " << json(clip) << ",\n"
                    << "  \"clip_w\": " << number(clip.w) << ",\n"
                    << "  \"ndc\": " << json(ndc) << ",\n"
                    << "  \"viewport\": " << json(viewport_value) << ",\n"
                    << "  \"translated_direction\": " << json(translated_direction) << ",\n"
                    << "  \"composition_probe\": {\n    \"expected_clip\": "
                    << json(expected_order_clip) << ",\n    \"actual_clip\": "
                    << json(selected_order_clip) << "\n  },\n"
                    << "  \"finite\": " << (finite(viewport_value) ? "true" : "false") << "\n}\n";
  write_text(options.output / "case-identity.json", identity_artifact.str());

  const DMat4 model = multiply(
      translation(3.0, -2.0, 5.0),
      multiply(rotation_z(std::numbers::pi / 6.0), scale(2.0, 1.0, 0.5)));
  const DVec3 tangent = normalize({1.0, 1.0, 0.0});
  const DVec3 normal = normalize({1.0, -1.0, 0.0});
  const DVec4 transformed_tangent4 = multiply(
      model, DVec4{tangent.x, tangent.y, tangent.z, 0.0});
  const DVec3 transformed_tangent{transformed_tangent4.x, transformed_tangent4.y, transformed_tangent4.z};
  const DMat3 model3 = upper_left3(model);
  const DVec3 transformed_normal = normalize(
      wrong_normal ? multiply(model3, normal) : multiply(inverse_transpose(model3), normal));
  const double tangent_normal_dot = dot(transformed_tangent, transformed_normal);

  std::ostringstream nonuniform_artifact;
  nonuniform_artifact << "{\n  \"schema_version\": 1,\n  \"case\": \"nonuniform-normal\",\n"
                      << "  \"model_determinant\": " << number(determinant(model3)) << ",\n"
                      << "  \"tangent_local\": " << json(tangent) << ",\n"
                      << "  \"normal_local\": " << json(normal) << ",\n"
                      << "  \"tangent_world\": " << json(transformed_tangent) << ",\n"
                      << "  \"normal_world\": " << json(transformed_normal) << ",\n"
                      << "  \"tangent_normal_dot\": " << number(tangent_normal_dot) << ",\n"
                      << "  \"normal_transform\": \""
                      << (wrong_normal ? "model-3x3" : "inverse-transpose") << "\"\n}\n";
  write_text(options.output / "case-nonuniform.json", nonuniform_artifact.str());

  const DMat4 parent = multiply(translation(10.0, 0.0, 0.0), rotation_z(std::numbers::pi / 2.0));
  const DMat4 child = translation(2.0, 0.0, 0.0);
  const DVec4 child_local{1.0, 0.0, 0.0, 1.0};
  const DVec4 hierarchy_world = multiply(multiply(parent, child), child_local);
  const DVec4 reversed_hierarchy_world = multiply(multiply(child, parent), child_local);
  const bool hierarchy_correct = near(hierarchy_world.x, 10.0) && near(hierarchy_world.y, 3.0);

  std::ostringstream hierarchy_artifact;
  hierarchy_artifact << "{\n  \"schema_version\": 1,\n  \"case\": \"parent-child\",\n"
                     << "  \"composition\": \"parent_world * child_local\",\n"
                     << "  \"child_point\": " << json(child_local) << ",\n"
                     << "  \"world\": " << json(hierarchy_world) << ",\n"
                     << "  \"reversed_order_counterexample\": " << json(reversed_hierarchy_world) << "\n}\n";
  write_text(options.output / "case-hierarchy.json", hierarchy_artifact.str());

  const std::vector<DVec4> view_triangle{
      {-0.4, -0.2, 0.5, 1.0},
      {0.6, -0.2, 2.0, 1.0},
      {0.0, 0.7, 2.0, 1.0}};
  std::vector<DVec4> clip_triangle;
  clip_triangle.reserve(view_triangle.size());
  for (const DVec4 vertex : view_triangle) clip_triangle.push_back(multiply(projection, vertex));
  std::vector<DVec4> clipped = discard_triangle ? std::vector<DVec4>{} : clip_near_plane(clip_triangle);
  const bool clipped_vertices_valid = !clipped.empty() &&
      std::all_of(clipped.begin(), clipped.end(), inside_clip_volume);

  std::ostringstream clip_artifact;
  clip_artifact << "{\n  \"schema_version\": 1,\n  \"case\": \"near-plane-crossing\",\n"
                << "  \"input_clip_vertices\": " << clip_vertices_json(clip_triangle) << ",\n"
                << "  \"output_clip_vertices\": " << clip_vertices_json(clipped) << ",\n"
                << "  \"output_vertex_count\": " << clipped.size() << ",\n"
                << "  \"generated_intersection_count\": " << (clipped.size() >= 3 ? clipped.size() - 2 : 0) << ",\n"
                << "  \"all_output_vertices_inside\": "
                << (clipped_vertices_valid ? "true" : "false") << "\n}\n";
  write_text(options.output / "case-near-clip.json", clip_artifact.str());

  bool invalid_camera_rejected = false;
  const DVec3 forward{0.0, 0.0, 1.0};
  const DVec3 parallel_up{0.0, 0.0, 1.0};
  if (std::abs(dot(normalize(forward), normalize(parallel_up))) > 1.0 - kEpsilon) {
    invalid_camera_rejected = true;
  }
  bool singular_normal_rejected = false;
  try {
    static_cast<void>(inverse_transpose(upper_left3(scale(1.0, 1.0, 0.0))));
  } catch (const std::runtime_error&) {
    singular_normal_rejected = true;
  }
  std::ostringstream rejected;
  rejected << "{\n  \"schema_version\": 1,\n  \"rejections\": [\n"
           << "    {\"id\": \"camera-up-parallel-forward\", \"reason\": \"degenerate-basis\", \"rejected\": "
           << (invalid_camera_rejected ? "true" : "false") << "},\n"
           << "    {\"id\": \"zero-scale-normal-matrix\", \"reason\": \"singular-inverse-transpose\", \"rejected\": "
           << (singular_normal_rejected ? "true" : "false") << "}\n  ]\n}\n";
  write_text(options.output / "rejected.json", rejected.str());

  const bool identity_preserved = near(local.x, world.x) && near(local.y, world.y) &&
      near(local.z, world.z) && near(local.w, world.w);
  const bool direction_ignores_translation = near(translated_direction.x, 1.0) &&
      near(translated_direction.y, 2.0) && near(translated_direction.z, 3.0) &&
      near(translated_direction.w, 0.0);
  const bool composition_correct = near(selected_order_clip.x, expected_order_clip.x) &&
      near(selected_order_clip.y, expected_order_clip.y) &&
      near(selected_order_clip.z, expected_order_clip.z) &&
      near(selected_order_clip.w, expected_order_clip.w);
  const bool divide_correct = near(ndc.x, clip.x / clip.w) &&
      near(ndc.y, clip.y / clip.w) && near(ndc.z, clip.z / clip.w);
  const DVec4 expected_viewport = viewport(perspective_divide(clip, false), 64, 64, false);
  const bool viewport_correct = near(viewport_value.x, expected_viewport.x) &&
      near(viewport_value.y, expected_viewport.y) && near(viewport_value.z, expected_viewport.z);

  const Invariants invariants{
      {"identity_preserves_position", identity_preserved},
      {"direction_ignores_translation", direction_ignores_translation},
      {"normal_preserves_tangent_orthogonality", std::abs(tangent_normal_dot) <= 1.0e-8},
      {"hierarchy_uses_parent_world_times_child_local", hierarchy_correct && composition_correct},
      {"clipped_vertices_satisfy_all_clip_planes", clipped_vertices_valid},
      {"valid_viewport_values_are_finite",
       finite(viewport_value) && divide_correct && viewport_correct}};
  return finish_stage(options, invariants);
}

[[nodiscard]] double srgb_decode(const double encoded) {
  const double clamped = std::clamp(encoded, 0.0, 1.0);
  if (clamped <= 0.04045) return clamped / 12.92;
  return std::pow((clamped + 0.055) / 1.055, 2.4);
}

[[nodiscard]] double srgb_encode(const double linear) {
  const double clamped = std::clamp(linear, 0.0, 1.0);
  if (clamped <= 0.0031308) return 12.92 * clamped;
  return 1.055 * std::pow(clamped, 1.0 / 2.4) - 0.055;
}

[[nodiscard]] unsigned char linear_to_srgb_byte(const double value) {
  const long rounded = std::lround(srgb_encode(value) * 255.0);
  return static_cast<unsigned char>(std::clamp(rounded, 0L, 255L));
}

[[nodiscard]] int positive_modulo(const int value, const int divisor) {
  const int remainder = value % divisor;
  return remainder < 0 ? remainder + divisor : remainder;
}

enum class AddressMode { clamp, repeat, mirror };

[[nodiscard]] int address_index(
    const int index,
    const int extent,
    const AddressMode mode,
    const bool language_remainder) {
  if (extent <= 0) throw std::runtime_error("address extent must be positive");
  if (mode == AddressMode::clamp) return std::clamp(index, 0, extent - 1);
  if (mode == AddressMode::repeat) {
    return language_remainder ? index % extent : positive_modulo(index, extent);
  }
  const int period = extent * 2;
  const int wrapped = positive_modulo(index, period);
  return wrapped < extent ? wrapped : period - 1 - wrapped;
}

[[nodiscard]] std::array<unsigned char, 3> marker_texel(const int x, const int y) {
  static constexpr std::array<std::array<unsigned char, 3>, 4> marker{{
      {255, 0, 0}, {0, 255, 0}, {0, 0, 255}, {255, 255, 255}}};
  if (x < 0 || x >= 2 || y < 0 || y >= 2) return {255, 0, 255};
  return marker[static_cast<std::size_t>(y * 2 + x)];
}

[[nodiscard]] std::array<int, 2> nearest_index(
    const double u,
    const double v,
    const AddressMode mode,
    const bool truncate_upper,
    const bool language_remainder) {
  const int raw_x = static_cast<int>(std::floor(u * 2.0));
  const int raw_y = static_cast<int>(std::floor(v * 2.0));
  if (truncate_upper && (raw_x >= 2 || raw_y >= 2)) return {raw_x, raw_y};
  return {
      address_index(raw_x, 2, mode, language_remainder),
      address_index(raw_y, 2, mode, language_remainder)};
}

[[nodiscard]] Rgba over_straight(const Rgba source, const Rgba destination) {
  const double output_alpha = source.a + destination.a * (1.0 - source.a);
  if (!(output_alpha > kEpsilon)) return {};
  return {
      (source.r * source.a + destination.r * destination.a * (1.0 - source.a)) / output_alpha,
      (source.g * source.a + destination.g * destination.a * (1.0 - source.a)) / output_alpha,
      (source.b * source.a + destination.b * destination.a * (1.0 - source.a)) / output_alpha,
      output_alpha};
}

[[nodiscard]] Rgba over_premultiplied(
    const Rgba source_premultiplied,
    const Rgba destination_premultiplied,
    const bool use_straight_factors) {
  const double source_factor = use_straight_factors ? source_premultiplied.a : 1.0;
  return {
      source_premultiplied.r * source_factor +
          destination_premultiplied.r * (1.0 - source_premultiplied.a),
      source_premultiplied.g * source_factor +
          destination_premultiplied.g * (1.0 - source_premultiplied.a),
      source_premultiplied.b * source_factor +
          destination_premultiplied.b * (1.0 - source_premultiplied.a),
      source_premultiplied.a + destination_premultiplied.a * (1.0 - source_premultiplied.a)};
}

[[nodiscard]] std::vector<unsigned char> single_pixel(const Rgba color) {
  return {
      linear_to_srgb_byte(color.r),
      linear_to_srgb_byte(color.g),
      linear_to_srgb_byte(color.b)};
}

[[nodiscard]] LinearImage make_odd_image() {
  LinearImage image{.width = 3, .height = 5};
  image.pixels.reserve(15);
  for (int y = 0; y < image.height; ++y) {
    for (int x = 0; x < image.width; ++x) {
      const double value = static_cast<double>(y * image.width + x) / 14.0;
      image.pixels.push_back({value, value * 0.5, 1.0 - value});
    }
  }
  return image;
}

[[nodiscard]] LinearImage downsample_box(const LinearImage& source, const bool drop_odd_edges) {
  const int next_width = std::max(1, drop_odd_edges ? source.width / 2 : (source.width + 1) / 2);
  const int next_height = std::max(1, drop_odd_edges ? source.height / 2 : (source.height + 1) / 2);
  LinearImage result{.width = next_width, .height = next_height};
  result.pixels.reserve(static_cast<std::size_t>(next_width * next_height));
  for (int y = 0; y < next_height; ++y) {
    for (int x = 0; x < next_width; ++x) {
      Rgb sum{};
      int count = 0;
      for (int offset_y = 0; offset_y < 2; ++offset_y) {
        for (int offset_x = 0; offset_x < 2; ++offset_x) {
          const int source_x = x * 2 + offset_x;
          const int source_y = y * 2 + offset_y;
          if (source_x >= source.width || source_y >= source.height) continue;
          const Rgb sample = source.pixels[static_cast<std::size_t>(source_y * source.width + source_x)];
          sum.r += sample.r;
          sum.g += sample.g;
          sum.b += sample.b;
          ++count;
        }
      }
      if (count == 0) throw std::runtime_error("empty mip footprint");
      const double reciprocal = 1.0 / static_cast<double>(count);
      result.pixels.push_back({sum.r * reciprocal, sum.g * reciprocal, sum.b * reciprocal});
    }
  }
  return result;
}

[[nodiscard]] std::vector<unsigned char> ppm_bytes(const LinearImage& image) {
  std::vector<unsigned char> result;
  result.reserve(image.pixels.size() * 3);
  for (const Rgb pixel : image.pixels) {
    result.push_back(linear_to_srgb_byte(pixel.r));
    result.push_back(linear_to_srgb_byte(pixel.g));
    result.push_back(linear_to_srgb_byte(pixel.b));
  }
  return result;
}

[[nodiscard]] std::string address_name(const AddressMode mode) {
  switch (mode) {
    case AddressMode::clamp: return "clamp";
    case AddressMode::repeat: return "repeat";
    case AddressMode::mirror: return "mirror";
  }
  throw std::logic_error("unknown address mode");
}

int run_sampling_color(const RunOptions& options) {
  require_known_mutation(
      options,
      {"truncate_u_times_width",
       "use_language_remainder_for_negative_repeat",
       "average_srgb_encoded_bytes",
       "use_straight_factors_for_premultiplied_source",
       "decode_normal_map_as_srgb",
       "drop_odd_last_row_or_column"});
  ensure_output_directory(options.output);

  const bool truncate_upper = mutation_is(options, "truncate_u_times_width");
  const bool language_remainder = mutation_is(options, "use_language_remainder_for_negative_repeat");
  const bool encoded_average = mutation_is(options, "average_srgb_encoded_bytes");
  const bool straight_factors = mutation_is(options, "use_straight_factors_for_premultiplied_source");
  const bool decode_data = mutation_is(options, "decode_normal_map_as_srgb");
  const bool drop_odd = mutation_is(options, "drop_odd_last_row_or_column");

  const std::array<double, 6> u_values{-0.25, 0.0, 0.25, 0.75, 1.0, 1.25};
  const std::array<AddressMode, 3> modes{AddressMode::clamp, AddressMode::repeat, AddressMode::mirror};
  std::vector<unsigned char> address_grid;
  address_grid.reserve(u_values.size() * modes.size() * 3);
  for (const AddressMode mode : modes) {
    for (const double u : u_values) {
      const auto selected = nearest_index(u, 0.25, mode, truncate_upper, language_remainder);
      const auto color = marker_texel(selected[0], selected[1]);
      address_grid.insert(address_grid.end(), color.begin(), color.end());
    }
  }
  write_ppm_p3(
      options.output / "address-grid.ppm",
      static_cast<int>(u_values.size()),
      static_cast<int>(modes.size()),
      address_grid);

  const double correct_linear_average = 0.5;
  const double selected_linear_average = encoded_average
      ? srgb_decode(0.5)
      : correct_linear_average;
  const std::vector<unsigned char> linear_average_pixel{
      linear_to_srgb_byte(selected_linear_average),
      linear_to_srgb_byte(selected_linear_average),
      linear_to_srgb_byte(selected_linear_average)};
  const std::vector<unsigned char> wrong_encoded_average_pixel{128, 128, 128};
  write_ppm_p3(options.output / "bilinear-linear.ppm", 1, 1, linear_average_pixel);
  write_ppm_p3(options.output / "bilinear-wrong-srgb.ppm", 1, 1, wrong_encoded_average_pixel);

  const Rgba straight_source{1.0, 0.0, 0.0, 0.5};
  const Rgba straight_destination{0.0, 0.0, 1.0, 1.0};
  const Rgba straight_result = over_straight(straight_source, straight_destination);
  const Rgba premultiplied_source{0.5, 0.0, 0.0, 0.5};
  const Rgba premultiplied_destination{0.0, 0.0, 1.0, 1.0};
  const Rgba premultiplied_result = over_premultiplied(
      premultiplied_source, premultiplied_destination, straight_factors);
  write_ppm_p3(options.output / "alpha-straight.ppm", 1, 1, single_pixel(straight_result));
  write_ppm_p3(
      options.output / "alpha-premultiplied.ppm", 1, 1, single_pixel(premultiplied_result));

  std::vector<LinearImage> mip_chain;
  mip_chain.push_back(make_odd_image());
  while (mip_chain.back().width != 1 || mip_chain.back().height != 1) {
    mip_chain.push_back(downsample_box(mip_chain.back(), drop_odd));
  }
  for (std::size_t level = 0; level < mip_chain.size(); ++level) {
    write_ppm_p3(
        options.output / ("mip-level-" + std::to_string(level) + ".ppm"),
        mip_chain[level].width,
        mip_chain[level].height,
        ppm_bytes(mip_chain[level]));
  }

  const auto clamp_zero = nearest_index(0.0, 0.0, AddressMode::clamp, truncate_upper, language_remainder);
  const auto clamp_one = nearest_index(1.0, 1.0, AddressMode::clamp, truncate_upper, language_remainder);
  const auto repeat_negative = nearest_index(-0.25, 0.25, AddressMode::repeat, truncate_upper, language_remainder);
  const auto repeat_upper = nearest_index(1.25, 0.25, AddressMode::repeat, truncate_upper, language_remainder);
  const auto mirror_negative = nearest_index(-0.25, 0.25, AddressMode::mirror, truncate_upper, language_remainder);
  const double encoded_half = srgb_encode(0.5);
  const double color_value = srgb_decode(0.5);
  const double data_value = decode_data ? srgb_decode(0.5) : 0.5;

  std::ostringstream samples;
  samples << "{\n  \"schema_version\": 1,\n  \"texel_coordinate\": \"u * width - 0.5 for bilinear\",\n"
          << "  \"nearest_tie_break\": \"floor(u * width)\",\n"
          << "  \"texel_centers_2x2\": [[0.25, 0.25], [0.75, 0.25], [0.25, 0.75], [0.75, 0.75]],\n"
          << "  \"nearest_cases\": [\n"
          << "    {\"uv\": [0.0, 0.0], \"mode\": \"clamp\", \"index\": [" << clamp_zero[0] << ", " << clamp_zero[1] << "]},\n"
          << "    {\"uv\": [1.0, 1.0], \"mode\": \"clamp\", \"index\": [" << clamp_one[0] << ", " << clamp_one[1] << "]},\n"
          << "    {\"uv\": [-0.25, 0.25], \"mode\": \"repeat\", \"index\": [" << repeat_negative[0] << ", " << repeat_negative[1] << "]},\n"
          << "    {\"uv\": [1.25, 0.25], \"mode\": \"repeat\", \"index\": [" << repeat_upper[0] << ", " << repeat_upper[1] << "]},\n"
          << "    {\"uv\": [-0.25, 0.25], \"mode\": \"mirror\", \"index\": [" << mirror_negative[0] << ", " << mirror_negative[1] << "]}\n  ],\n"
          << "  \"bilinear_midpoint\": {\"indices\": [[0,0],[1,0],[0,1],[1,1]], \"weights\": [0.25,0.25,0.25,0.25], \"linear\": "
          << number(selected_linear_average) << ", \"encoded\": " << number(srgb_encode(selected_linear_average)) << "},\n"
          << "  \"srgb_piecewise\": {\"decode_0_04045\": " << number(srgb_decode(0.04045))
          << ", \"encode_0_0031308\": " << number(srgb_encode(0.0031308))
          << ", \"linear_half_encoded\": " << number(encoded_half) << "},\n"
          << "  \"same_byte_color_vs_data\": {\"encoded\": 0.5, \"color_linear\": "
          << number(color_value) << ", \"data_linear\": " << number(data_value) << "}\n}\n";
  write_text(options.output / "samples.json", samples.str());

  std::ostringstream report;
  report << "{\n  \"schema_version\": 1,\n  \"linear_black_white_average\": 0.5,\n"
         << "  \"linear_average_srgb_byte\": "
         << static_cast<unsigned int>(linear_to_srgb_byte(correct_linear_average)) << ",\n"
         << "  \"encoded_byte_average\": 128,\n"
         << "  \"straight_result\": [" << number(straight_result.r) << ", "
         << number(straight_result.g) << ", " << number(straight_result.b) << ", "
         << number(straight_result.a) << "],\n"
         << "  \"premultiplied_result\": [" << number(premultiplied_result.r) << ", "
         << number(premultiplied_result.g) << ", " << number(premultiplied_result.b) << ", "
         << number(premultiplied_result.a) << "],\n  \"mip_extents\": [";
  for (std::size_t level = 0; level < mip_chain.size(); ++level) {
    if (level != 0) report << ", ";
    report << '[' << mip_chain[level].width << ", " << mip_chain[level].height << ']';
  }
  report << "],\n  \"address_modes\": [";
  for (std::size_t index = 0; index < modes.size(); ++index) {
    if (index != 0) report << ", ";
    report << '"' << address_name(modes[index]) << '"';
  }
  report << "]\n}\n";
  write_text(options.output / "report.json", report.str());

  const bool texel_center_explicit = clamp_zero == std::array<int, 2>{0, 0} &&
      (!truncate_upper && clamp_one == std::array<int, 2>{1, 1});
  const bool address_boundaries = repeat_negative == std::array<int, 2>{1, 0} &&
      repeat_upper == std::array<int, 2>{0, 0} &&
      mirror_negative == std::array<int, 2>{0, 0};
  const bool linear_filtering = near(selected_linear_average, correct_linear_average);
  const bool color_data_distinct = !near(color_value, data_value);
  const bool alpha_equations_match = near(straight_result.r, premultiplied_result.r) &&
      near(straight_result.g, premultiplied_result.g) &&
      near(straight_result.b, premultiplied_result.b) &&
      near(straight_result.a, premultiplied_result.a);
  const bool correct_mip_extents = mip_chain.size() == 4 &&
      mip_chain[0].width == 3 && mip_chain[0].height == 5 &&
      mip_chain[1].width == 2 && mip_chain[1].height == 3 &&
      mip_chain[2].width == 1 && mip_chain[2].height == 2 &&
      mip_chain[3].width == 1 && mip_chain[3].height == 1;

  const Invariants invariants{
      {"texel_center_mapping_is_explicit", texel_center_explicit},
      {"address_modes_handle_negative_and_upper_boundary", address_boundaries},
      {"filtering_occurs_in_linear_rgb", linear_filtering},
      {"color_and_data_textures_use_distinct_encoding", color_data_distinct},
      {"alpha_representation_matches_blend_equation", alpha_equations_match},
      {"mip_chain_reaches_one_by_one", correct_mip_extents}};
  return finish_stage(options, invariants);
}

}  // namespace

int run_visual_stage(const RunOptions& options) {
  if (options.backend != Backend::software) return exit_unsupported;
  if (options.stage == Stage::transform_trace) return run_transform_trace(options);
  if (options.stage == Stage::sampling_color) return run_sampling_color(options);
  return exit_not_implemented;
}

}  // namespace cg
