#include "test.hpp"
#include "unique_file.hpp"

#include <filesystem>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <system_error>
#include <type_traits>
#include <utility>
#include <variant>

using guide::io::FileError;
using guide::io::UniqueFile;

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
    guide::test::Suite suite{"unique-file"};
    guide::test::TempDirectory temp{"guide-cpp-unique-file"};

    const auto invalid_mode = guide::io::open_file(temp.path() / "invalid.txt", nullptr);
    GUIDE_CHECK(suite, std::holds_alternative<FileError>(invalid_mode));
    if (const auto* error = std::get_if<FileError>(&invalid_mode))
        GUIDE_CHECK_EQ(suite, error->error, std::make_error_code(std::errc::invalid_argument));

    const auto missing = guide::io::open_file(temp.path() / "missing" / "file.txt", "rb");
    GUIDE_CHECK(suite, std::holds_alternative<FileError>(missing));
    if (const auto* error = std::get_if<FileError>(&missing))
    {
        GUIDE_CHECK_EQ(suite, error->path, temp.path() / "missing" / "file.txt");
        GUIDE_CHECK(suite, static_cast<bool>(error->error));
    }

    UniqueFile closed;
    GUIDE_CHECK(suite, !closed.is_open());
    GUIDE_CHECK(suite, throws_logic_error([&closed] { closed.write("no"); }));
    GUIDE_CHECK(suite, throws_logic_error([&closed] { static_cast<void>(closed.read_all()); }));

    const auto first_path = temp.path() / "first.bin";
    auto opened = guide::io::open_file(first_path, "w+b");
    GUIDE_CHECK(suite, std::holds_alternative<UniqueFile>(opened));
    if (!std::holds_alternative<UniqueFile>(opened))
        return suite.finish();

    std::string payload(600, 'x');
    payload[255] = '\0';
    payload[511] = 'z';

    UniqueFile first = std::move(std::get<UniqueFile>(opened));
    first.write({});
    first.write(payload);
    UniqueFile moved = std::move(first);
    GUIDE_CHECK(suite, !first.is_open());
    GUIDE_CHECK(suite, throws_logic_error([&first] { first.write("moved"); }));
    GUIDE_CHECK(suite, moved.is_open());
    GUIDE_CHECK_EQ(suite, moved.read_all(), payload);
    GUIDE_CHECK_EQ(suite, moved.read_all(), payload);

    const auto second_path = temp.path() / "second.txt";
    auto second_opened = guide::io::open_file(second_path, "w+b");
    GUIDE_CHECK(suite, std::holds_alternative<UniqueFile>(second_opened));
    if (!std::holds_alternative<UniqueFile>(second_opened))
        return suite.finish();

    UniqueFile second = std::move(std::get<UniqueFile>(second_opened));
    second.write("beta");
    second = std::move(moved);
    GUIDE_CHECK(suite, !moved.is_open());
    GUIDE_CHECK(suite, second.is_open());
    GUIDE_CHECK_EQ(suite, read_text(second_path), std::string{"beta"});
    GUIDE_CHECK_EQ(suite, second.read_all(), payload);
    UniqueFile* second_alias = &second;
    second = std::move(*second_alias);
    GUIDE_CHECK(suite, second.is_open());
    GUIDE_CHECK_EQ(suite, second.read_all(), payload);

    second.close();
    second.close();
    GUIDE_CHECK(suite, !second.is_open());
    GUIDE_CHECK(suite, throws_logic_error([&second] { second.write("closed"); }));

    const auto read_only_path = temp.path() / "read-only.txt";
    {
        std::ofstream output{read_only_path, std::ios::binary};
        output << "read-only";
    }
    auto read_only_result = guide::io::open_file(read_only_path, "rb");
    GUIDE_CHECK(suite, std::holds_alternative<UniqueFile>(read_only_result));
    if (auto* read_only = std::get_if<UniqueFile>(&read_only_result))
        GUIDE_CHECK_EQ(suite, read_only->read_all(), std::string{"read-only"});

    return suite.finish();
}
