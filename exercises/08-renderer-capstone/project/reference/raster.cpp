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
#include <stdexcept>
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
  int winding_rejections{};
  bool nonfinite_setup{};

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
    const EdgeTie tie,
    const bool normalize_winding = true,
    const bool truncate_bounds = false,
    const bool guard_degenerate = true) {
  double area = orient2d(triangle.vertices[0], triangle.vertices[1], triangle.vertices[2]);
  if (std::abs(area) <= 1.0e-12) {
    if (guard_degenerate) {
      ++raster.degenerate_triangles;
    } else {
      const double reciprocal_area = 1.0 / area;
      raster.nonfinite_setup = !std::isfinite(reciprocal_area);
    }
    return;
  }
  if (area < 0.0) {
    if (!normalize_winding) {
      ++raster.winding_rejections;
      return;
    }
    std::swap(triangle.vertices[1], triangle.vertices[2]);
    area = -area;
    ++raster.winding_normalizations;
  }

  const auto [minimum_x, maximum_x] = std::minmax(
      {triangle.vertices[0].x, triangle.vertices[1].x, triangle.vertices[2].x});
  const auto [minimum_y, maximum_y] = std::minmax(
      {triangle.vertices[0].y, triangle.vertices[1].y, triangle.vertices[2].y});
  const auto lower_bound = [truncate_bounds](const double value) {
    return truncate_bounds ? static_cast<int>(value - 0.5)
                           : static_cast<int>(std::ceil(value - 0.5));
  };
  const auto upper_bound = [truncate_bounds](const double value) {
    return truncate_bounds ? static_cast<int>(value - 0.5)
                           : static_cast<int>(std::floor(value - 0.5));
  };
  const int first_x = std::max({0, scissor.min_x, lower_bound(minimum_x)});
  const int last_x = std::min(
      {raster.width - 1, scissor.max_x - 1, upper_bound(maximum_x)});
  const int first_y = std::max({0, scissor.min_y, lower_bound(minimum_y)});
  const int last_y = std::min(
      {raster.height - 1, scissor.max_y - 1, upper_bound(maximum_y)});

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

struct CoverageClipVertex {
  double x{};
  double y{};
  double z{};
  double w{};
};

double coverage_plane_distance(const CoverageClipVertex vertex, const std::size_t plane) {
  const std::array<double, 6> distances{
      vertex.x + vertex.w,
      vertex.w - vertex.x,
      vertex.y + vertex.w,
      vertex.w - vertex.y,
      vertex.z,
      vertex.w - vertex.z,
  };
  const double distance = distances.at(plane);
  if (!std::isfinite(distance)) throw std::runtime_error("non-finite coverage clip distance");
  return distance;
}

CoverageClipVertex interpolate_clip(
    const CoverageClipVertex left,
    const CoverageClipVertex right,
    const double amount) {
  if (!std::isfinite(amount) || amount < -1.0e-12 || amount > 1.0 + 1.0e-12) {
    throw std::runtime_error("invalid coverage clip interpolation parameter");
  }
  return {
      left.x + (right.x - left.x) * amount,
      left.y + (right.y - left.y) * amount,
      left.z + (right.z - left.z) * amount,
      left.w + (right.w - left.w) * amount,
  };
}

std::vector<CoverageClipVertex> clip_coverage_polygon(
    std::vector<CoverageClipVertex> polygon) {
  for (std::size_t plane = 0; plane < 6; ++plane) {
    if (polygon.empty()) break;
    std::vector<CoverageClipVertex> output;
    CoverageClipVertex previous = polygon.back();
    double previous_distance = coverage_plane_distance(previous, plane);
    bool previous_inside = previous_distance >= -1.0e-12;
    for (const CoverageClipVertex& current : polygon) {
      const double current_distance = coverage_plane_distance(current, plane);
      const bool current_inside = current_distance >= -1.0e-12;
      if (current_inside != previous_inside) {
        const double denominator = previous_distance - current_distance;
        if (std::abs(denominator) <= 1.0e-12) {
          throw std::runtime_error("unstable coverage clip intersection");
        }
        output.push_back(interpolate_clip(previous, current, previous_distance / denominator));
      }
      if (current_inside) output.push_back(current);
      previous = current;
      previous_distance = current_distance;
      previous_inside = current_inside;
    }
    polygon = std::move(output);
  }
  return polygon;
}

bool inside_coverage_clip(const CoverageClipVertex vertex) {
  return std::isfinite(vertex.x) && std::isfinite(vertex.y) &&
      std::isfinite(vertex.z) && std::isfinite(vertex.w) && vertex.w > 0.0 &&
      vertex.x >= -vertex.w - 1.0e-12 && vertex.x <= vertex.w + 1.0e-12 &&
      vertex.y >= -vertex.w - 1.0e-12 && vertex.y <= vertex.w + 1.0e-12 &&
      vertex.z >= -1.0e-12 && vertex.z <= vertex.w + 1.0e-12;
}

Point2d clip_to_screen(const CoverageClipVertex vertex, const int extent) {
  if (!(std::abs(vertex.w) > 1.0e-12) || !std::isfinite(vertex.w)) {
    throw std::runtime_error("coverage perspective divide requires finite non-zero w");
  }
  return {
      (vertex.x / vertex.w + 1.0) * 0.5 * static_cast<double>(extent),
      (1.0 - vertex.y / vertex.w) * 0.5 * static_cast<double>(extent),
  };
}

void rasterize_clipped_polygon(
    RasterMap& raster,
    const std::vector<CoverageClipVertex>& polygon,
    const Scissor scissor) {
  if (polygon.size() < 3) return;
  for (std::size_t index = 1; index + 1 < polygon.size(); ++index) {
    rasterize_triangle(
        raster,
        Triangle2d{{
            clip_to_screen(polygon[0], raster.width),
            clip_to_screen(polygon[index], raster.width),
            clip_to_screen(polygon[index + 1], raster.width)}},
        static_cast<int>(20 + index),
        scissor,
        EdgeTie::top_left);
  }
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

  const bool truncate_bounds = mutation == "truncate_negative_bounding_box";
  const bool keep_old_winding = mutation == "keep_old_front_face_after_y_flip";
  const bool divide_degenerate = mutation == "divide_by_zero_for_degenerate_area";
  const bool skip_clipping = mutation == "skip_clipping";

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
  rasterize_triangle(
      reversed,
      reversed_triangle,
      1,
      full,
      EdgeTie::top_left,
      !keep_old_winding);

  RasterMap degenerate(8, 8);
  rasterize_triangle(
      degenerate,
      Triangle2d{{Point2d{1.0, 1.0}, Point2d{3.0, 3.0}, Point2d{5.0, 5.0}}},
      9,
      full,
      EdgeTie::top_left,
      true,
      false,
      !divide_degenerate);

  RasterMap offscreen_boundary(8, 8);
  rasterize_triangle(
      offscreen_boundary,
      Triangle2d{{Point2d{-0.9, 1.0}, Point2d{0.2, 2.0}, Point2d{-0.4, 3.0}}},
      11,
      full,
      EdgeTie::top_left,
      true,
      truncate_bounds);

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

  const std::vector<CoverageClipVertex> unclipped_polygon{
      {-0.6, -0.2, -0.4, 1.0},
      {0.8, -0.4, 0.6, 1.0},
      {0.0, 0.8, 0.6, 1.0},
  };
  const std::vector<CoverageClipVertex> computed_polygon =
      clip_coverage_polygon(unclipped_polygon);
  const std::vector<CoverageClipVertex>& selected_polygon =
      skip_clipping ? unclipped_polygon : computed_polygon;
  RasterMap clipped_path(8, 8);
  rasterize_clipped_polygon(clipped_path, selected_polygon, full);
  const bool selected_polygon_inside = !selected_polygon.empty() && std::all_of(
      selected_polygon.begin(), selected_polygon.end(), inside_coverage_clip);
  const int clipped_covered = static_cast<int>(std::count_if(
      clipped_path.owner.begin(), clipped_path.owner.end(), [](const int owner) { return owner != 0; }));

  const int gaps = count_rectangle_gaps(rectangle);
  const bool offscreen_bounds_correct =
      offscreen_boundary.tested_samples == 0 && count_owner(offscreen_boundary, 11) == 0;
  const bool degenerate_safe = count_owner(degenerate, 9) == 0 &&
      degenerate.degenerate_triangles == 1 && !degenerate.nonfinite_setup;
  const bool winding_preserved = owners_equal(forward, reversed) && reversed.winding_rejections == 0;
  Invariants invariants{
      {"shared_edge_has_no_gap", gaps == 0},
      {"shared_edge_has_no_overlap", rectangle.overlap_writes == 0 && count_owner(rectangle, -1) == 0},
      {"degenerate_triangle_writes_no_samples", degenerate_safe},
      {"bounding_box_never_writes_outside_framebuffer",
       scissor_respected && offscreen_bounds_correct && selected_polygon_inside && clipped_covered > 0},
      {"scissor_is_respected", scissor_respected},
      {"winding_normalization_preserves_coverage_set", winding_preserved},
  };
  if (!known_mutation) {
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
         << "  \"degenerate_writes\": " << count_owner(degenerate, 9) << ",\n"
         << "  \"offscreen_boundary\": {\"tested_samples\": "
         << offscreen_boundary.tested_samples << ", \"written_samples\": "
         << count_owner(offscreen_boundary, 11) << ", \"expected_tested_samples\": 0},\n"
         << "  \"reversed_coverage\": {\"forward_samples\": " << count_owner(forward, 1)
         << ", \"reversed_samples\": " << count_owner(reversed, 1)
         << ", \"winding_rejections\": " << reversed.winding_rejections << "},\n"
         << "  \"degenerate_setup\": {\"guarded\": "
         << (divide_degenerate ? "false" : "true") << ", \"nonfinite_detected\": "
         << (degenerate.nonfinite_setup ? "true" : "false") << "},\n"
         << "  \"clipped_primitive\": {\"input_vertex_count\": " << unclipped_polygon.size()
         << ", \"computed_output_vertex_count\": " << computed_polygon.size()
         << ", \"selected_output_vertex_count\": " << selected_polygon.size()
         << ", \"child_triangle_count\": "
         << (selected_polygon.size() >= 3 ? selected_polygon.size() - 2 : 0)
         << ", \"covered_samples\": " << clipped_covered
         << ", \"selected_policy\": \"" << (skip_clipping ? "unclipped" : "six-plane")
         << "\", \"all_inside\": " << (selected_polygon_inside ? "true" : "false") << "}\n}\n";
  write_text(options.output / "coverage-counts.json", counts.str());

  std::string first_difference = "none";
  if (mutation == "truncate_negative_bounding_box") {
    first_difference = "coverage-counts.offscreen_boundary.tested_samples";
  } else if (mutation == "keep_old_front_face_after_y_flip") {
    first_difference = "coverage-counts.reversed_coverage.reversed_samples";
  } else if (mutation == "divide_by_zero_for_degenerate_area") {
    first_difference = "coverage-counts.degenerate_setup.nonfinite_detected";
  } else if (mutation == "skip_clipping") {
    first_difference = "coverage-counts.clipped_primitive.selected_output_vertex_count";
  } else if (mutation == "make_every_edge_inclusive" || mutation == "break_top_left_rule") {
    first_difference = "coverage-counts.overlap_samples";
  } else if (mutation == "make_every_edge_exclusive") {
    first_difference = "coverage-counts.gap_samples";
  } else if (!known_mutation) {
    first_difference = "mutation-report.recognized";
  }
  std::ostringstream setup_trace;
  setup_trace
      << "{\n  \"schema_version\": 1,\n  \"sample\": \"pixel-center\",\n"
      << "  \"quantization\": \""
      << (truncate_bounds ? "truncate(min-0.5)..truncate(max-0.5)"
                          : "ceil(min-0.5)..floor(max-0.5)") << "\",\n"
      << "  \"front_area_sign\": \"positive-after-normalization\",\n"
      << "  \"edge_0\": {\"a\": 0.0, \"b\": 6.0, \"c\": -6.0, \"top_left\": true},\n"
      << "  \"shared_edge\": {\"owner\": 1, \"rule\": \"top-left\"},\n"
      << "  \"clipped_primitive\": {\"selected_policy\": \""
      << (skip_clipping ? "unclipped" : "six-plane") << "\", \"computed_output_vertex_count\": "
      << computed_polygon.size() << ", \"selected_output_vertex_count\": "
      << selected_polygon.size() << "},\n"
      << "  \"first_difference\": \"" << json_escape(first_difference) << "\"\n}\n";
  write_text(options.output / "setup-trace.json", setup_trace.str());

  std::ostringstream mutation_report;
  mutation_report << "{\n  \"schema_version\": 1,\n  \"mutation\": ";
  if (options.mutation) {
    mutation_report << '"' << json_escape(*options.mutation) << '"';
  } else {
    mutation_report << "null";
  }
  mutation_report << ",\n  \"recognized\": " << (known_mutation ? "true" : "false")
                  << ",\n  \"first_difference\": \"" << json_escape(first_difference) << "\""
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
  LinearRgb color{1.0, 1.0, 1.0};
  std::array<double, 3> normal{0.0, 0.0, -1.0};
};

struct InterpolatedSample {
  std::array<double, 3> lambda{};
  double denominator{};
  Uv uv;
  double depth{};
  LinearRgb color;
  std::array<double, 3> normal{};
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
  if (!std::isfinite(area) || std::abs(area) <= 1.0e-12) {
    throw std::runtime_error("attribute interpolation requires finite non-zero triangle area");
  }
  const std::array<double, 3> lambda{
      orient2d(vertices[1].position, vertices[2].position, point) / area,
      orient2d(vertices[2].position, vertices[0].position, point) / area,
      orient2d(vertices[0].position, vertices[1].position, point) / area,
  };
  const double denominator = perspective_correct
      ? lambda[0] * vertices[0].inverse_w + lambda[1] * vertices[1].inverse_w +
            lambda[2] * vertices[2].inverse_w
      : 1.0;
  if (!std::isfinite(denominator) || std::abs(denominator) <= 1.0e-12) {
    throw std::runtime_error("perspective interpolation requires finite non-zero reciprocal-w sum");
  }
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
      .depth = lambda[0] * vertices[0].depth + lambda[1] * vertices[1].depth +
          lambda[2] * vertices[2].depth,
      .color = {
          interpolate(vertices[0].color.red, vertices[1].color.red, vertices[2].color.red),
          interpolate(vertices[0].color.green, vertices[1].color.green, vertices[2].color.green),
          interpolate(vertices[0].color.blue, vertices[1].color.blue, vertices[2].color.blue)},
      .normal = {
          interpolate(vertices[0].normal[0], vertices[1].normal[0], vertices[2].normal[0]),
          interpolate(vertices[0].normal[1], vertices[1].normal[1], vertices[2].normal[1]),
          interpolate(vertices[0].normal[2], vertices[1].normal[2], vertices[2].normal[2])},
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

  QuadRender perspective = render_perspective_quad(true);
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
  const InterpolatedSample selected_sample = use_affine ? affine_sample : first_sample;
  const bool diagonal_continuous = nearly_equal(first_sample.uv.u, second_sample.uv.u) &&
      nearly_equal(first_sample.uv.v, second_sample.uv.v) && changed_pixels > 0 &&
      nearly_equal(selected_sample.uv.u, first_sample.uv.u) &&
      nearly_equal(selected_sample.uv.v, first_sample.uv.v);

  bool reciprocal_w_zero_rejected = false;
  try {
    const std::array<AttributeVertex, 3> zero_denominator{{
        {{0.0, 0.0}, {0.0, 0.0}, 1.0, 0.2},
        {{2.0, 0.0}, {1.0, 0.0}, -1.0, 0.4},
        {{0.0, 2.0}, {0.0, 1.0}, -1.0, 0.6},
    }};
    static_cast<void>(interpolate_attribute(zero_denominator, {0.5, 0.5}, true));
  } catch (const std::runtime_error&) {
    reciprocal_w_zero_rejected = true;
  }

  const bool reverse_depth = mutation == "reverse_depth_compare_without_projection_change" ||
      mutation == "reverse_depth_convention";
  const auto draw_opaque = [reverse_depth](const std::array<double, 2> order) {
    double stored = 1.0;
    int owner = 0;
    for (const double depth : order) {
      const bool passes = reverse_depth ? depth > stored : depth < stored;
      if (passes) {
        stored = depth;
        owner = nearly_equal(depth, 0.25) ? 1 : 2;
      }
    }
    return std::pair{stored, owner};
  };
  const auto order_a = draw_opaque({0.75, 0.25});
  const auto order_b = draw_opaque({0.25, 0.75});
  const bool opaque_order_invariant = order_a == order_b && order_a.second == 1;
  if (mutation == "store_view_space_z_as_depth") {
    for (double& value : perspective.depth) {
      if (value < 1.0) value += 2.0;
    }
  }
  const QuadRender& selected_quad = use_affine ? affine : perspective;
  const bool depth_valid = std::all_of(selected_quad.depth.begin(), selected_quad.depth.end(), [](const double value) {
    return std::isfinite(value) && value >= 0.0 && value <= 1.0;
  }) && std::isfinite(first_sample.depth) && first_sample.depth >= 0.0 &&
      first_sample.depth <= 1.0 && reciprocal_w_zero_rejected;
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
  const bool depth_write_transparent = mutation == "enable_depth_write_for_blended_surface";
  const bool encoded_blend = mutation == "blend_srgb_encoded_values";
  const bool mismatched_alpha = mutation == "mismatch_alpha_representation_and_factors" ||
      mutation == "mismatch_alpha_blend";
  struct TransparentProbe {
    LinearRgb color;
    double depth{1.0};
    int accepted_layers{};
  };
  const auto composite = [encoded_blend, mismatched_alpha](
                             const LinearRgb source,
                             const double alpha,
                             const LinearRgb destination) {
    if (encoded_blend) {
      return LinearRgb{
          srgb_to_linear(linear_to_srgb(source.red) * alpha +
                         linear_to_srgb(destination.red) * (1.0 - alpha)),
          srgb_to_linear(linear_to_srgb(source.green) * alpha +
                         linear_to_srgb(destination.green) * (1.0 - alpha)),
          srgb_to_linear(linear_to_srgb(source.blue) * alpha +
                         linear_to_srgb(destination.blue) * (1.0 - alpha)),
      };
    }
    if (mismatched_alpha) return blend_premultiplied(source, alpha, destination);
    return blend_straight(source, alpha, destination);
  };
  const auto draw_transparent = [&](const std::array<std::pair<LinearRgb, double>, 2>& layers) {
    TransparentProbe result{.color = blue};
    for (const auto& [color, incoming_depth] : layers) {
      if (incoming_depth >= result.depth) continue;
      result.color = composite(color, 0.5, result.color);
      ++result.accepted_layers;
      if (depth_write_transparent) result.depth = incoming_depth;
    }
    return result;
  };
  const TransparentProbe transparent_a = draw_transparent({{{red, 0.25}, {green, 0.75}}});
  const TransparentProbe transparent_b = draw_transparent({{{green, 0.75}, {red, 0.25}}});
  const bool blends_in_linear = !encoded_blend && color_distance(straight, wrong_encoded) > 0.1;
  const bool alpha_states_match = !mismatched_alpha && !depth_write_transparent &&
      color_distance(straight, premultiplied) <= 1.0e-12 &&
      transparent_a.accepted_layers == 2 && transparent_b.accepted_layers == 2;

  Invariants invariants{
      {"perspective_uv_is_continuous_across_quad_diagonal", diagonal_continuous},
      {"opaque_visibility_is_draw_order_invariant", opaque_order_invariant},
      {"depth_is_finite_and_in_zero_one", depth_valid},
      {"flat_ids_are_not_interpolated", flat_ids},
      {"blend_occurs_in_linear_color", blends_in_linear},
      {"alpha_representation_matches_state", alpha_states_match},
  };
  if (!known_mutation) {
    set_invariant(invariants, "flat_ids_are_not_interpolated", false);
  }

  write_ppm_p3(
      options.output / "perspective-correct.ppm", 8, 8, selected_quad.color);
  write_ppm_p3(options.output / "affine-mutation.ppm", 8, 8, affine.color);
  write_ppm_p3(options.output / "primitive-id.ppm", 8, 8, perspective.primitive_id);
  write_ppm_p3(
      options.output / "transparent-order-a.ppm", 4, 4, solid_image(4, 4, transparent_a.color));
  write_ppm_p3(
      options.output / "transparent-order-b.ppm", 4, 4, solid_image(4, 4, transparent_b.color));
  write_ppm_p3(options.output / "blend-probe.ppm", 1, 1, solid_image(1, 1, transparent_a.color));

  std::ostringstream depth;
  depth << "{\n  \"schema_version\": 1,\n  \"clear\": 1.0,\n  \"compare\": \""
        << (reverse_depth ? "greater" : "less") << "\",\n"
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
        << "  \"vertex_inverse_w\": [" << vertices[0].inverse_w << ", "
        << vertices[1].inverse_w << ", " << vertices[2].inverse_w << "],\n"
        << "  \"denominator_finite_nonzero\": "
        << (std::isfinite(first_sample.denominator) && std::abs(first_sample.denominator) > 1.0e-12
                ? "true" : "false") << ",\n"
        << "  \"reciprocal_w_zero_rejected\": "
        << (reciprocal_w_zero_rejected ? "true" : "false") << ",\n"
        << "  \"depth_interpolation\": \"screen-affine-ndc\",\n"
        << "  \"affine_ndc_depth\": " << first_sample.depth << ",\n"
        << "  \"perspective_uv\": [" << first_sample.uv.u << ", " << first_sample.uv.v << "],\n"
        << "  \"affine_uv\": [" << affine_sample.uv.u << ", " << affine_sample.uv.v << "],\n"
        << "  \"selected_uv\": [" << selected_sample.uv.u << ", " << selected_sample.uv.v << "],\n"
        << "  \"incoming_depth\": " << first_sample.depth << ",\n"
        << "  \"depth_test\": true\n}\n";
  write_text(options.output / "pixel-traces" / "sample-3-3.json", trace.str());

  std::string first_difference = "none";
  if (use_affine) {
    first_difference = "pixel-traces/sample-3-3.json.selected_uv";
  } else if (mutation == "store_view_space_z_as_depth") {
    first_difference = "depth.json.order_a.depth";
  } else if (reverse_depth) {
    first_difference = "depth.json.order_a.owner";
  } else if (depth_write_transparent) {
    first_difference = "report.json.transparent_order_a_accepted_layers";
  } else if (encoded_blend) {
    first_difference = "report.json.selected_blend_linear";
  } else if (mismatched_alpha) {
    first_difference = "report.json.selected_alpha_representation";
  } else if (!known_mutation) {
    first_difference = "run.json.invariants.flat_ids_are_not_interpolated";
  }
  std::ostringstream report;
  report << std::fixed << std::setprecision(6)
         << "{\n  \"schema_version\": 1,\n  \"perspective_vs_affine_changed_pixels\": "
         << changed_pixels << ",\n"
         << "  \"diagonal_uv_delta\": [" << std::abs(first_sample.uv.u - second_sample.uv.u) << ", "
         << std::abs(first_sample.uv.v - second_sample.uv.v) << "],\n"
         << "  \"opaque_order_invariant\": " << (opaque_order_invariant ? "true" : "false") << ",\n"
         << "  \"selected_depth_compare\": \"" << (reverse_depth ? "greater" : "less") << "\",\n"
         << "  \"transparent_depth_write\": " << (depth_write_transparent ? "true" : "false") << ",\n"
         << "  \"transparent_order_a_accepted_layers\": " << transparent_a.accepted_layers << ",\n"
         << "  \"straight_premultiplied_max_delta\": " << color_distance(straight, premultiplied) << ",\n"
         << "  \"linear_vs_encoded_blend_delta\": " << color_distance(straight, wrong_encoded) << ",\n"
         << "  \"selected_blend_linear\": " << (encoded_blend ? "false" : "true") << ",\n"
         << "  \"selected_alpha_representation\": \""
         << (mismatched_alpha ? "straight-data-with-premultiplied-factors" : "straight") << "\",\n"
         << "  \"first_difference\": \"" << json_escape(first_difference) << "\"\n}\n";
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
  LinearRgb traced_vertex_color{};
  Vector3d traced_local_normal{};
  Vector3d traced_world_normal{};
  double traced_ndotl{};
};

LitRenderArtifacts render_lit_triangle(
    const SceneSnapshot& scene,
    const std::array<LinearRgb, 4>& texture,
    const Matrix3d& normal_transform,
    const Vector3d normal_map_sample,
    const bool use_wrong_mip,
    const bool object_visible,
    const int lod_level) {
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

  if (!object_visible) return output;

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
        .color = {
            static_cast<double>(source.color_linear.x),
            static_cast<double>(source.color_linear.y),
            static_cast<double>(source.color_linear.z)},
        .normal = {
            static_cast<double>(source.normal.x),
            static_cast<double>(source.normal.y),
            static_cast<double>(source.normal.z)},
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
  const Vector3d light = normalized({-0.35, 0.25, -1.0});
  const LinearRgb wrong_mip = encoded_mip_average(texture);
  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) {
      if (lod_level > 0 && (x + y) % 2 != 0) continue;
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
      const LinearRgb sampled_texture =
          use_wrong_mip ? wrong_mip : sample_bilinear_repeat(texture, sample.uv);
      const LinearRgb base{
          sampled_texture.red * sample.color.red,
          sampled_texture.green * sample.color.green,
          sampled_texture.blue * sample.color.blue,
      };
      const Vector3d snapshot_normal = normalized(
          {sample.normal[0], sample.normal[1], sample.normal[2]});
      const Vector3d perturbed_normal = normalized(
          snapshot_normal + normal_map_sample * 0.25);
      const Vector3d world_normal = normalized(multiply(normal_transform, perturbed_normal));
      const double ndotl_value = std::max(dot(world_normal, light), 0.0);
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
        output.traced_vertex_color = sample.color;
        output.traced_local_normal = snapshot_normal;
        output.traced_world_normal = world_normal;
        output.traced_ndotl = ndotl_value;
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
      {{0.0, 0.0, 0.0}, {0.75, 0.25}},
  };
  const std::size_t position_unique = position_only_unique_count(seam_vertices);
  const std::size_t semantic_unique = semantic_unique_count(seam_vertices);
  const bool seam_identity_preserved = semantic_unique == 4 && position_unique == 3;

  const bool valid_hierarchy = hierarchy_is_acyclic({-1, 0, 1});
  const bool cycle_rejected = !hierarchy_is_acyclic({1, 0});

  constexpr double cosine = 0.7071067811865476;
  const Matrix3d nonuniform_rotated{
      .value = {{{2.0 * cosine, -0.35, 0.40},
                 {2.0 * cosine, 0.90, 0.15},
                 {0.20, 0.30, 0.50}}},
  };
  const Matrix3d singular{
      .value = {{{1.0, 0.0, 0.0},
                 {0.0, 0.0, 0.0},
                 {0.0, 0.0, 1.0}}},
  };
  const auto inverse_model = inverse(nonuniform_rotated);
  const auto singular_inverse = inverse(singular);
  if (!inverse_model) throw std::runtime_error("reference model transform must be invertible");
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

  const std::size_t selected_unique = mutation == "deduplicate_by_position_only"
      ? position_unique
      : semantic_unique;
  const Uv selected_duplicate_uv = mutation == "deduplicate_by_position_only"
      ? seam_vertices.front().second
      : seam_vertices.back().second;
  const LinearRgb seam_first_color = sample_bilinear_repeat(texture, seam_vertices.front().second);
  const LinearRgb seam_duplicate_color = sample_bilinear_repeat(texture, selected_duplicate_uv);
  const double seam_probe_delta = color_distance(seam_first_color, seam_duplicate_color);
  const bool selected_seam_valid = selected_unique == semantic_unique && seam_probe_delta > 0.1;

  const bool selected_cycle_accepted = mutation == "accept_scene_cycle"
      ? true
      : hierarchy_is_acyclic({1, 0});
  const Matrix3d correct_normal_transform = transpose(*inverse_model);
  const Matrix3d& selected_normal_transform = mutation == "transform_normal_with_model_matrix"
      ? nonuniform_rotated
      : correct_normal_transform;
  const Vector3d selected_probe_normal = mutation == "transform_normal_with_model_matrix"
      ? wrong_normal
      : correct_normal;
  const double selected_orthogonality = std::abs(dot(selected_probe_normal, transformed_tangent));
  const Vector3d selected_normal_map = mutation == "mark_normal_map_as_srgb"
      ? flat_normal_srgb
      : flat_normal_data;
  const bool selected_normal_map_is_data =
      length(selected_normal_map - flat_normal_data) <= 1.0e-12 && normal_map_data;
  const bool use_wrong_mip = mutation == "average_encoded_color_for_mips" ||
      mutation == "skip_srgb_decode";
  const LinearRgb selected_mip_for_render = use_wrong_mip ? mip_encoded : mip_linear;
  const bool selected_mip_is_linear =
      color_distance(selected_mip_for_render, mip_linear) <= 1.0e-12 && linear_lighting;

  const Bounds3d selected_bounds = mutation == "transform_only_aabb_min_and_max"
      ? two_point_bounds
      : conservative_bounds;
  bool selected_bounds_contain_all = true;
  for (const Vector3d corner : bounds_corners(local_bounds)) {
    selected_bounds_contain_all = selected_bounds_contain_all &&
        contains(selected_bounds, transform_point(nonuniform_rotated, translation, corner));
  }
  const std::vector<int>& selected_lod = mutation == "remove_lod_hysteresis"
      ? lod_without_hysteresis
      : lod_with_hysteresis;
  const bool selected_lod_stable = stable_lod && transition_count(selected_lod) == 2;
  const int render_lod = selected_lod.at(2);
  const bool render_visible = visible_count > 0 && visibility.front() != FrustumRelation::outside;
  const LitRenderArtifacts rendered = render_lit_triangle(
      scene,
      texture,
      selected_normal_transform,
      selected_normal_map,
      use_wrong_mip,
      render_visible,
      render_lod);
  const bool selected_lighting_computed = rendered.covered_samples > 0 &&
      rendered.traced_ndotl > 0.0 && std::isfinite(rendered.traced_ndotl) &&
      length(rendered.traced_local_normal) > 0.99 &&
      length(rendered.traced_world_normal) > 0.99;

  Invariants invariants{
      {"indices_and_attribute_counts_are_valid",
       valid_mesh && invalid_index_rejected && mismatch_rejected && valid_area > 0.0 && degenerate_rejected &&
           seam_identity_preserved && selected_seam_valid},
      {"scene_hierarchy_is_acyclic",
       valid_hierarchy && cycle_rejected && !selected_cycle_accepted},
      {"world_bounds_conservatively_contain_geometry",
       conservative_contains_all && two_point_misses_corner && selected_bounds_contain_all},
      {"normals_are_valid_after_nonuniform_scale",
       normal_valid && selected_orthogonality <= 1.0e-9},
      {"normal_maps_are_data_textures", selected_normal_map_is_data},
      {"lighting_uses_linear_rgb",
       selected_mip_is_linear && selected_lighting_computed},
      {"lod_hysteresis_prevents_boundary_oscillation", selected_lod_stable},
  };
  if (!known_mutation) {
    set_invariant(invariants, "indices_and_attribute_counts_are_valid", false);
  }

  write_ppm_p3(options.output / "final.ppm", 16, 16, rendered.final_color);
  write_ppm_p3(options.output / "base-color.ppm", 16, 16, rendered.base_color);
  write_ppm_p3(options.output / "normal-world.ppm", 16, 16, rendered.normal_world);
  write_ppm_p3(options.output / "ndotl.ppm", 16, 16, rendered.ndotl);
  write_ppm_p3(options.output / "mip-level.ppm", 16, 16, rendered.mip_level);
  write_ppm_p3(options.output / "object-id.ppm", 16, 16, rendered.object_id);
  write_ppm_p3(options.output / "primitive-id.ppm", 16, 16, rendered.primitive_id);
  std::vector<unsigned char> seam_probe(6, 0);
  set_rgb(seam_probe, 2, 0, 0, seam_first_color);
  set_rgb(seam_probe, 2, 1, 0, seam_duplicate_color);
  write_ppm_p3(options.output / "seam-probe.ppm", 2, 1, seam_probe);

  std::ostringstream asset;
  asset << std::fixed << std::setprecision(6)
        << "{\n  \"schema_version\": 1,\n  \"scene_schema_version\": " << SceneSnapshot::schema_version
        << ",\n  \"scene_id\": \"" << SceneSnapshot::id << "\",\n  \"cases\": {\n"
        << "    \"valid_mesh\": {\"accepted\": " << (valid_mesh ? "true" : "false") << "},\n"
        << "    \"invalid_index\": {\"accepted\": false, \"reason\": \"index_out_of_range\"},\n"
        << "    \"attribute_count_mismatch\": {\"accepted\": false, \"reason\": \"attribute_count_mismatch\"},\n"
        << "    \"cycle_hierarchy\": {\"accepted\": "
        << (selected_cycle_accepted ? "true" : "false") << ", \"reason\": \"cycle\"},\n"
        << "    \"singular_normal_matrix\": {\"accepted\": false, \"reason\": \"singular_inverse\"},\n"
        << "    \"degenerate_triangle\": {\"accepted\": false, \"reason\": \"zero_area\"},\n"
        << "    \"uv_negative_repeat\": {\"input\": [-0.25, -0.25], \"wrapped\": [0.75, 0.75], \"sample\": "
        << color_json(negative_uv_sample) << "},\n"
        << "    \"uv_out_of_range_repeat\": {\"input\": [1.25, 1.25], \"wrapped\": [0.25, 0.25], \"sample\": "
        << color_json(out_of_range_uv_sample) << "}\n  },\n"
        << "  \"seam_vertices\": {\"semantic_unique\": " << semantic_unique
        << ", \"position_only_unique\": " << position_unique
        << ", \"selected_unique\": " << selected_unique
        << ", \"selected_policy\": \""
        << (mutation == "deduplicate_by_position_only" ? "position-only" : "position+uv")
        << "\", \"selected_duplicate_uv\": [" << selected_duplicate_uv.u << ", "
        << selected_duplicate_uv.v << "], \"probe_color_delta\": " << seam_probe_delta << "},\n"
        << "  \"normal\": {\"correct\": " << vector_json(correct_normal)
        << ", \"model_matrix_mutation\": " << vector_json(wrong_normal)
        << ", \"snapshot_input\": [0.000000, 0.000000, -1.000000]"
        << ", \"selected_transform\": \""
        << (mutation == "transform_normal_with_model_matrix" ? "model-3x3" : "inverse-transpose")
        << "\", \"selected_world\": " << vector_json(rendered.traced_world_normal)
        << ", \"correct_tangent_dot\": " << correct_orthogonality
        << ", \"mutation_tangent_dot\": " << wrong_orthogonality << "},\n"
        << "  \"normal_map\": {\"encoding\": \"data-linear\", \"flat_decoded\": "
        << vector_json(selected_normal_map) << "}\n}\n";
  write_text(options.output / "asset-validation.json", asset.str());

  int selected_vertex_work = 0;
  int selected_sample_budget = 0;
  for (const int level : selected_lod) {
    selected_vertex_work += level == 0 ? 3 : 2;
    selected_sample_budget += level == 0 ? 256 : 128;
  }
  std::ostringstream culling;
  culling << std::fixed << std::setprecision(6)
          << "{\n  \"schema_version\": 1,\n  \"frustum\": {\"input\": 3, \"visible\": "
          << visible_count << ", \"inside\": 1, \"intersecting\": 1, \"outside\": 1},\n"
          << "  \"world_bounds\": {\"minimum\": " << vector_json(selected_bounds.minimum)
          << ", \"maximum\": " << vector_json(selected_bounds.maximum) << "},\n"
          << "  \"bounds_all_corners_contained\": "
          << (selected_bounds_contain_all ? "true" : "false") << ",\n"
          << "  \"render_decisions\": ["
          << "{\"object\": 0, \"relation\": \"inside\", \"drawn\": true}, "
          << "{\"object\": 1, \"relation\": \"outside\", \"drawn\": false}, "
          << "{\"object\": 2, \"relation\": \"intersecting\", \"drawn\": true}],\n"
          << "  \"lod\": {\"threshold\": 0.5, \"hysteresis\": "
          << (mutation == "remove_lod_hysteresis" ? 0.0 : 0.05) << ", \"levels\": [";
  for (std::size_t index = 0; index < selected_lod.size(); ++index) {
    culling << selected_lod[index] << (index + 1 == selected_lod.size() ? "" : ", ");
  }
  culling << "], \"transitions\": " << transition_count(selected_lod)
          << ", \"selected_render_level\": " << render_lod
          << ", \"vertex_work\": " << selected_vertex_work
          << ", \"sample_budget\": " << selected_sample_budget << "},\n"
          << "  \"render_probe\": {\"visible\": " << (render_visible ? "true" : "false")
          << ", \"output_primitives\": " << (render_visible ? 1 : 0)
          << ", \"covered_samples\": " << rendered.covered_samples << "}\n}\n";
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

  std::ostringstream trace;
  trace << std::fixed << std::setprecision(6)
        << "{\n  \"schema_version\": 1,\n  \"pixel\": [8, 8],\n  \"uv\": ["
        << rendered.traced_uv.u << ", " << rendered.traced_uv.v << "],\n"
        << "  \"base_color_linear\": " << color_json(rendered.traced_base) << ",\n"
        << "  \"interpolated_vertex_color\": "
        << color_json(rendered.traced_vertex_color) << ",\n"
        << "  \"mip_1x1_linear\": " << color_json(selected_mip_for_render) << ",\n"
        << "  \"snapshot_normal_interpolated\": "
        << vector_json(rendered.traced_local_normal) << ",\n"
        << "  \"normal_transform\": \""
        << (mutation == "transform_normal_with_model_matrix" ? "model-3x3" : "inverse-transpose")
        << "\",\n"
        << "  \"normal_world\": " << vector_json(rendered.traced_world_normal) << ",\n"
        << "  \"normal_map_decoded\": " << vector_json(selected_normal_map) << ",\n"
        << "  \"light_direction_to_light\": "
        << vector_json(normalized({-0.35, 0.25, -1.0})) << ",\n"
        << "  \"ndotl\": " << rendered.traced_ndotl
        << "\n}\n";
  write_text(options.output / "trace.json", trace.str());

  std::ostringstream statistics;
  statistics << "{\n  \"schema_version\": 1,\n  \"input_vertices\": " << scene.vertices.size()
             << ",\n  \"input_triangles\": 1,\n  \"covered_samples\": " << rendered.covered_samples
             << ",\n  \"depth_passed_samples\": " << rendered.covered_samples
             << ",\n  \"invalid_fixture_count\": 5,\n  \"visible_objects\": " << visible_count
             << ",\n  \"culled_objects\": " << (3 - visible_count)
             << ",\n  \"selected_render_lod\": " << render_lod
             << ",\n  \"selected_vertex_work\": " << selected_vertex_work
             << ",\n  \"selected_sample_budget\": " << selected_sample_budget
             << ",\n  \"lod_transitions\": " << transition_count(selected_lod) << "\n}\n";
  write_text(options.output / "statistics.json", statistics.str());

  std::ostringstream frame;
  frame << "{\n  \"schema_version\": 1,\n  \"scene\": \"" << SceneSnapshot::id
        << "\",\n  \"extent\": [16, 16],\n  \"sample\": \"pixel-center\",\n"
        << "  \"input_primitives\": 1,\n  \"output_primitives\": "
        << (render_visible ? 1 : 0) << ",\n  \"selected_lod\": " << render_lod << ",\n"
        << "  \"covered_samples\": " << rendered.covered_samples
        << ",\n  \"invalid_non_finite_values\": 0,\n  \"color_encoding\": \"sRGB-output\"\n}\n";
  write_text(options.output / "frame.json", frame.str());

  std::string first_difference = "none";
  if (mutation == "deduplicate_by_position_only") {
    first_difference = "asset-validation.json.seam_vertices.selected_unique";
  } else if (mutation == "transform_normal_with_model_matrix") {
    first_difference = "trace.json.normal_world";
  } else if (mutation == "mark_normal_map_as_srgb") {
    first_difference = "trace.json.normal_map_decoded";
  } else if (mutation == "average_encoded_color_for_mips" || mutation == "skip_srgb_decode") {
    first_difference = "trace.json.mip_1x1_linear";
  } else if (mutation == "transform_only_aabb_min_and_max") {
    first_difference = "culling-lod.json.bounds_all_corners_contained";
  } else if (mutation == "accept_scene_cycle") {
    first_difference = "asset-validation.json.cases.cycle_hierarchy.accepted";
  } else if (mutation == "remove_lod_hysteresis") {
    first_difference = "culling-lod.json.lod.levels[2]";
  } else if (!known_mutation) {
    first_difference = "mutation-report.json.recognized";
  }
  std::ostringstream mutation_report;
  mutation_report << "{\n  \"schema_version\": 1,\n  \"mutation\": ";
  if (options.mutation) {
    mutation_report << '"' << json_escape(*options.mutation) << '"';
  } else {
    mutation_report << "null";
  }
  mutation_report << ",\n  \"recognized\": " << (known_mutation ? "true" : "false")
                  << ",\n  \"first_difference\": \"" << json_escape(first_difference) << "\""
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
