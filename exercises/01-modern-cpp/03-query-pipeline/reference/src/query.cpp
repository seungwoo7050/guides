#include "query.hpp"

#include <algorithm>

namespace guide::query
{
namespace
{
bool has_tag(const Job& job, std::string_view required)
{
    return std::ranges::any_of(job.tags, [required](const std::string& tag) {
        return tag == required;
    });
}
} // namespace

// [Implementation 3] 독립 필터를 조합한 view를 원본 수명을 공유하는 참조 목록으로 materialize합니다.
std::vector<JobReference> select_jobs(std::span<const Job> jobs, const Query& query)
{
    auto filtered = jobs | std::views::filter([&query](const Job& job) {
        if (query.status && job.status != *query.status)
            return false;
        if (query.maximum_duration && job.duration > *query.maximum_duration)
            return false;
        if (query.required_tag && !has_tag(job, *query.required_tag))
            return false;
        return true;
    });

    std::vector<JobReference> result;
    result.reserve(jobs.size());
    for (const Job& job : filtered)
        result.emplace_back(std::cref(job));

    // [Implementation 4] 선택한 key 뒤에 ID tie-breaker를 두어 방향과 무관하게 결과 순서를 결정적으로 만듭니다.
    const auto ascending = [&query](JobReference left, JobReference right) {
        const Job& lhs = left.get();
        const Job& rhs = right.get();
        if (query.sort_key == SortKey::id)
            return lhs.id < rhs.id;
        if (lhs.duration != rhs.duration)
            return lhs.duration < rhs.duration;
        return lhs.id < rhs.id;
    };

    if (query.descending)
    {
        std::ranges::sort(result, [&ascending](JobReference left, JobReference right) {
            return ascending(right, left);
        });
    }
    else
    {
        std::ranges::sort(result, ascending);
    }
    return result;
}
} // namespace guide::query
