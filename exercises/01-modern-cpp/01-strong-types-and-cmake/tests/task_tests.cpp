#include "task.hpp"
#include "test.hpp"

#include <concepts>
#include <cstdint>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>

using guide::tasks::Priority;
using guide::tasks::Task;
using guide::tasks::TaskId;

static_assert(!std::is_convertible_v<std::uint64_t, TaskId>);
static_assert(std::is_trivially_copyable_v<TaskId>);
static_assert(std::three_way_comparable<TaskId>);

int main()
{
    guide::test::Suite suite{"strong-types-and-cmake"};

    const auto id = TaskId::parse("42");
    GUIDE_CHECK(suite, id.has_value());
    if (id)
        GUIDE_CHECK_EQ(suite, id->value(), std::uint64_t{42});

    const auto maximum = TaskId::parse("18446744073709551615");
    GUIDE_CHECK(suite, maximum.has_value());
    if (maximum)
        GUIDE_CHECK_EQ(suite, maximum->value(), std::numeric_limits<std::uint64_t>::max());

    const auto zero = TaskId::parse("0");
    GUIDE_CHECK(suite, zero.has_value());
    if (zero)
        GUIDE_CHECK_EQ(suite, zero->value(), std::uint64_t{0});

    const auto leading_zero = TaskId::parse("00042");
    GUIDE_CHECK(suite, leading_zero.has_value());
    if (leading_zero)
        GUIDE_CHECK_EQ(suite, leading_zero->value(), std::uint64_t{42});

    GUIDE_CHECK(suite, !TaskId::parse("").has_value());
    GUIDE_CHECK(suite, !TaskId::parse("42x").has_value());
    GUIDE_CHECK(suite, !TaskId::parse("-1").has_value());
    GUIDE_CHECK(suite, !TaskId::parse("+1").has_value());
    GUIDE_CHECK(suite, !TaskId::parse(" 42").has_value());
    GUIDE_CHECK(suite, !TaskId::parse("42\n").has_value());
    GUIDE_CHECK(suite, !TaskId::parse(std::string_view{"42\0", 3}).has_value());
    GUIDE_CHECK(suite, !TaskId::parse("18446744073709551616").has_value());

    GUIDE_CHECK_EQ(suite, guide::tasks::parse_priority("low"), std::optional{Priority::low});
    GUIDE_CHECK_EQ(
        suite,
        guide::tasks::parse_priority("normal"),
        std::optional{Priority::normal});
    GUIDE_CHECK_EQ(suite, guide::tasks::parse_priority("high"), std::optional{Priority::high});
    GUIDE_CHECK(suite, !guide::tasks::parse_priority("").has_value());
    GUIDE_CHECK(suite, !guide::tasks::parse_priority("High").has_value());
    GUIDE_CHECK(suite, !guide::tasks::parse_priority("urgent").has_value());

    GUIDE_CHECK_EQ(suite, guide::tasks::to_string(Priority::low), std::string_view{"low"});
    GUIDE_CHECK_EQ(
        suite,
        guide::tasks::to_string(Priority::normal),
        std::string_view{"normal"});
    GUIDE_CHECK_EQ(suite, guide::tasks::to_string(Priority::high), std::string_view{"high"});

    const Task task{TaskId{7}, "write tests", Priority::high};
    GUIDE_CHECK_EQ(suite, task.id().value(), std::uint64_t{7});
    GUIDE_CHECK_EQ(suite, task.title(), std::string{"write tests"});
    GUIDE_CHECK_EQ(suite, guide::tasks::format_task(task), std::string{"#7 [high] write tests"});

    bool rejected_empty_title = false;
    try
    {
        static_cast<void>(Task{TaskId{8}, "", Priority::low});
    }
    catch (const std::invalid_argument&)
    {
        rejected_empty_title = true;
    }
    GUIDE_CHECK(suite, rejected_empty_title);

    return suite.finish();
}
