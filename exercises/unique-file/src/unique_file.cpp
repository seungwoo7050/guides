#include "unique_file.hpp"

#include <cerrno>
#include <ios>
#include <stdexcept>
#include <system_error>
#include <utility>

namespace io
{
namespace
{
std::error_code current_io_error()
{
    if (errno != 0)
        return {errno, std::generic_category()};
    return std::make_error_code(std::io_errc::stream);
}

[[noreturn]] void throw_io_error(const char* operation)
{
    throw std::system_error(current_io_error(), operation);
}
} // namespace

// [Implementation 2] Single-owner lifecycle
// Destruction, movement, and close preserve exactly one owner for each FILE*.
UniqueFile::~UniqueFile()
{
    close();
}

UniqueFile::UniqueFile(UniqueFile&& other) noexcept
    : handle_(std::exchange(other.handle_, nullptr))
{}

UniqueFile& UniqueFile::operator=(UniqueFile&& other) noexcept
{
    if (this == &other)
        return *this;
    close();
    handle_ = std::exchange(other.handle_, nullptr);
    return *this;
}

// [Implementation 3] Checked I/O boundary
// Checked operations reject closed handles and translate partial I/O into system_error.
void UniqueFile::write(std::string_view text)
{
    if (!is_open())
        throw std::logic_error("write on closed file");

    errno = 0;
    if (!text.empty() &&
        std::fwrite(text.data(), 1, text.size(), handle_) != text.size())
    {
        throw_io_error("fwrite");
    }
    errno = 0;
    if (std::fflush(handle_) != 0)
        throw_io_error("fflush");
}

std::string UniqueFile::read_all()
{
    if (!is_open())
        throw std::logic_error("read on closed file");
    errno = 0;
    if (std::fseek(handle_, 0, SEEK_SET) != 0)
        throw_io_error("fseek");

    std::string content;
    char buffer[256];
    while (true)
    {
        errno = 0;
        const std::size_t count = std::fread(buffer, 1, sizeof(buffer), handle_);
        content.append(buffer, count);
        if (count < sizeof(buffer))
        {
            if (std::ferror(handle_) != 0)
                throw_io_error("fread");
            break;
        }
    }
    return content;
}

void UniqueFile::close() noexcept
{
    if (handle_ == nullptr)
        return;
    std::fclose(handle_);
    handle_ = nullptr;
}

// [Implementation 4] Resource acquisition result
// Acquisition returns the original path and error code without constructing an invalid owner.
OpenResult open_file(const std::filesystem::path& path, const char* mode)
{
    if (mode == nullptr)
    {
        return FileError{
            path,
            std::make_error_code(std::errc::invalid_argument),
        };
    }

    errno = 0;
    std::FILE* handle = std::fopen(path.string().c_str(), mode);
    if (handle == nullptr)
        return FileError{path, current_io_error()};
    return UniqueFile{handle};
}
} // namespace io
