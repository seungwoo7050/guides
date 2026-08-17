#include "task.hpp"

#include <cassert>
#include <concepts>
#include <cstdint>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>

using tasks::Priority;
using tasks::Task;
using tasks::TaskId;

static_assert(!std::is_convertible_v<std::uint64_t, TaskId>);
static_assert(std::is_trivially_copyable_v<TaskId>);
static_assert(std::three_way_comparable<TaskId>);

int main()
{
    const auto id = TaskId::parse("42");
    assert(id && id->value() == 42);
    assert(TaskId::parse("18446744073709551615")->value() ==
           std::numeric_limits<std::uint64_t>::max());
    assert(TaskId::parse("00042")->value() == 42);

    assert(!TaskId::parse(""));
    assert(!TaskId::parse("42x"));
    assert(!TaskId::parse("-1"));
    assert(!TaskId::parse("+1"));
    assert(!TaskId::parse(" 42"));
    assert(!TaskId::parse("42\n"));
    assert(!TaskId::parse(std::string_view{"42\0", 3}));
    assert(!TaskId::parse("18446744073709551616"));

    assert(tasks::parse_priority("low") == std::optional{Priority::low});
    assert(tasks::parse_priority("normal") == std::optional{Priority::normal});
    assert(tasks::parse_priority("high") == std::optional{Priority::high});
    assert(!tasks::parse_priority("High"));
    assert(!tasks::parse_priority("urgent"));

    const Task task{TaskId{7}, "write tests", Priority::high};
    assert(task.id().value() == 7);
    assert(task.title() == "write tests");
    assert(tasks::format_task(task) == "#7 [high] write tests");

    bool rejected = false;
    try
    {
        static_cast<void>(Task{TaskId{8}, "", Priority::low});
    }
    catch (const std::invalid_argument&)
    {
        rejected = true;
    }
    assert(rejected);
}
