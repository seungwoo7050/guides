#include "task.hpp"

#include <charconv>
#include <stdexcept>
#include <system_error>
#include <utility>

namespace guide::tasks
{
// [Implementation 3] 입력 전체를 소비한 경우에만 강한 ID와 제한된 우선순위 값으로 변환합니다.
std::optional<TaskId> TaskId::parse(std::string_view text) noexcept
{
    if (text.empty())
        return std::nullopt;

    std::uint64_t value = 0;
    const char* const first = text.data();
    const char* const last = first + text.size();
    const auto [end, error] = std::from_chars(first, last, value);
    if (error != std::errc{} || end != last)
        return std::nullopt;
    return TaskId{value};
}

std::optional<Priority> parse_priority(std::string_view text) noexcept
{
    if (text == "low")
        return Priority::low;
    if (text == "normal")
        return Priority::normal;
    if (text == "high")
        return Priority::high;
    return std::nullopt;
}

std::string_view to_string(Priority priority) noexcept
{
    switch (priority)
    {
    case Priority::low:
        return "low";
    case Priority::normal:
        return "normal";
    case Priority::high:
        return "high";
    }
    return "unknown";
}

// [Implementation 4] Task 생성 시 빈 제목을 거부해 이후 모든 사용자가 같은 불변식을 공유하게 합니다.
Task::Task(TaskId id, std::string title, Priority priority)
    : id_(id), title_(std::move(title)), priority_(priority)
{
    if (title_.empty())
        throw std::invalid_argument("task title must not be empty");
}

// [Implementation 5] 유효한 도메인 값을 하나의 안정된 외부 문자열 형식으로 직렬화합니다.
std::string format_task(const Task& task)
{
    return "#" + std::to_string(task.id().value()) + " [" +
           std::string{to_string(task.priority())} + "] " + task.title();
}
} // namespace guide::tasks
