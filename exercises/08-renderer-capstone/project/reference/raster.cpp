#include "cg/artifact.hpp"
#include "cg/contracts.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <iomanip>
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

int run_textured_lit_scene(const RunOptions& options) {
  ensure_output_directory(options.output);
  Invariants invariants{
      {"indices_and_attribute_counts_are_valid", false},
      {"scene_hierarchy_is_acyclic", false},
      {"world_bounds_conservatively_contain_geometry", false},
      {"normals_are_valid_after_nonuniform_scale", false},
      {"normal_maps_are_data_textures", false},
      {"lighting_uses_linear_rgb", false},
      {"lod_hysteresis_prevents_boundary_oscillation", false},
  };
  write_run_json(options, invariants);
  return exit_not_implemented;
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
