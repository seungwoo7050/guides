#ifndef GUIDE_MODERN_QUERY_PIPELINE_HPP
#define GUIDE_MODERN_QUERY_PIPELINE_HPP

#include <chrono>
#include <concepts>
#include <cstdint>
#include <functional>
#include <optional>
#include <ranges>
#include <span>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace guide::query
{
enum class Status
{
    pending,
    running,
    succeeded,
    failed
};

struct Job
{
    std::uint64_t id;
    std::string name;
    Status status;
    std::chrono::milliseconds duration;
    std::vector<std::string> tags;
};

enum class SortKey
{
    id,
    duration
};

struct Query
{
    std::optional<Status> status;
    std::optional<std::chrono::milliseconds> maximum_duration;
    std::optional<std::string> required_tag;
    SortKey sort_key{SortKey::id};
    bool descending{false};
};

using JobReference = std::reference_wrapper<const Job>;

[[nodiscard]] std::vector<JobReference> select_jobs(
    std::span<const Job> jobs,
    const Query& query);

template <typename Range>
concept JobReferenceRange =
    std::ranges::input_range<Range> &&
    std::same_as<
        std::remove_cvref_t<std::ranges::range_reference_t<Range>>,
        JobReference>;

template <JobReferenceRange Range>
[[nodiscard]] std::string summarize(const Range& jobs)
{
    std::string output;
    bool first = true;
    for (const JobReference reference : jobs)
    {
        if (!first)
            output += ", ";
        first = false;
        output += std::to_string(reference.get().id);
        output += ':';
        output += reference.get().name;
    }
    return output;
}
} // namespace guide::query

#endif
