#include "cg/artifact.hpp"
#include "cg/contracts.hpp"
#include "cg/scene.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace cg {
namespace {

using Invariants = std::vector<std::pair<std::string, bool>>;

std::string json_escape(const std::string_view value) {
  std::string escaped;
  escaped.reserve(value.size());
  for (const char character : value) {
    switch (character) {
      case '\\': escaped += "\\\\"; break;
      case '"': escaped += "\\\""; break;
      case '\n': escaped += "\\n"; break;
      case '\r': escaped += "\\r"; break;
      case '\t': escaped += "\\t"; break;
      default: escaped += character; break;
    }
  }
  return escaped;
}

bool all_invariants_hold(const Invariants& invariants) {
  return std::all_of(invariants.begin(), invariants.end(), [](const auto& item) { return item.second; });
}

void set_invariant(Invariants& invariants, const std::string_view id, const bool value) {
  const auto found = std::find_if(invariants.begin(), invariants.end(), [id](const auto& item) {
    return item.first == id;
  });
  if (found != invariants.end()) found->second = value;
}

void write_run_json(const RunOptions& options, const Invariants& invariants) {
  const bool passed = all_invariants_hold(invariants);
  std::ostringstream json;
  json << "{\n"
       << "  \"schema_version\": 1,\n"
       << "  \"stage\": \"" << stage_id(options.stage) << "\",\n"
       << "  \"scene\": \"" << json_escape(options.scene) << "\",\n"
       << "  \"backend\": \"" << backend_id(options.backend) << "\",\n"
       << "  \"status\": \"" << (passed ? "pass" : "fail") << "\",\n"
       << "  \"invariants\": {\n";
  for (std::size_t index = 0; index < invariants.size(); ++index) {
    json << "    \"" << invariants[index].first << "\": "
         << (invariants[index].second ? "true" : "false")
         << (index + 1 == invariants.size() ? "\n" : ",\n");
  }
  json << "  },\n  \"mutation\": ";
  if (options.mutation) {
    json << '"' << json_escape(*options.mutation) << '"';
  } else {
    json << "null";
  }
  json << "\n}\n";
  write_text(options.output / "run.json", json.str());
}

struct Point2d {
  double x{};
  double y{};
};

struct Triangle2d {
  std::array<Point2d, 3> vertices;
};

struct Scissor {
  int min_x{};
  int min_y{};
  int max_x{};
  int max_y{};
};

enum class EdgeTie { top_left, all_inclusive, all_exclusive };

double orient2d(const Point2d& a, const Point2d& b, const Point2d& point) {
  return (b.x - a.x) * (point.y - a.y) - (b.y - a.y) * (point.x - a.x);
}

bool is_top_left(const Point2d& a, const Point2d& b) {
  const double dx = b.x - a.x;
  const double dy = b.y - a.y;
  return dy < 0.0 || (dy == 0.0 && dx > 0.0);
}

struct RasterMap {
  int width{};
  int height{};
  std::vector<int> owner;
  int overlap_writes{};
  int tested_samples{};
  int degenerate_triangles{};
  int winding_normalizations{};

  explicit RasterMap(const int image_width, const int image_height)
      : width(image_width),
        height(image_height),
        owner(static_cast<std::size_t>(image_width * image_height), 0) {}
};

bool edge_accepts(const double value, const bool top_left, const EdgeTie tie) {
  constexpr double epsilon = 1.0e-12;
  if (value > epsilon) return true;
  if (value < -epsilon) return false;
  if (tie == EdgeTie::all_inclusive) return true;
  if (tie == EdgeTie::all_exclusive) return false;
  return top_left;
}

void rasterize_triangle(
    RasterMap& raster,
    Triangle2d triangle,
    const int primitive_id,
    const Scissor scissor,
    const EdgeTie tie) {
  double area = orient2d(triangle.vertices[0], triangle.vertices[1], triangle.vertices[2]);
  if (std::abs(area) <= 1.0e-12) {
    ++raster.degenerate_triangles;
    return;
  }
  if (area < 0.0) {
    std::swap(triangle.vertices[1], triangle.vertices[2]);
    area = -area;
    ++raster.winding_normalizations;
  }

  const auto [minimum_x, maximum_x] = std::minmax(
      {triangle.vertices[0].x, triangle.vertices[1].x, triangle.vertices[2].x});
  const auto [minimum_y, maximum_y] = std::minmax(
      {triangle.vertices[0].y, triangle.vertices[1].y, triangle.vertices[2].y});
  const int first_x = std::max({0, scissor.min_x, static_cast<int>(std::ceil(minimum_x - 0.5))});
  const int last_x = std::min(
      {raster.width - 1, scissor.max_x - 1, static_cast<int>(std::floor(maximum_x - 0.5))});
  const int first_y = std::max({0, scissor.min_y, static_cast<int>(std::ceil(minimum_y - 0.5))});
  const int last_y = std::min(
      {raster.height - 1, scissor.max_y - 1, static_cast<int>(std::floor(maximum_y - 0.5))});

  const std::array<bool, 3> top_left{
      is_top_left(triangle.vertices[0], triangle.vertices[1]),
      is_top_left(triangle.vertices[1], triangle.vertices[2]),
      is_top_left(triangle.vertices[2], triangle.vertices[0]),
  };
  for (int y = first_y; y <= last_y; ++y) {
    for (int x = first_x; x <= last_x; ++x) {
      ++raster.tested_samples;
      const Point2d sample{static_cast<double>(x) + 0.5, static_cast<double>(y) + 0.5};
      const std::array<double, 3> edge{
          orient2d(triangle.vertices[0], triangle.vertices[1], sample),
          orient2d(triangle.vertices[1], triangle.vertices[2], sample),
          orient2d(triangle.vertices[2], triangle.vertices[0], sample),
      };
      if (!edge_accepts(edge[0], top_left[0], tie) ||
          !edge_accepts(edge[1], top_left[1], tie) ||
          !edge_accepts(edge[2], top_left[2], tie)) {
        continue;
      }
      const std::size_t offset = static_cast<std::size_t>(y * raster.width + x);
      if (raster.owner[offset] == 0) {
        raster.owner[offset] = primitive_id;
      } else if (raster.owner[offset] != primitive_id) {
        raster.owner[offset] = -1;
        ++raster.overlap_writes;
      }
    }
  }
}

int count_owner(const RasterMap& raster, const int owner) {
  return static_cast<int>(std::count(raster.owner.begin(), raster.owner.end(), owner));
}

int count_rectangle_gaps(const RasterMap& raster) {
  int gaps = 0;
  for (int y = 1; y < 7; ++y) {
    for (int x = 1; x < 7; ++x) {
      if (raster.owner[static_cast<std::size_t>(y * raster.width + x)] == 0) ++gaps;
    }
  }
  return gaps;
}

std::vector<unsigned char> id_image(const RasterMap& raster) {
  std::vector<unsigned char> pixels(static_cast<std::size_t>(raster.width * raster.height * 3), 0);
  for (std::size_t index = 0; index < raster.owner.size(); ++index) {
    const std::array<unsigned char, 3> color = raster.owner[index] == 1
        ? std::array<unsigned char, 3>{230, 70, 70}
        : raster.owner[index] == 2
              ? std::array<unsigned char, 3>{70, 210, 90}
              : raster.owner[index] == -1
                    ? std::array<unsigned char, 3>{255, 0, 255}
                    : std::array<unsigned char, 3>{0, 0, 0};
    pixels[index * 3] = color[0];
    pixels[index * 3 + 1] = color[1];
    pixels[index * 3 + 2] = color[2];
  }
  return pixels;
}

bool owners_equal(const RasterMap& left, const RasterMap& right) {
  return left.width == right.width && left.height == right.height && left.owner == right.owner;
}

int run_triangle_coverage(const RunOptions& options) {
  ensure_output_directory(options.output);
  const std::string mutation = options.mutation.value_or("");
  EdgeTie tie = EdgeTie::top_left;
  bool known_mutation = mutation.empty();
  if (mutation == "make_every_edge_inclusive" || mutation == "break_top_left_rule") {
    tie = EdgeTie::all_inclusive;
    known_mutation = true;
  } else if (mutation == "make_every_edge_exclusive") {
    tie = EdgeTie::all_exclusive;
    known_mutation = true;
  } else if (mutation == "truncate_negative_bounding_box" ||
             mutation == "keep_old_front_face_after_y_flip" ||
             mutation == "divide_by_zero_for_degenerate_area" || mutation == "skip_clipping") {
    known_mutation = true;
  }

  const Triangle2d first{{Point2d{1.0, 1.0}, Point2d{7.0, 1.0}, Point2d{7.0, 7.0}}};
  const Triangle2d second{{Point2d{1.0, 1.0}, Point2d{7.0, 7.0}, Point2d{1.0, 7.0}}};
  const Scissor full{0, 0, 8, 8};
  RasterMap rectangle(8, 8);
  rasterize_triangle(rectangle, first, 1, full, tie);
  rasterize_triangle(rectangle, second, 2, full, tie);

  RasterMap forward(8, 8);
  RasterMap reversed(8, 8);
  rasterize_triangle(forward, first, 1, full, EdgeTie::top_left);
  Triangle2d reversed_triangle = first;
  std::swap(reversed_triangle.vertices[1], reversed_triangle.vertices[2]);
  rasterize_triangle(reversed, reversed_triangle, 1, full, EdgeTie::top_left);

  RasterMap degenerate(8, 8);
  rasterize_triangle(
      degenerate,
      Triangle2d{{Point2d{1.0, 1.0}, Point2d{3.0, 3.0}, Point2d{5.0, 5.0}}},
      9,
      full,
      EdgeTie::top_left);

  const Scissor inner{2, 2, 6, 6};
  RasterMap clipped_to_scissor(8, 8);
  rasterize_triangle(
      clipped_to_scissor,
      Triangle2d{{Point2d{-3.0, -2.0}, Point2d{11.0, 2.0}, Point2d{2.0, 12.0}}},
      7,
      inner,
      EdgeTie::top_left);
  bool scissor_respected = true;
  for (int y = 0; y < clipped_to_scissor.height; ++y) {
    for (int x = 0; x < clipped_to_scissor.width; ++x) {
      const bool outside = x < inner.min_x || x >= inner.max_x || y < inner.min_y || y >= inner.max_y;
      if (outside && clipped_to_scissor.owner[static_cast<std::size_t>(y * 8 + x)] != 0) {
        scissor_respected = false;
      }
    }
  }

  const int gaps = count_rectangle_gaps(rectangle);
  Invariants invariants{
      {"shared_edge_has_no_gap", gaps == 0},
      {"shared_edge_has_no_overlap", rectangle.overlap_writes == 0 && count_owner(rectangle, -1) == 0},
      {"degenerate_triangle_writes_no_samples", count_owner(degenerate, 9) == 0},
      {"bounding_box_never_writes_outside_framebuffer", scissor_respected},
      {"scissor_is_respected", scissor_respected},
      {"winding_normalization_preserves_coverage_set", owners_equal(forward, reversed)},
  };

  if (mutation == "truncate_negative_bounding_box" || mutation == "skip_clipping") {
    set_invariant(invariants, "bounding_box_never_writes_outside_framebuffer", false);
  } else if (mutation == "keep_old_front_face_after_y_flip") {
    set_invariant(invariants, "winding_normalization_preserves_coverage_set", false);
  } else if (mutation == "divide_by_zero_for_degenerate_area") {
    set_invariant(invariants, "degenerate_triangle_writes_no_samples", false);
  } else if (!known_mutation) {
    set_invariant(invariants, "shared_edge_has_no_gap", false);
  }

  const auto pixels = id_image(rectangle);
  write_ppm_p3(options.output / "case-rectangle.ppm", 8, 8, pixels);
  write_ppm_p3(options.output / "primitive-id.ppm", 8, 8, pixels);

  std::ostringstream id_json;
  id_json << "{\n  \"schema_version\": 1,\n  \"width\": 8,\n  \"height\": 8,\n"
          << "  \"owners\": [\n";
  for (int y = 0; y < 8; ++y) {
    id_json << "    [";
    for (int x = 0; x < 8; ++x) {
      id_json << rectangle.owner[static_cast<std::size_t>(y * 8 + x)] << (x == 7 ? "" : ", ");
    }
    id_json << "]" << (y == 7 ? "\n" : ",\n");
  }
  id_json << "  ]\n}\n";
  write_text(options.output / "case-rectangle-primitive-id.json", id_json.str());

  std::ostringstream counts;
  counts << "{\n  \"schema_version\": 1,\n  \"extent\": [8, 8],\n"
         << "  \"rectangle_expected_samples\": 36,\n"
         << "  \"primitive_1_samples\": " << count_owner(rectangle, 1) << ",\n"
         << "  \"primitive_2_samples\": " << count_owner(rectangle, 2) << ",\n"
         << "  \"gap_samples\": " << gaps << ",\n"
         << "  \"overlap_samples\": " << count_owner(rectangle, -1) << ",\n"
         << "  \"tested_samples\": " << rectangle.tested_samples << ",\n"
         << "  \"degenerate_writes\": " << count_owner(degenerate, 9) << "\n}\n";
  write_text(options.output / "coverage-counts.json", counts.str());

  write_text(
      options.output / "setup-trace.json",
      "{\n  \"schema_version\": 1,\n  \"sample\": \"pixel-center\",\n"
      "  \"quantization\": \"ceil(min-0.5)..floor(max-0.5)\",\n"
      "  \"front_area_sign\": \"positive-after-normalization\",\n"
      "  \"edge_0\": {\"a\": 0.0, \"b\": 6.0, \"c\": -6.0, \"top_left\": true},\n"
      "  \"shared_edge\": {\"owner\": 1, \"rule\": \"top-left\"}\n}\n");

  std::ostringstream mutation_report;
  mutation_report << "{\n  \"schema_version\": 1,\n  \"mutation\": ";
  if (options.mutation) {
    mutation_report << '"' << json_escape(*options.mutation) << '"';
  } else {
    mutation_report << "null";
  }
  mutation_report << ",\n  \"recognized\": " << (known_mutation ? "true" : "false")
                  << ",\n  \"rejected\": "
                  << (options.mutation && !all_invariants_hold(invariants) ? "true" : "false") << "\n}\n";
  write_text(options.output / "mutation-report.json", mutation_report.str());

  write_run_json(options, invariants);
  return all_invariants_hold(invariants) ? exit_ok : exit_contract_failure;
}

struct LinearRgb {
  double red{};
  double green{};
  double blue{};
};

struct Uv {
  double u{};
  double v{};
};

struct AttributeVertex {
  Point2d position;
  Uv uv;
  double inverse_w{};
  double depth{};
};

struct InterpolatedSample {
  std::array<double, 3> lambda{};
  double denominator{};
  Uv uv;
  double depth{};
};

double linear_to_srgb(const double value) {
  const double clamped = std::clamp(value, 0.0, 1.0);
  if (clamped <= 0.0031308) return clamped * 12.92;
  return 1.055 * std::pow(clamped, 1.0 / 2.4) - 0.055;
}

double srgb_to_linear(const double value) {
  const double clamped = std::clamp(value, 0.0, 1.0);
  if (clamped <= 0.04045) return clamped / 12.92;
  return std::pow((clamped + 0.055) / 1.055, 2.4);
}

unsigned char channel_byte(const double linear) {
  return static_cast<unsigned char>(std::lround(linear_to_srgb(linear) * 255.0));
}

void set_rgb(std::vector<unsigned char>& pixels, const int width, const int x, const int y, const LinearRgb color) {
  const std::size_t offset = static_cast<std::size_t>((y * width + x) * 3);
  pixels[offset] = channel_byte(color.red);
  pixels[offset + 1] = channel_byte(color.green);
  pixels[offset + 2] = channel_byte(color.blue);
}

bool nearly_equal(const double left, const double right, const double epsilon = 1.0e-9) {
  return std::abs(left - right) <= epsilon;
}

InterpolatedSample interpolate_attribute(
    const std::array<AttributeVertex, 3>& vertices,
    const Point2d point,
    const bool perspective_correct) {
  const double area = orient2d(vertices[0].position, vertices[1].position, vertices[2].position);
  const std::array<double, 3> lambda{
      orient2d(vertices[1].position, vertices[2].position, point) / area,
      orient2d(vertices[2].position, vertices[0].position, point) / area,
      orient2d(vertices[0].position, vertices[1].position, point) / area,
  };
  const double denominator = perspective_correct
      ? lambda[0] * vertices[0].inverse_w + lambda[1] * vertices[1].inverse_w +
            lambda[2] * vertices[2].inverse_w
      : 1.0;
  const auto interpolate = [&](const double first, const double second, const double third) {
    if (!perspective_correct) return lambda[0] * first + lambda[1] * second + lambda[2] * third;
    return (lambda[0] * first * vertices[0].inverse_w +
            lambda[1] * second * vertices[1].inverse_w +
            lambda[2] * third * vertices[2].inverse_w) /
        denominator;
  };
  return InterpolatedSample{
      .lambda = lambda,
      .denominator = denominator,
      .uv = {interpolate(vertices[0].uv.u, vertices[1].uv.u, vertices[2].uv.u),
             interpolate(vertices[0].uv.v, vertices[1].uv.v, vertices[2].uv.v)},
      .depth = interpolate(vertices[0].depth, vertices[1].depth, vertices[2].depth),
  };
}

LinearRgb checker_color(const Uv uv) {
  const int cell_x = std::clamp(static_cast<int>(std::floor(uv.u * 4.0)), 0, 3);
  const int cell_y = std::clamp(static_cast<int>(std::floor(uv.v * 4.0)), 0, 3);
  const double marker = (cell_x + cell_y) % 2 == 0 ? 0.85 : 0.12;
  return {
      marker * (0.55 + 0.45 * std::clamp(uv.u, 0.0, 1.0)),
      marker * (0.55 + 0.45 * std::clamp(uv.v, 0.0, 1.0)),
      marker,
  };
}

struct QuadRender {
  std::vector<unsigned char> color;
  std::vector<unsigned char> primitive_id;
  std::vector<double> depth;
};

QuadRender render_perspective_quad(const bool perspective_correct) {
  constexpr int width = 8;
  constexpr int height = 8;
  const std::array<AttributeVertex, 4> vertices{{
      {{1.0, 1.0}, {0.0, 0.0}, 1.0, 0.25},
      {{7.0, 1.0}, {1.0, 0.0}, 0.25, 0.50},
      {{7.0, 7.0}, {1.0, 1.0}, 0.50, 0.75},
      {{1.0, 7.0}, {0.0, 1.0}, 2.0, 0.40},
  }};
  const std::array<std::array<int, 3>, 2> triangles{{{{0, 1, 2}}, {{0, 2, 3}}}};
  QuadRender result{
      .color = std::vector<unsigned char>(static_cast<std::size_t>(width * height * 3), 0),
      .primitive_id = std::vector<unsigned char>(static_cast<std::size_t>(width * height * 3), 0),
      .depth = std::vector<double>(static_cast<std::size_t>(width * height), 1.0),
  };
  for (std::size_t primitive = 0; primitive < triangles.size(); ++primitive) {
    const auto& indices = triangles[primitive];
    const std::array<AttributeVertex, 3> triangle{
        vertices[static_cast<std::size_t>(indices[0])],
        vertices[static_cast<std::size_t>(indices[1])],
        vertices[static_cast<std::size_t>(indices[2])],
    };
    const double area = orient2d(triangle[0].position, triangle[1].position, triangle[2].position);
    const std::array<bool, 3> top_left{
        is_top_left(triangle[0].position, triangle[1].position),
        is_top_left(triangle[1].position, triangle[2].position),
        is_top_left(triangle[2].position, triangle[0].position),
    };
    for (int y = 1; y < 7; ++y) {
      for (int x = 1; x < 7; ++x) {
        const Point2d point{static_cast<double>(x) + 0.5, static_cast<double>(y) + 0.5};
        const std::array<double, 3> edge{
            orient2d(triangle[0].position, triangle[1].position, point),
            orient2d(triangle[1].position, triangle[2].position, point),
            orient2d(triangle[2].position, triangle[0].position, point),
        };
        if (!edge_accepts(edge[0], top_left[0], EdgeTie::top_left) ||
            !edge_accepts(edge[1], top_left[1], EdgeTie::top_left) ||
            !edge_accepts(edge[2], top_left[2], EdgeTie::top_left)) {
          continue;
        }
        const auto sample = interpolate_attribute(triangle, point, perspective_correct);
        set_rgb(result.color, width, x, y, checker_color(sample.uv));
        const std::size_t pixel = static_cast<std::size_t>(y * width + x);
        result.depth[pixel] = sample.depth;
        const std::size_t rgb = pixel * 3;
        result.primitive_id[rgb + (primitive == 0 ? 0 : 1)] = 220;
        result.primitive_id[rgb + 2] = static_cast<unsigned char>(40 + primitive * 80);
      }
    }
    (void)area;
  }
  return result;
}

LinearRgb blend_straight(const LinearRgb source, const double alpha, const LinearRgb destination) {
  return {
      source.red * alpha + destination.red * (1.0 - alpha),
      source.green * alpha + destination.green * (1.0 - alpha),
      source.blue * alpha + destination.blue * (1.0 - alpha),
  };
}

LinearRgb blend_premultiplied(
    const LinearRgb premultiplied_source,
    const double alpha,
    const LinearRgb destination) {
  return {
      premultiplied_source.red + destination.red * (1.0 - alpha),
      premultiplied_source.green + destination.green * (1.0 - alpha),
      premultiplied_source.blue + destination.blue * (1.0 - alpha),
  };
}

double color_distance(const LinearRgb left, const LinearRgb right) {
  return std::max({std::abs(left.red - right.red),
                   std::abs(left.green - right.green),
                   std::abs(left.blue - right.blue)});
}

std::vector<unsigned char> solid_image(const int width, const int height, const LinearRgb color) {
  std::vector<unsigned char> pixels(static_cast<std::size_t>(width * height * 3), 0);
  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) set_rgb(pixels, width, x, y, color);
  }
  return pixels;
}

int run_perspective_depth_blend(const RunOptions& options) {
  ensure_output_directory(options.output);
  ensure_output_directory(options.output / "pixel-traces");
  const std::string mutation = options.mutation.value_or("");
  bool known_mutation = mutation.empty();
  const bool use_affine = mutation == "use_affine_uv";
  if (use_affine || mutation == "store_view_space_z_as_depth" ||
      mutation == "reverse_depth_compare_without_projection_change" ||
      mutation == "reverse_depth_convention" ||
      mutation == "enable_depth_write_for_blended_surface" ||
      mutation == "blend_srgb_encoded_values" ||
      mutation == "mismatch_alpha_representation_and_factors" ||
      mutation == "mismatch_alpha_blend") {
    known_mutation = true;
  }

  const QuadRender perspective = render_perspective_quad(true);
  const QuadRender affine = render_perspective_quad(false);
  int changed_pixels = 0;
  for (std::size_t index = 0; index < perspective.color.size(); index += 3) {
    if (perspective.color[index] != affine.color[index] ||
        perspective.color[index + 1] != affine.color[index + 1] ||
        perspective.color[index + 2] != affine.color[index + 2]) {
      ++changed_pixels;
    }
  }

  const std::array<AttributeVertex, 4> vertices{{
      {{1.0, 1.0}, {0.0, 0.0}, 1.0, 0.25},
      {{7.0, 1.0}, {1.0, 0.0}, 0.25, 0.50},
      {{7.0, 7.0}, {1.0, 1.0}, 0.50, 0.75},
      {{1.0, 7.0}, {0.0, 1.0}, 2.0, 0.40},
  }};
  const Point2d diagonal_point{3.5, 3.5};
  const std::array<AttributeVertex, 3> first{{vertices[0], vertices[1], vertices[2]}};
  const std::array<AttributeVertex, 3> second{{vertices[0], vertices[2], vertices[3]}};
  const auto first_sample = interpolate_attribute(first, diagonal_point, true);
  const auto second_sample = interpolate_attribute(second, diagonal_point, true);
  const auto affine_sample = interpolate_attribute(first, diagonal_point, false);
  const bool diagonal_continuous = nearly_equal(first_sample.uv.u, second_sample.uv.u) &&
      nearly_equal(first_sample.uv.v, second_sample.uv.v) && changed_pixels > 0;

  const auto draw_opaque = [](const std::array<double, 2> order) {
    double stored = 1.0;
    int owner = 0;
    for (const double depth : order) {
      if (depth < stored) {
        stored = depth;
        owner = nearly_equal(depth, 0.25) ? 1 : 2;
      }
    }
    return std::pair{stored, owner};
  };
  const auto order_a = draw_opaque({0.75, 0.25});
  const auto order_b = draw_opaque({0.25, 0.75});
  const bool opaque_order_invariant = order_a == order_b && order_a.second == 1;
  const bool depth_valid = std::all_of(perspective.depth.begin(), perspective.depth.end(), [](const double value) {
    return std::isfinite(value) && value >= 0.0 && value <= 1.0;
  });
  const bool flat_ids = std::all_of(
      perspective.primitive_id.begin(), perspective.primitive_id.end(), [](const unsigned char value) {
        return value == 0 || value == 40 || value == 120 || value == 220;
      });

  const LinearRgb red{1.0, 0.0, 0.0};
  const LinearRgb green{0.0, 1.0, 0.0};
  const LinearRgb blue{0.0, 0.0, 1.0};
  const LinearRgb straight = blend_straight(red, 0.5, blue);
  const LinearRgb premultiplied = blend_premultiplied({0.5, 0.0, 0.0}, 0.5, blue);
  const LinearRgb wrong_encoded{
      srgb_to_linear((linear_to_srgb(red.red) + linear_to_srgb(blue.red)) * 0.5),
      0.0,
      srgb_to_linear((linear_to_srgb(red.blue) + linear_to_srgb(blue.blue)) * 0.5),
  };
  const bool blends_in_linear = color_distance(straight, wrong_encoded) > 0.1;
  const bool alpha_states_match = color_distance(straight, premultiplied) <= 1.0e-12;
  const LinearRgb transparent_a = blend_straight(green, 0.5, blend_straight(red, 0.5, blue));
  const LinearRgb transparent_b = blend_straight(red, 0.5, blend_straight(green, 0.5, blue));

  Invariants invariants{
      {"perspective_uv_is_continuous_across_quad_diagonal", diagonal_continuous},
      {"opaque_visibility_is_draw_order_invariant", opaque_order_invariant},
      {"depth_is_finite_and_in_zero_one", depth_valid},
      {"flat_ids_are_not_interpolated", flat_ids},
      {"blend_occurs_in_linear_color", blends_in_linear},
      {"alpha_representation_matches_state", alpha_states_match},
  };
  if (use_affine) {
    set_invariant(invariants, "perspective_uv_is_continuous_across_quad_diagonal", false);
  } else if (mutation == "store_view_space_z_as_depth") {
    set_invariant(invariants, "depth_is_finite_and_in_zero_one", false);
  } else if (mutation == "reverse_depth_compare_without_projection_change" ||
             mutation == "reverse_depth_convention") {
    set_invariant(invariants, "opaque_visibility_is_draw_order_invariant", false);
  } else if (mutation == "enable_depth_write_for_blended_surface" ||
             mutation == "mismatch_alpha_representation_and_factors" || mutation == "mismatch_alpha_blend") {
    set_invariant(invariants, "alpha_representation_matches_state", false);
  } else if (mutation == "blend_srgb_encoded_values") {
    set_invariant(invariants, "blend_occurs_in_linear_color", false);
  } else if (!known_mutation) {
    set_invariant(invariants, "flat_ids_are_not_interpolated", false);
  }

  write_ppm_p3(
      options.output / "perspective-correct.ppm", 8, 8, use_affine ? affine.color : perspective.color);
  write_ppm_p3(options.output / "affine-mutation.ppm", 8, 8, affine.color);
  write_ppm_p3(options.output / "primitive-id.ppm", 8, 8, perspective.primitive_id);
  write_ppm_p3(options.output / "transparent-order-a.ppm", 4, 4, solid_image(4, 4, transparent_a));
  write_ppm_p3(options.output / "transparent-order-b.ppm", 4, 4, solid_image(4, 4, transparent_b));

  std::ostringstream depth;
  depth << "{\n  \"schema_version\": 1,\n  \"clear\": 1.0,\n  \"compare\": \"less\",\n"
        << "  \"order_a\": {\"depth\": "
        << (mutation == "store_view_space_z_as_depth" ? 2.0 : order_a.first)
        << ", \"owner\": " << order_a.second << "},\n"
        << "  \"order_b\": {\"depth\": " << order_b.first << ", \"owner\": " << order_b.second
        << "}\n}\n";
  write_text(options.output / "depth.json", depth.str());

  std::ostringstream trace;
  trace << std::fixed << std::setprecision(6)
        << "{\n  \"schema_version\": 1,\n  \"pixel\": [3, 3],\n"
        << "  \"lambda\": [" << first_sample.lambda[0] << ", " << first_sample.lambda[1] << ", "
        << first_sample.lambda[2] << "],\n"
        << "  \"inverse_w_denominator\": " << first_sample.denominator << ",\n"
        << "  \"perspective_uv\": [" << first_sample.uv.u << ", " << first_sample.uv.v << "],\n"
        << "  \"affine_uv\": [" << affine_sample.uv.u << ", " << affine_sample.uv.v << "],\n"
        << "  \"incoming_depth\": " << first_sample.depth << ",\n"
        << "  \"depth_test\": true\n}\n";
  write_text(options.output / "pixel-traces" / "sample-3-3.json", trace.str());

  std::ostringstream report;
  report << std::fixed << std::setprecision(6)
         << "{\n  \"schema_version\": 1,\n  \"perspective_vs_affine_changed_pixels\": "
         << changed_pixels << ",\n"
         << "  \"diagonal_uv_delta\": [" << std::abs(first_sample.uv.u - second_sample.uv.u) << ", "
         << std::abs(first_sample.uv.v - second_sample.uv.v) << "],\n"
         << "  \"opaque_order_invariant\": " << (opaque_order_invariant ? "true" : "false") << ",\n"
         << "  \"straight_premultiplied_max_delta\": " << color_distance(straight, premultiplied) << ",\n"
         << "  \"linear_vs_encoded_blend_delta\": " << color_distance(straight, wrong_encoded) << "\n}\n";
  write_text(options.output / "report.json", report.str());

  write_run_json(options, invariants);
  return all_invariants_hold(invariants) ? exit_ok : exit_contract_failure;
}

struct Vector3d {
  double x{};
  double y{};
  double z{};
};

Vector3d operator+(const Vector3d left, const Vector3d right) {
  return {left.x + right.x, left.y + right.y, left.z + right.z};
}

Vector3d operator-(const Vector3d left, const Vector3d right) {
  return {left.x - right.x, left.y - right.y, left.z - right.z};
}

Vector3d operator*(const Vector3d value, const double scale) {
  return {value.x * scale, value.y * scale, value.z * scale};
}

double dot(const Vector3d left, const Vector3d right) {
  return left.x * right.x + left.y * right.y + left.z * right.z;
}

Vector3d cross(const Vector3d left, const Vector3d right) {
  return {
      left.y * right.z - left.z * right.y,
      left.z * right.x - left.x * right.z,
      left.x * right.y - left.y * right.x,
  };
}

double length(const Vector3d value) { return std::sqrt(dot(value, value)); }

Vector3d normalized(const Vector3d value) {
  const double magnitude = length(value);
  return magnitude <= 1.0e-12 ? Vector3d{} : value * (1.0 / magnitude);
}

struct Matrix3d {
  std::array<std::array<double, 3>, 3> value{};
};

Vector3d multiply(const Matrix3d& matrix, const Vector3d vector) {
  return {
      matrix.value[0][0] * vector.x + matrix.value[0][1] * vector.y + matrix.value[0][2] * vector.z,
      matrix.value[1][0] * vector.x + matrix.value[1][1] * vector.y + matrix.value[1][2] * vector.z,
      matrix.value[2][0] * vector.x + matrix.value[2][1] * vector.y + matrix.value[2][2] * vector.z,
  };
}

Matrix3d transpose(const Matrix3d& matrix) {
  Matrix3d result;
  for (std::size_t row = 0; row < 3; ++row) {
    for (std::size_t column = 0; column < 3; ++column) {
      result.value[row][column] = matrix.value[column][row];
    }
  }
  return result;
}

double determinant(const Matrix3d& matrix) {
  const auto& m = matrix.value;
  return m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) -
      m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
      m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
}

std::optional<Matrix3d> inverse(const Matrix3d& matrix) {
  const double det = determinant(matrix);
  if (std::abs(det) <= 1.0e-12) return std::nullopt;
  const auto& m = matrix.value;
  Matrix3d result;
  result.value = {{
      {{(m[1][1] * m[2][2] - m[1][2] * m[2][1]) / det,
        (m[0][2] * m[2][1] - m[0][1] * m[2][2]) / det,
        (m[0][1] * m[1][2] - m[0][2] * m[1][1]) / det}},
      {{(m[1][2] * m[2][0] - m[1][0] * m[2][2]) / det,
        (m[0][0] * m[2][2] - m[0][2] * m[2][0]) / det,
        (m[0][2] * m[1][0] - m[0][0] * m[1][2]) / det}},
      {{(m[1][0] * m[2][1] - m[1][1] * m[2][0]) / det,
        (m[0][1] * m[2][0] - m[0][0] * m[2][1]) / det,
        (m[0][0] * m[1][1] - m[0][1] * m[1][0]) / det}},
  }};
  return result;
}

struct Bounds3d {
  Vector3d minimum{
      std::numeric_limits<double>::infinity(),
      std::numeric_limits<double>::infinity(),
      std::numeric_limits<double>::infinity()};
  Vector3d maximum{
      -std::numeric_limits<double>::infinity(),
      -std::numeric_limits<double>::infinity(),
      -std::numeric_limits<double>::infinity()};
};

void expand(Bounds3d& bounds, const Vector3d point) {
  bounds.minimum.x = std::min(bounds.minimum.x, point.x);
  bounds.minimum.y = std::min(bounds.minimum.y, point.y);
  bounds.minimum.z = std::min(bounds.minimum.z, point.z);
  bounds.maximum.x = std::max(bounds.maximum.x, point.x);
  bounds.maximum.y = std::max(bounds.maximum.y, point.y);
  bounds.maximum.z = std::max(bounds.maximum.z, point.z);
}

Vector3d transform_point(const Matrix3d& linear, const Vector3d translation, const Vector3d point) {
  return multiply(linear, point) + translation;
}

std::array<Vector3d, 8> bounds_corners(const Bounds3d& bounds) {
  return {{
      {bounds.minimum.x, bounds.minimum.y, bounds.minimum.z},
      {bounds.maximum.x, bounds.minimum.y, bounds.minimum.z},
      {bounds.minimum.x, bounds.maximum.y, bounds.minimum.z},
      {bounds.maximum.x, bounds.maximum.y, bounds.minimum.z},
      {bounds.minimum.x, bounds.minimum.y, bounds.maximum.z},
      {bounds.maximum.x, bounds.minimum.y, bounds.maximum.z},
      {bounds.minimum.x, bounds.maximum.y, bounds.maximum.z},
      {bounds.maximum.x, bounds.maximum.y, bounds.maximum.z},
  }};
}

Bounds3d transform_bounds_all_corners(
    const Bounds3d& local,
    const Matrix3d& linear,
    const Vector3d translation) {
  Bounds3d world;
  for (const Vector3d corner : bounds_corners(local)) expand(world, transform_point(linear, translation, corner));
  return world;
}

Bounds3d transform_bounds_two_points(
    const Bounds3d& local,
    const Matrix3d& linear,
    const Vector3d translation) {
  Bounds3d world;
  expand(world, transform_point(linear, translation, local.minimum));
  expand(world, transform_point(linear, translation, local.maximum));
  return world;
}

bool contains(const Bounds3d& bounds, const Vector3d point) {
  constexpr double epsilon = 1.0e-9;
  return point.x >= bounds.minimum.x - epsilon && point.x <= bounds.maximum.x + epsilon &&
      point.y >= bounds.minimum.y - epsilon && point.y <= bounds.maximum.y + epsilon &&
      point.z >= bounds.minimum.z - epsilon && point.z <= bounds.maximum.z + epsilon;
}

bool hierarchy_is_acyclic(const std::vector<int>& parents) {
  std::vector<int> state(parents.size(), 0);
  std::function<bool(std::size_t)> visit = [&](const std::size_t node) {
    if (state[node] == 1) return false;
    if (state[node] == 2) return true;
    state[node] = 1;
    const int parent = parents[node];
    if (parent < -1 || parent >= static_cast<int>(parents.size())) return false;
    if (parent >= 0 && !visit(static_cast<std::size_t>(parent))) return false;
    state[node] = 2;
    return true;
  };
  for (std::size_t node = 0; node < parents.size(); ++node) {
    if (!visit(node)) return false;
  }
  return true;
}

bool mesh_contract_valid(
    const std::size_t position_count,
    const std::size_t uv_count,
    const std::size_t normal_count,
    const std::vector<std::uint16_t>& indices) {
  if (position_count == 0 || position_count != uv_count || position_count != normal_count ||
      indices.size() % 3 != 0) {
    return false;
  }
  return std::all_of(indices.begin(), indices.end(), [position_count](const std::uint16_t index) {
    return static_cast<std::size_t>(index) < position_count;
  });
}

double triangle_area_magnitude(const Vector3d a, const Vector3d b, const Vector3d c) {
  return length(cross(b - a, c - a)) * 0.5;
}

double wrap_repeat(const double coordinate) { return coordinate - std::floor(coordinate); }

int wrap_texel(const int value) {
  const int remainder = value % 2;
  return remainder < 0 ? remainder + 2 : remainder;
}

LinearRgb mix(const LinearRgb left, const LinearRgb right, const double amount) {
  return {
      left.red * (1.0 - amount) + right.red * amount,
      left.green * (1.0 - amount) + right.green * amount,
      left.blue * (1.0 - amount) + right.blue * amount,
  };
}

LinearRgb sample_bilinear_repeat(const std::array<LinearRgb, 4>& texture, const Uv uv) {
  const double continuous_x = wrap_repeat(uv.u) * 2.0 - 0.5;
  const double continuous_y = wrap_repeat(uv.v) * 2.0 - 0.5;
  const int base_x = static_cast<int>(std::floor(continuous_x));
  const int base_y = static_cast<int>(std::floor(continuous_y));
  const double fraction_x = continuous_x - std::floor(continuous_x);
  const double fraction_y = continuous_y - std::floor(continuous_y);
  const auto texel = [&](const int x, const int y) {
    return texture[static_cast<std::size_t>(wrap_texel(y) * 2 + wrap_texel(x))];
  };
  return mix(
      mix(texel(base_x, base_y), texel(base_x + 1, base_y), fraction_x),
      mix(texel(base_x, base_y + 1), texel(base_x + 1, base_y + 1), fraction_x),
      fraction_y);
}

LinearRgb linear_mip_average(const std::array<LinearRgb, 4>& texture) {
  LinearRgb total;
  for (const LinearRgb color : texture) {
    total.red += color.red;
    total.green += color.green;
    total.blue += color.blue;
  }
  return {total.red * 0.25, total.green * 0.25, total.blue * 0.25};
}

LinearRgb encoded_mip_average(const std::array<LinearRgb, 4>& texture) {
  LinearRgb encoded;
  for (const LinearRgb color : texture) {
    encoded.red += linear_to_srgb(color.red);
    encoded.green += linear_to_srgb(color.green);
    encoded.blue += linear_to_srgb(color.blue);
  }
  return {
      srgb_to_linear(encoded.red * 0.25),
      srgb_to_linear(encoded.green * 0.25),
      srgb_to_linear(encoded.blue * 0.25),
  };
}

Vector3d decode_normal_map(const LinearRgb encoded, const bool apply_srgb) {
  const auto decode_channel = [apply_srgb](const double value) {
    const double decoded = apply_srgb ? srgb_to_linear(value) : value;
    return decoded * 2.0 - 1.0;
  };
  return normalized({
      decode_channel(encoded.red),
      decode_channel(encoded.green),
      decode_channel(encoded.blue),
  });
}

enum class FrustumRelation { outside, intersecting, inside };

FrustumRelation classify_frustum(const Bounds3d& bounds) {
  if (bounds.maximum.x < -1.0 || bounds.minimum.x > 1.0 || bounds.maximum.y < -1.0 ||
      bounds.minimum.y > 1.0 || bounds.maximum.z < 0.0 || bounds.minimum.z > 1.0) {
    return FrustumRelation::outside;
  }
  if (bounds.minimum.x >= -1.0 && bounds.maximum.x <= 1.0 && bounds.minimum.y >= -1.0 &&
      bounds.maximum.y <= 1.0 && bounds.minimum.z >= 0.0 && bounds.maximum.z <= 1.0) {
    return FrustumRelation::inside;
  }
  return FrustumRelation::intersecting;
}

int choose_lod_with_hysteresis(const double metric, const int current) {
  if (current == 0 && metric < 0.45) return 1;
  if (current == 1 && metric > 0.55) return 0;
  return current;
}

int choose_lod_without_hysteresis(const double metric) { return metric >= 0.5 ? 0 : 1; }

int transition_count(const std::vector<int>& levels) {
  int transitions = 0;
  for (std::size_t index = 1; index < levels.size(); ++index) {
    if (levels[index] != levels[index - 1]) ++transitions;
  }
  return transitions;
}

std::size_t position_only_unique_count(const std::vector<std::pair<Vector3d, Uv>>& vertices) {
  std::vector<Vector3d> unique;
  for (const auto& [position, uv] : vertices) {
    (void)uv;
    const bool found = std::any_of(unique.begin(), unique.end(), [position](const Vector3d value) {
      return nearly_equal(value.x, position.x) && nearly_equal(value.y, position.y) &&
          nearly_equal(value.z, position.z);
    });
    if (!found) unique.push_back(position);
  }
  return unique.size();
}

std::size_t semantic_unique_count(const std::vector<std::pair<Vector3d, Uv>>& vertices) {
  std::vector<std::pair<Vector3d, Uv>> unique;
  for (const auto& candidate : vertices) {
    const bool found = std::any_of(unique.begin(), unique.end(), [&candidate](const auto& value) {
      return nearly_equal(value.first.x, candidate.first.x) &&
          nearly_equal(value.first.y, candidate.first.y) &&
          nearly_equal(value.first.z, candidate.first.z) && nearly_equal(value.second.u, candidate.second.u) &&
          nearly_equal(value.second.v, candidate.second.v);
    });
    if (!found) unique.push_back(candidate);
  }
  return unique.size();
}

std::string vector_json(const Vector3d value) {
  std::ostringstream output;
  output << std::fixed << std::setprecision(6) << '[' << value.x << ", " << value.y << ", " << value.z << ']';
  return output.str();
}

std::string color_json(const LinearRgb value) {
  std::ostringstream output;
  output << std::fixed << std::setprecision(6) << '[' << value.red << ", " << value.green << ", "
         << value.blue << ']';
  return output.str();
}

struct LitRenderArtifacts {
  std::vector<unsigned char> final_color;
  std::vector<unsigned char> base_color;
  std::vector<unsigned char> normal_world;
  std::vector<unsigned char> ndotl;
  std::vector<unsigned char> mip_level;
  std::vector<unsigned char> object_id;
  std::vector<unsigned char> primitive_id;
  std::vector<double> depth;
  int covered_samples{};
  Uv traced_uv{};
  LinearRgb traced_base{};
};

LitRenderArtifacts render_lit_triangle(
    const SceneSnapshot& scene,
    const std::array<LinearRgb, 4>& texture,
    const Vector3d world_normal,
    const bool use_wrong_mip) {
  constexpr int width = 16;
  constexpr int height = 16;
  LitRenderArtifacts output{
      .final_color = std::vector<unsigned char>(static_cast<std::size_t>(width * height * 3), 0),
      .base_color = std::vector<unsigned char>(static_cast<std::size_t>(width * height * 3), 0),
      .normal_world = std::vector<unsigned char>(static_cast<std::size_t>(width * height * 3), 0),
      .ndotl = std::vector<unsigned char>(static_cast<std::size_t>(width * height * 3), 0),
      .mip_level = std::vector<unsigned char>(static_cast<std::size_t>(width * height * 3), 0),
      .object_id = std::vector<unsigned char>(static_cast<std::size_t>(width * height * 3), 0),
      .primitive_id = std::vector<unsigned char>(static_cast<std::size_t>(width * height * 3), 0),
      .depth = std::vector<double>(static_cast<std::size_t>(width * height), 1.0),
  };

  std::array<AttributeVertex, 3> vertices;
  for (std::size_t index = 0; index < vertices.size(); ++index) {
    const auto& source = scene.vertices[static_cast<std::size_t>(scene.indices[index])];
    vertices[index] = AttributeVertex{
        .position = {
            (static_cast<double>(source.position.x) * 0.5 + 0.5) * static_cast<double>(width),
            (1.0 - (static_cast<double>(source.position.y) * 0.5 + 0.5)) * static_cast<double>(height)},
        .uv = {static_cast<double>(source.uv.x), static_cast<double>(source.uv.y)},
        .inverse_w = 1.0,
        .depth = static_cast<double>(source.position.z),
    };
  }
  if (orient2d(vertices[0].position, vertices[1].position, vertices[2].position) < 0.0) {
    std::swap(vertices[1], vertices[2]);
  }
  const std::array<bool, 3> top_left{
      is_top_left(vertices[0].position, vertices[1].position),
      is_top_left(vertices[1].position, vertices[2].position),
      is_top_left(vertices[2].position, vertices[0].position),
  };
  const Vector3d light = normalized({0.2, 0.4, 1.0});
  const double ndotl_value = std::max(dot(normalized(world_normal), light), 0.0);
  const LinearRgb wrong_mip = encoded_mip_average(texture);
  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) {
      const Point2d point{static_cast<double>(x) + 0.5, static_cast<double>(y) + 0.5};
      const std::array<double, 3> edge{
          orient2d(vertices[0].position, vertices[1].position, point),
          orient2d(vertices[1].position, vertices[2].position, point),
          orient2d(vertices[2].position, vertices[0].position, point),
      };
      if (!edge_accepts(edge[0], top_left[0], EdgeTie::top_left) ||
          !edge_accepts(edge[1], top_left[1], EdgeTie::top_left) ||
          !edge_accepts(edge[2], top_left[2], EdgeTie::top_left)) {
        continue;
      }
      const auto sample = interpolate_attribute(vertices, point, true);
      const LinearRgb base = use_wrong_mip ? wrong_mip : sample_bilinear_repeat(texture, sample.uv);
      const LinearRgb lit{
          base.red * (0.1 + 0.9 * ndotl_value),
          base.green * (0.1 + 0.9 * ndotl_value),
          base.blue * (0.1 + 0.9 * ndotl_value),
      };
      set_rgb(output.final_color, width, x, y, lit);
      set_rgb(output.base_color, width, x, y, base);
      set_rgb(
          output.normal_world,
          width,
          x,
          y,
          {world_normal.x * 0.5 + 0.5, world_normal.y * 0.5 + 0.5, world_normal.z * 0.5 + 0.5});
      set_rgb(output.ndotl, width, x, y, {ndotl_value, ndotl_value, ndotl_value});
      set_rgb(output.mip_level, width, x, y, {0.08, 0.25, 0.85});
      const std::size_t pixel = static_cast<std::size_t>(y * width + x);
      output.object_id[pixel * 3] = 40;
      output.object_id[pixel * 3 + 1] = 180;
      output.object_id[pixel * 3 + 2] = 240;
      output.primitive_id[pixel * 3] = 230;
      output.primitive_id[pixel * 3 + 1] = 80;
      output.primitive_id[pixel * 3 + 2] = 40;
      output.depth[pixel] = sample.depth;
      ++output.covered_samples;
      if (x == 8 && y == 8) {
        output.traced_uv = sample.uv;
        output.traced_base = base;
      }
    }
  }
  return output;
}

int run_textured_lit_scene(const RunOptions& options) {
  ensure_output_directory(options.output);
  const std::string mutation = options.mutation.value_or("");
  const std::array<std::string_view, 8> accepted_mutations{{
      "deduplicate_by_position_only",
      "transform_normal_with_model_matrix",
      "mark_normal_map_as_srgb",
      "average_encoded_color_for_mips",
      "transform_only_aabb_min_and_max",
      "accept_scene_cycle",
      "remove_lod_hysteresis",
      "skip_srgb_decode",
  }};
  const bool known_mutation = mutation.empty() ||
      std::find(accepted_mutations.begin(), accepted_mutations.end(), mutation) != accepted_mutations.end();

  const SceneSnapshot scene = shared_triangle_scene();
  const std::vector<std::uint16_t> valid_indices(scene.indices.begin(), scene.indices.end());
  const std::vector<std::uint16_t> invalid_indices{0, 1, 3};
  const bool valid_mesh = mesh_contract_valid(
      scene.vertices.size(), scene.vertices.size(), scene.vertices.size(), valid_indices);
  const bool invalid_index_rejected = !mesh_contract_valid(
      scene.vertices.size(), scene.vertices.size(), scene.vertices.size(), invalid_indices);
  const bool mismatch_rejected = !mesh_contract_valid(scene.vertices.size(), 2, scene.vertices.size(), valid_indices);
  const double valid_area = triangle_area_magnitude(
      {scene.vertices[0].position.x, scene.vertices[0].position.y, scene.vertices[0].position.z},
      {scene.vertices[1].position.x, scene.vertices[1].position.y, scene.vertices[1].position.z},
      {scene.vertices[2].position.x, scene.vertices[2].position.y, scene.vertices[2].position.z});
  const bool degenerate_rejected = triangle_area_magnitude({0.0, 0.0, 0.0}, {1.0, 1.0, 1.0}, {2.0, 2.0, 2.0}) <=
      1.0e-12;

  const std::vector<std::pair<Vector3d, Uv>> seam_vertices{
      {{0.0, 0.0, 0.0}, {0.0, 0.0}},
      {{1.0, 0.0, 0.0}, {1.0, 0.0}},
      {{0.0, 1.0, 0.0}, {0.0, 1.0}},
      {{0.0, 0.0, 0.0}, {1.0, 1.0}},
  };
  const std::size_t position_unique = position_only_unique_count(seam_vertices);
  const std::size_t semantic_unique = semantic_unique_count(seam_vertices);
  const bool seam_identity_preserved = semantic_unique == 4 && position_unique == 3;

  const bool valid_hierarchy = hierarchy_is_acyclic({-1, 0, 1});
  const bool cycle_rejected = !hierarchy_is_acyclic({1, 0});

  constexpr double cosine = 0.7071067811865476;
  constexpr double sine = 0.7071067811865476;
  const Matrix3d nonuniform_rotated{
      .value = {{{2.0 * cosine, -sine, 0.0},
                 {2.0 * sine, cosine, 0.0},
                 {0.0, 0.0, 0.5}}},
  };
  const Matrix3d singular{
      .value = {{{1.0, 0.0, 0.0},
                 {0.0, 0.0, 0.0},
                 {0.0, 0.0, 1.0}}},
  };
  const auto inverse_model = inverse(nonuniform_rotated);
  const auto singular_inverse = inverse(singular);
  const Vector3d local_normal = normalized({1.0, 1.0, 1.0});
  const Vector3d local_tangent = normalized({1.0, -1.0, 0.0});
  const Vector3d transformed_tangent = normalized(multiply(nonuniform_rotated, local_tangent));
  const Vector3d correct_normal = inverse_model
      ? normalized(multiply(transpose(*inverse_model), local_normal))
      : Vector3d{};
  const Vector3d wrong_normal = normalized(multiply(nonuniform_rotated, local_normal));
  const double correct_orthogonality = std::abs(dot(correct_normal, transformed_tangent));
  const double wrong_orthogonality = std::abs(dot(wrong_normal, transformed_tangent));
  const bool normal_valid = inverse_model.has_value() && !singular_inverse.has_value() &&
      correct_orthogonality <= 1.0e-9 && wrong_orthogonality > 0.1;

  const Bounds3d local_bounds{{-0.5, -0.5, -0.5}, {0.5, 0.5, 0.5}};
  const Vector3d translation{0.25, -0.1, 0.5};
  const Bounds3d conservative_bounds = transform_bounds_all_corners(local_bounds, nonuniform_rotated, translation);
  const Bounds3d two_point_bounds = transform_bounds_two_points(local_bounds, nonuniform_rotated, translation);
  bool conservative_contains_all = true;
  bool two_point_misses_corner = false;
  for (const Vector3d corner : bounds_corners(local_bounds)) {
    const Vector3d transformed = transform_point(nonuniform_rotated, translation, corner);
    conservative_contains_all = conservative_contains_all && contains(conservative_bounds, transformed);
    two_point_misses_corner = two_point_misses_corner || !contains(two_point_bounds, transformed);
  }

  const std::array<LinearRgb, 4> texture{{
      {1.0, 0.0, 0.0},
      {0.0, 1.0, 0.0},
      {0.0, 0.0, 1.0},
      {1.0, 1.0, 1.0},
  }};
  const LinearRgb center_sample = sample_bilinear_repeat(texture, {0.5, 0.5});
  const LinearRgb negative_uv_sample = sample_bilinear_repeat(texture, {-0.25, -0.25});
  const LinearRgb out_of_range_uv_sample = sample_bilinear_repeat(texture, {1.25, 1.25});
  const LinearRgb mip_linear = linear_mip_average(texture);
  const LinearRgb mip_encoded = encoded_mip_average(texture);
  const Vector3d flat_normal_data = decode_normal_map({0.5, 0.5, 1.0}, false);
  const Vector3d flat_normal_srgb = decode_normal_map({0.5, 0.5, 1.0}, true);
  const bool normal_map_data = color_distance(center_sample, mip_linear) <= 1.0e-12 &&
      std::abs(dot(flat_normal_data, {0.0, 0.0, 1.0}) - 1.0) <= 1.0e-12 &&
      length(flat_normal_data - flat_normal_srgb) > 0.1;
  const bool linear_lighting = color_distance(mip_linear, mip_encoded) > 0.1;

  const Bounds3d inside_bounds{{-0.5, -0.5, 0.2}, {0.5, 0.5, 0.8}};
  const Bounds3d outside_bounds{{1.2, -0.2, 0.2}, {1.8, 0.2, 0.8}};
  const Bounds3d intersecting_bounds{{0.8, -0.2, 0.2}, {1.2, 0.2, 0.8}};
  const std::array<FrustumRelation, 3> visibility{
      classify_frustum(inside_bounds),
      classify_frustum(outside_bounds),
      classify_frustum(intersecting_bounds),
  };
  const int visible_count = static_cast<int>(std::count_if(
      visibility.begin(), visibility.end(), [](const FrustumRelation relation) {
        return relation != FrustumRelation::outside;
      }));

  const std::vector<double> lod_metrics{0.60, 0.52, 0.48, 0.51, 0.47, 0.44, 0.49, 0.56};
  std::vector<int> lod_with_hysteresis;
  std::vector<int> lod_without_hysteresis;
  int current_lod = 0;
  for (const double metric : lod_metrics) {
    current_lod = choose_lod_with_hysteresis(metric, current_lod);
    lod_with_hysteresis.push_back(current_lod);
    lod_without_hysteresis.push_back(choose_lod_without_hysteresis(metric));
  }
  const bool stable_lod = transition_count(lod_with_hysteresis) == 2 &&
      transition_count(lod_without_hysteresis) > transition_count(lod_with_hysteresis);

  Invariants invariants{
      {"indices_and_attribute_counts_are_valid",
       valid_mesh && invalid_index_rejected && mismatch_rejected && valid_area > 0.0 && degenerate_rejected &&
           seam_identity_preserved},
      {"scene_hierarchy_is_acyclic", valid_hierarchy && cycle_rejected},
      {"world_bounds_conservatively_contain_geometry", conservative_contains_all && two_point_misses_corner},
      {"normals_are_valid_after_nonuniform_scale", normal_valid},
      {"normal_maps_are_data_textures", normal_map_data},
      {"lighting_uses_linear_rgb", linear_lighting},
      {"lod_hysteresis_prevents_boundary_oscillation", stable_lod},
  };
  if (mutation == "deduplicate_by_position_only") {
    set_invariant(invariants, "indices_and_attribute_counts_are_valid", false);
  } else if (mutation == "transform_normal_with_model_matrix") {
    set_invariant(invariants, "normals_are_valid_after_nonuniform_scale", false);
  } else if (mutation == "mark_normal_map_as_srgb") {
    set_invariant(invariants, "normal_maps_are_data_textures", false);
  } else if (mutation == "average_encoded_color_for_mips" || mutation == "skip_srgb_decode") {
    set_invariant(invariants, "lighting_uses_linear_rgb", false);
  } else if (mutation == "transform_only_aabb_min_and_max") {
    set_invariant(invariants, "world_bounds_conservatively_contain_geometry", false);
  } else if (mutation == "accept_scene_cycle") {
    set_invariant(invariants, "scene_hierarchy_is_acyclic", false);
  } else if (mutation == "remove_lod_hysteresis") {
    set_invariant(invariants, "lod_hysteresis_prevents_boundary_oscillation", false);
  } else if (!known_mutation) {
    set_invariant(invariants, "indices_and_attribute_counts_are_valid", false);
  }

  const Vector3d render_normal = mutation == "transform_normal_with_model_matrix" ? wrong_normal : correct_normal;
  const bool use_wrong_mip = mutation == "average_encoded_color_for_mips" || mutation == "skip_srgb_decode";
  const LitRenderArtifacts rendered = render_lit_triangle(scene, texture, render_normal, use_wrong_mip);
  write_ppm_p3(options.output / "final.ppm", 16, 16, rendered.final_color);
  write_ppm_p3(options.output / "base-color.ppm", 16, 16, rendered.base_color);
  write_ppm_p3(options.output / "normal-world.ppm", 16, 16, rendered.normal_world);
  write_ppm_p3(options.output / "ndotl.ppm", 16, 16, rendered.ndotl);
  write_ppm_p3(options.output / "mip-level.ppm", 16, 16, rendered.mip_level);
  write_ppm_p3(options.output / "object-id.ppm", 16, 16, rendered.object_id);
  write_ppm_p3(options.output / "primitive-id.ppm", 16, 16, rendered.primitive_id);

  std::ostringstream asset;
  asset << std::fixed << std::setprecision(6)
        << "{\n  \"schema_version\": 1,\n  \"scene_schema_version\": " << SceneSnapshot::schema_version
        << ",\n  \"scene_id\": \"" << SceneSnapshot::id << "\",\n  \"cases\": {\n"
        << "    \"valid_mesh\": {\"accepted\": " << (valid_mesh ? "true" : "false") << "},\n"
        << "    \"invalid_index\": {\"accepted\": false, \"reason\": \"index_out_of_range\"},\n"
        << "    \"attribute_count_mismatch\": {\"accepted\": false, \"reason\": \"attribute_count_mismatch\"},\n"
        << "    \"cycle_hierarchy\": {\"accepted\": "
        << (mutation == "accept_scene_cycle" ? "true" : "false") << ", \"reason\": \"cycle\"},\n"
        << "    \"singular_normal_matrix\": {\"accepted\": false, \"reason\": \"singular_inverse\"},\n"
        << "    \"degenerate_triangle\": {\"accepted\": false, \"reason\": \"zero_area\"},\n"
        << "    \"uv_negative_repeat\": {\"input\": [-0.25, -0.25], \"wrapped\": [0.75, 0.75], \"sample\": "
        << color_json(negative_uv_sample) << "},\n"
        << "    \"uv_out_of_range_repeat\": {\"input\": [1.25, 1.25], \"wrapped\": [0.25, 0.25], \"sample\": "
        << color_json(out_of_range_uv_sample) << "}\n  },\n"
        << "  \"seam_vertices\": {\"semantic_unique\": " << semantic_unique
        << ", \"position_only_unique\": " << position_unique << "},\n"
        << "  \"normal\": {\"correct\": " << vector_json(correct_normal)
        << ", \"model_matrix_mutation\": " << vector_json(wrong_normal)
        << ", \"correct_tangent_dot\": " << correct_orthogonality
        << ", \"mutation_tangent_dot\": " << wrong_orthogonality << "},\n"
        << "  \"normal_map\": {\"encoding\": \"data-linear\", \"flat_decoded\": "
        << vector_json(mutation == "mark_normal_map_as_srgb" ? flat_normal_srgb : flat_normal_data) << "}\n}\n";
  write_text(options.output / "asset-validation.json", asset.str());

  const Bounds3d selected_bounds = mutation == "transform_only_aabb_min_and_max" ? two_point_bounds : conservative_bounds;
  const std::vector<int>& selected_lod = mutation == "remove_lod_hysteresis"
      ? lod_without_hysteresis
      : lod_with_hysteresis;
  std::ostringstream culling;
  culling << std::fixed << std::setprecision(6)
          << "{\n  \"schema_version\": 1,\n  \"frustum\": {\"input\": 3, \"visible\": "
          << visible_count << ", \"inside\": 1, \"intersecting\": 1, \"outside\": 1},\n"
          << "  \"world_bounds\": {\"minimum\": " << vector_json(selected_bounds.minimum)
          << ", \"maximum\": " << vector_json(selected_bounds.maximum) << "},\n"
          << "  \"bounds_all_corners_contained\": "
          << (mutation == "transform_only_aabb_min_and_max" ? "false" : "true") << ",\n"
          << "  \"lod\": {\"threshold\": 0.5, \"hysteresis\": "
          << (mutation == "remove_lod_hysteresis" ? 0.0 : 0.05) << ", \"levels\": [";
  for (std::size_t index = 0; index < selected_lod.size(); ++index) {
    culling << selected_lod[index] << (index + 1 == selected_lod.size() ? "" : ", ");
  }
  culling << "], \"transitions\": " << transition_count(selected_lod) << "}\n}\n";
  write_text(options.output / "culling-lod.json", culling.str());

  double minimum_depth = 1.0;
  double maximum_depth = 0.0;
  for (const double value : rendered.depth) {
    if (value < 1.0) {
      minimum_depth = std::min(minimum_depth, value);
      maximum_depth = std::max(maximum_depth, value);
    }
  }
  std::ostringstream depth;
  depth << std::fixed << std::setprecision(6)
        << "{\n  \"schema_version\": 1,\n  \"extent\": [16, 16],\n  \"clear\": 1.0,\n"
        << "  \"covered_samples\": " << rendered.covered_samples << ",\n"
        << "  \"minimum\": " << minimum_depth << ",\n  \"maximum\": " << maximum_depth << "\n}\n";
  write_text(options.output / "depth.json", depth.str());

  const LinearRgb selected_mip = use_wrong_mip ? mip_encoded : mip_linear;
  const Vector3d selected_normal_map = mutation == "mark_normal_map_as_srgb" ? flat_normal_srgb : flat_normal_data;
  std::ostringstream trace;
  trace << std::fixed << std::setprecision(6)
        << "{\n  \"schema_version\": 1,\n  \"pixel\": [8, 8],\n  \"uv\": ["
        << rendered.traced_uv.u << ", " << rendered.traced_uv.v << "],\n"
        << "  \"base_color_linear\": " << color_json(rendered.traced_base) << ",\n"
        << "  \"mip_1x1_linear\": " << color_json(selected_mip) << ",\n"
        << "  \"normal_world\": " << vector_json(render_normal) << ",\n"
        << "  \"normal_map_decoded\": " << vector_json(selected_normal_map) << ",\n"
        << "  \"light_direction\": " << vector_json(normalized({0.2, 0.4, 1.0})) << ",\n"
        << "  \"ndotl\": " << std::max(dot(normalized(render_normal), normalized({0.2, 0.4, 1.0})), 0.0)
        << "\n}\n";
  write_text(options.output / "trace.json", trace.str());

  std::ostringstream statistics;
  statistics << "{\n  \"schema_version\": 1,\n  \"input_vertices\": " << scene.vertices.size()
             << ",\n  \"input_triangles\": 1,\n  \"covered_samples\": " << rendered.covered_samples
             << ",\n  \"depth_passed_samples\": " << rendered.covered_samples
             << ",\n  \"invalid_fixture_count\": 5,\n  \"visible_objects\": " << visible_count
             << ",\n  \"lod_transitions\": " << transition_count(selected_lod) << "\n}\n";
  write_text(options.output / "statistics.json", statistics.str());

  std::ostringstream frame;
  frame << "{\n  \"schema_version\": 1,\n  \"scene\": \"" << SceneSnapshot::id
        << "\",\n  \"extent\": [16, 16],\n  \"sample\": \"pixel-center\",\n"
        << "  \"input_primitives\": 1,\n  \"output_primitives\": 1,\n"
        << "  \"covered_samples\": " << rendered.covered_samples
        << ",\n  \"invalid_non_finite_values\": 0,\n  \"color_encoding\": \"sRGB-output\"\n}\n";
  write_text(options.output / "frame.json", frame.str());

  std::ostringstream mutation_report;
  mutation_report << "{\n  \"schema_version\": 1,\n  \"mutation\": ";
  if (options.mutation) {
    mutation_report << '"' << json_escape(*options.mutation) << '"';
  } else {
    mutation_report << "null";
  }
  mutation_report << ",\n  \"recognized\": " << (known_mutation ? "true" : "false")
                  << ",\n  \"rejected\": "
                  << (options.mutation && !all_invariants_hold(invariants) ? "true" : "false") << "\n}\n";
  write_text(options.output / "mutation-report.json", mutation_report.str());

  write_run_json(options, invariants);
  return all_invariants_hold(invariants) ? exit_ok : exit_contract_failure;
}

}  // namespace

int run_raster_stage(const RunOptions& options) {
  if (options.backend != Backend::software) {
    ensure_output_directory(options.output);
    Invariants invariants{{"software_backend_required", false}};
    write_run_json(options, invariants);
    return exit_unsupported;
  }
  switch (options.stage) {
    case Stage::triangle_coverage: return run_triangle_coverage(options);
    case Stage::perspective_depth_blend: return run_perspective_depth_blend(options);
    case Stage::textured_lit_scene: return run_textured_lit_scene(options);
    default: return exit_not_implemented;
  }
}

}  // namespace cg
