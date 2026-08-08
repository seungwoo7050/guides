#include "unique_file.hpp"

#include <cerrno>
#include <stdexcept>
#include <system_error>
#include <utility>

namespace guide::io
{
UniqueFile::~UniqueFile()
{
    close();
}

UniqueFile::UniqueFile(UniqueFile&& other) noexcept
{
    // TODO: 소유권을 옮기고 other를 닫힌 상태로 만듭니다.
    static_cast<void>(other);
}

UniqueFile& UniqueFile::operator=(UniqueFile&& other) noexcept
{
    // TODO: 현재 자원을 먼저 정리하고 other의 자원을 인수합니다.
    static_cast<void>(other);
    return *this;
}

void UniqueFile::write(std::string_view text)
{
    // TODO: 닫힌 파일을 거부하고 전체 쓰기와 flush를 확인합니다.
    static_cast<void>(text);
}

std::string UniqueFile::read_all()
{
    // TODO: 파일 위치를 처음으로 옮긴 뒤 EOF까지 읽습니다.
    return {};
}

void UniqueFile::close() noexcept
{
    // TODO: 여러 번 호출해도 안전해야 합니다.
    if (handle_ != nullptr)
    {
        std::fclose(handle_);
        handle_ = nullptr;
    }
}

OpenResult open_file(const std::filesystem::path& path, const char* mode)
{
    // TODO: fopen의 소유권을 UniqueFile에 넘기고 errno를 FileError로 보존합니다.
    static_cast<void>(mode);
    return FileError{path, std::error_code(errno, std::generic_category())};
}
} // namespace guide::io
