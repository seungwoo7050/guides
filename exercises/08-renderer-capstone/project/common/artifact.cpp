#include "cg/artifact.hpp"

#include <fstream>
#include <stdexcept>

namespace cg {

void ensure_output_directory(const std::filesystem::path& directory) {
  if (directory.empty() || directory == directory.root_path()) {
    throw std::invalid_argument("unsafe output directory");
  }
  std::filesystem::create_directories(directory);
  if (!std::filesystem::is_directory(directory) || std::filesystem::is_symlink(directory)) {
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
