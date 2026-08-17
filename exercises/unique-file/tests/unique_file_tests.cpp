#include "unique_file.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <variant>

using io::FileError;
using io::UniqueFile;

static_assert(!std::is_copy_constructible_v<UniqueFile>);
static_assert(!std::is_copy_assignable_v<UniqueFile>);
static_assert(std::is_nothrow_move_constructible_v<UniqueFile>);
static_assert(std::is_nothrow_move_assignable_v<UniqueFile>);

namespace
{
std::string read_text(const std::filesystem::path& path)
{
    std::ifstream input{path, std::ios::binary};
    return {std::istreambuf_iterator<char>{input}, std::istreambuf_iterator<char>{}};
}

template <typename Callable>
bool throws_logic_error(Callable&& callable)
{
    try
    {
        std::forward<Callable>(callable)();
    }
    catch (const std::logic_error&)
    {
        return true;
    }
    return false;
}
} // namespace

int main()
{
    const auto root = std::filesystem::temp_directory_path() /
                      ("unique-file-test-" + std::to_string(std::filesystem::file_time_type::clock::now().time_since_epoch().count()));
    std::filesystem::create_directories(root);

    const auto invalid_mode = io::open_file(root / "invalid.txt", nullptr);
    assert(std::holds_alternative<FileError>(invalid_mode));
    assert(std::get<FileError>(invalid_mode).error ==
           std::make_error_code(std::errc::invalid_argument));

    const auto missing = io::open_file(root / "missing" / "file.txt", "rb");
    assert(std::holds_alternative<FileError>(missing));
    assert(std::get<FileError>(missing).path == root / "missing" / "file.txt");

    UniqueFile closed;
    assert(!closed.is_open());
    assert(throws_logic_error([&closed] { closed.write("no"); }));
    assert(throws_logic_error([&closed] { static_cast<void>(closed.read_all()); }));

    const auto first_path = root / "first.bin";
    auto opened = io::open_file(first_path, "w+b");
    assert(std::holds_alternative<UniqueFile>(opened));
    std::string payload(600, 'x');
    payload[255] = '\0';
    payload[511] = 'z';

    UniqueFile first = std::move(std::get<UniqueFile>(opened));
    first.write({});
    first.write(payload);
    UniqueFile moved = std::move(first);
    assert(!first.is_open());
    assert(moved.is_open());
    assert(moved.read_all() == payload);

    const auto second_path = root / "second.txt";
    auto second_opened = io::open_file(second_path, "w+b");
    assert(std::holds_alternative<UniqueFile>(second_opened));
    UniqueFile second = std::move(std::get<UniqueFile>(second_opened));
    second.write("beta");
    second = std::move(moved);
    assert(!moved.is_open());
    assert(second.read_all() == payload);
    assert(read_text(second_path) == "beta");

    UniqueFile* alias = &second;
    second = std::move(*alias);
    assert(second.is_open());
    second.close();
    second.close();
    assert(!second.is_open());

    std::filesystem::remove_all(root);
}
