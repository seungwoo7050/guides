#pragma once

#include <filesystem>
#include <span>
#include <string_view>
#include <vector>

namespace cg {

// Public runs must start from a path that does not exist and whose existing
// ancestors are real directories. This keeps a typo or symlink from redirecting
// deterministic artifacts into source, learner work, or an unrelated tree.
void validate_new_output_path(const std::filesystem::path& directory);
void ensure_output_directory(const std::filesystem::path& directory);
void write_text(const std::filesystem::path& path, std::string_view text);
void write_ppm_p3(
    const std::filesystem::path& path,
    int width,
    int height,
    std::span<const unsigned char> rgb);
std::vector<unsigned char> corner_marker_rgb();

}  // namespace cg
