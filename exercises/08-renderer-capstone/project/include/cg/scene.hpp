#pragma once

#include <array>
#include <cstdint>

namespace cg {

struct Vec2 {
  float x{};
  float y{};
};

struct Vec3 {
  float x{};
  float y{};
  float z{};
};

struct Vec4 {
  float x{};
  float y{};
  float z{};
  float w{};
};

struct Vertex {
  Vec3 position;
  Vec4 color_linear;
  Vec2 uv;
  Vec3 normal;
};

struct SceneSnapshot {
  static constexpr std::uint32_t schema_version = 1;
  static constexpr const char* id = "shared-textured-triangle-v1";
  std::array<Vertex, 3> vertices;
  std::array<std::uint16_t, 3> indices;
};

inline constexpr SceneSnapshot shared_triangle_scene() {
  return SceneSnapshot{
      .vertices = {{
          {{-0.7F, -0.6F, 0.5F}, {1.0F, 0.0F, 0.0F, 1.0F}, {0.0F, 1.0F}, {0.0F, 0.0F, -1.0F}},
          {{0.7F, -0.6F, 0.5F}, {0.0F, 1.0F, 0.0F, 1.0F}, {1.0F, 1.0F}, {0.0F, 0.0F, -1.0F}},
          {{0.0F, 0.7F, 0.5F}, {0.0F, 0.0F, 1.0F, 1.0F}, {0.5F, 0.0F}, {0.0F, 0.0F, -1.0F}},
      }},
      .indices = {0, 1, 2},
  };
}

}  // namespace cg
