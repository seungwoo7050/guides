#ifndef GUIDE_MODERN_SUPPORT_TEST_HPP
#define GUIDE_MODERN_SUPPORT_TEST_HPP

#include <atomic>
#include <chrono>
#include <filesystem>
#include <functional>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <thread>
#include <utility>

namespace guide::test
{
class Suite
{
public:
    explicit Suite(std::string name) : name_(std::move(name)) {}

    void check(bool condition, const char* expression, const char* file, int line)
    {
        if (condition)
            return;
        ++failures_;
        std::cerr << file << ':' << line << ": CHECK failed: " << expression << '\n';
    }

    template <typename Left, typename Right>
    void check_equal(
        const Left& left,
        const Right& right,
        const char* left_expression,
        const char* right_expression,
        const char* file,
        int line)
    {
        if (left == right)
            return;
        ++failures_;
        std::cerr << file << ':' << line << ": CHECK_EQ failed: " << left_expression
                  << " != " << right_expression << '\n';
    }

    int finish() const
    {
        if (failures_ == 0)
        {
            std::cout << name_ << ": PASS\n";
            return 0;
        }
        std::cerr << name_ << ": " << failures_ << " failure(s)\n";
        return 1;
    }

private:
    std::string name_;
    int failures_{0};
};

class TempDirectory
{
public:
    explicit TempDirectory(std::string prefix)
    {
        static std::atomic<unsigned long long> sequence{0};
        const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
        const auto thread = std::hash<std::thread::id>{}(std::this_thread::get_id());
        const auto root = std::filesystem::temp_directory_path();

        for (int attempt = 0; attempt < 100; ++attempt)
        {
            const auto serial = sequence.fetch_add(1, std::memory_order_relaxed);
            std::ostringstream name;
            name << prefix << '-' << stamp << '-' << thread << '-' << serial;
            const auto candidate = root / name.str();

            std::error_code error;
            if (std::filesystem::create_directory(candidate, error))
            {
                path_ = candidate;
                return;
            }
            if (error)
                throw std::system_error(error, "create temporary directory");
        }
        throw std::runtime_error("temporary directory collision limit reached");
    }

    TempDirectory(const TempDirectory&) = delete;
    TempDirectory& operator=(const TempDirectory&) = delete;

    ~TempDirectory()
    {
        std::error_code ignored;
        std::filesystem::remove_all(path_, ignored);
    }

    [[nodiscard]] const std::filesystem::path& path() const noexcept
    {
        return path_;
    }

private:
    std::filesystem::path path_;
};
} // namespace guide::test

#define GUIDE_CHECK(suite, expression) \
    (suite).check(static_cast<bool>(expression), #expression, __FILE__, __LINE__)

#define GUIDE_CHECK_EQ(suite, left, right) \
    (suite).check_equal((left), (right), #left, #right, __FILE__, __LINE__)

#endif
