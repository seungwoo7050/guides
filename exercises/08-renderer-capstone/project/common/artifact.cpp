#include "cg/artifact.hpp"

#include <fstream>
#include <system_error>
#include <stdexcept>

namespace cg {

namespace {

[[nodiscard]] bool path_entry_exists(
    const std::filesystem::path& path,
    std::filesystem::file_status* status = nullptr) {
  std::error_code error;
  const std::filesystem::file_status current = std::filesystem::symlink_status(path, error);
  if (error && error != std::errc::no_such_file_or_directory) {
    throw std::runtime_error("cannot inspect output path: " + path.string());
  }
  if (status != nullptr) *status = current;
  return !error && current.type() != std::filesystem::file_type::not_found;
}

void reject_linked_ancestors(const std::filesystem::path& absolute) {
  for (std::filesystem::path current = absolute.parent_path(); !current.empty();
       current = current.parent_path()) {
    std::filesystem::file_status status;
    if (path_entry_exists(current, &status) && std::filesystem::is_symlink(status)) {
      throw std::invalid_argument("output path has a symbolic-link ancestor: " + current.string());
    }
    if (current == current.root_path()) break;
  }
}

[[nodiscard]] std::filesystem::path normalized_absolute(const std::filesystem::path& directory) {
  if (directory.empty() || directory == directory.root_path()) {
    throw std::invalid_argument("unsafe output directory");
  }
  std::error_code error;
  const std::filesystem::path absolute = std::filesystem::absolute(directory, error).lexically_normal();
  if (error || absolute.empty() || absolute == absolute.root_path()) {
    throw std::invalid_argument("unsafe output directory");
  }
  return absolute;
}

}  // namespace

void validate_new_output_path(const std::filesystem::path& directory) {
  const std::filesystem::path absolute = normalized_absolute(directory);
  reject_linked_ancestors(absolute);
  if (path_entry_exists(absolute)) {
    throw std::invalid_argument("output path already exists: " + absolute.string());
  }
}

void ensure_output_directory(const std::filesystem::path& directory) {
  validate_new_output_path(directory);
  const std::filesystem::path absolute = normalized_absolute(directory);
  std::filesystem::create_directories(absolute);
  if (!std::filesystem::is_directory(absolute) || std::filesystem::is_symlink(absolute)) {
    throw std::runtime_error("output must be a real directory");
  }
}

void write_text(const std::filesystem::path& path, const std::string_view text) {
  std::ofstream output(path, std::ios::binary | std::ios::trunc);
  if (!output) throw std::runtime_error("cannot open artifact: " + path.string());
  output.write(text.data(), static_cast<std::streamsize>(text.size()));
  if (!output) throw std::runtime_error("cannot write artifact: " + path.string());
}

void write_ppm_p3(
    const std::filesystem::path& path,
    const int width,
    const int height,
    const std::span<const unsigned char> rgb) {
  if (width <= 0 || height <= 0 || rgb.size() != static_cast<std::size_t>(width * height * 3)) {
    throw std::invalid_argument("invalid PPM extent or byte count");
  }
  std::ofstream output(path, std::ios::trunc);
  if (!output) throw std::runtime_error("cannot open PPM artifact");
  output << "P3\n" << width << ' ' << height << "\n255\n";
  for (std::size_t index = 0; index < rgb.size(); ++index) {
    output << static_cast<unsigned int>(rgb[index]);
    output << ((index + 1) % 12 == 0 ? '\n' : ' ');
  }
  output << '\n';
}

std::vector<unsigned char> corner_marker_rgb() {
  return {255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255};
}

}  // namespace cg
