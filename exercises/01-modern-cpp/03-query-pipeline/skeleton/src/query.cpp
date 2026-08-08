#include "query.hpp"

namespace guide::query
{
std::vector<JobReference> select_jobs(std::span<const Job> jobs, const Query& query)
{
    // TODO: views로 필터링하고 ranges 알고리즘으로 정렬합니다.
    static_cast<void>(query);
    std::vector<JobReference> result;
    for (const Job& job : jobs)
        result.emplace_back(std::cref(job));
    return result;
}
} // namespace guide::query
