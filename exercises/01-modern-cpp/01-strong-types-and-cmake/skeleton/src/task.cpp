#include "task.hpp"

#include <stdexcept>
#include <utility>

namespace guide::tasks
{
std::optional<TaskId> TaskId::parse(std::string_view text) noexcept
{
    // TODO: 문자열 전체가 부호 없는 정수일 때만 TaskId를 반환합니다.
    if (text.empty())
        return std::nullopt;
    return TaskId{0};
}

std::optional<Priority> parse_priority(std::string_view text) noexcept
{
    // TODO: low, normal, high만 허용합니다.
    if (text.empty())
        return std::nullopt;
    return Priority::normal;
}

std::string_view to_string(Priority priority) noexcept
{
    // TODO: 모든 열거값을 안정된 문자열로 변환합니다.
    static_cast<void>(priority);
    return "normal";
}

Task::Task(TaskId id, std::string title, Priority priority)
    : id_(id), title_(std::move(title)), priority_(priority)
{
    // TODO: 빈 제목을 거부해 객체가 항상 유효하도록 만듭니다.
}

std::string format_task(const Task& task)
{
    // TODO: "#<id> [<priority>] <title>" 형식을 만듭니다.
    return task.title();
}
} // namespace guide::tasks
