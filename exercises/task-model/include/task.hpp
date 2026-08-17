#ifndef TASK_MODEL_TASK_HPP
#define TASK_MODEL_TASK_HPP

#include <compare>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace tasks
{
// [Implementation 1] Domain value model
// Domain values own validation-relevant state instead of exposing raw primitives.
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
} // namespace tasks

#endif
