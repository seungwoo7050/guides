#ifndef GUIDE_MODERN_UNIQUE_FILE_HPP
#define GUIDE_MODERN_UNIQUE_FILE_HPP

#include <cstdio>
#include <filesystem>
#include <string>
#include <string_view>
#include <system_error>
#include <variant>

namespace guide::io
{
struct FileError
{
    std::filesystem::path path;
    std::error_code error;
};

class UniqueFile
{
public:
    UniqueFile() noexcept = default;
    ~UniqueFile();

    UniqueFile(const UniqueFile&) = delete;
    UniqueFile& operator=(const UniqueFile&) = delete;

    UniqueFile(UniqueFile&& other) noexcept;
    UniqueFile& operator=(UniqueFile&& other) noexcept;

    [[nodiscard]] bool is_open() const noexcept { return handle_ != nullptr; }
    [[nodiscard]] std::FILE* get() const noexcept { return handle_; }

    void write(std::string_view text);
    [[nodiscard]] std::string read_all();
    void close() noexcept;

private:
    explicit UniqueFile(std::FILE* handle) noexcept : handle_(handle) {}

    std::FILE* handle_{nullptr};

    friend std::variant<UniqueFile, FileError> open_file(
        const std::filesystem::path& path,
        const char* mode);
};

using OpenResult = std::variant<UniqueFile, FileError>;

[[nodiscard]] OpenResult open_file(const std::filesystem::path& path, const char* mode);
} // namespace guide::io

#endif
