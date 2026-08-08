#ifndef GUIDE_MODERN_STRONG_TYPES_TASK_HPP
#define GUIDE_MODERN_STRONG_TYPES_TASK_HPP

#include <compare>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace guide::tasks
{
class TaskId
{
public:
    explicit constexpr TaskId(std::uint64_t value) noexcept : value_(value) {}

    [[nodiscard]] static std::optional<TaskId> parse(std::string_view text) noexcept;
    [[nodiscard]] constexpr std::uint64_t value() const noexcept { return value_; }

    auto operator<=>(const TaskId&) const = default;

private:
    std::uint64_t value_;
};

enum class Priority
{
    low,
    normal,
    high
};

[[nodiscard]] std::optional<Priority> parse_priority(std::string_view text) noexcept;
[[nodiscard]] std::string_view to_string(Priority priority) noexcept;

class Task
{
public:
    Task(TaskId id, std::string title, Priority priority);

    [[nodiscard]] TaskId id() const noexcept { return id_; }
    [[nodiscard]] const std::string& title() const noexcept { return title_; }
    [[nodiscard]] Priority priority() const noexcept { return priority_; }

private:
    TaskId id_;
    std::string title_;
    Priority priority_;
};

[[nodiscard]] std::string format_task(const Task& task);
} // namespace guide::tasks

#endif
