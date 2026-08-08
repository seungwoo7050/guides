#include "query.hpp"
#include "test.hpp"

#include <array>
#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <vector>

using namespace std::chrono_literals;
using guide::query::Job;
using guide::query::JobReference;
using guide::query::Query;
using guide::query::SortKey;
using guide::query::Status;

static_assert(guide::query::JobReferenceRange<std::vector<JobReference>>);
static_assert(!guide::query::JobReferenceRange<std::vector<Job>>);
static_assert(!guide::query::JobReferenceRange<std::array<int, 2>>);

namespace
{
std::vector<Job> jobs()
{
    return {
        Job{4, "compile", Status::succeeded, 40ms, {"build", "cpu"}},
        Job{2, "lint", Status::failed, 15ms, {"quality"}},
        Job{7, "test", Status::succeeded, 15ms, {"quality", "cpu"}},
        Job{1, "package", Status::pending, 80ms, {"build"}},
        Job{5, "deploy", Status::running, 30ms, {"network"}},
    };
}
} // namespace

int main()
{
    guide::test::Suite suite{"query-pipeline"};
    const std::vector<Job> source = jobs();

    const auto all = guide::query::select_jobs(source, Query{});
    GUIDE_CHECK_EQ(suite, guide::query::summarize(all), std::string{"1:package, 2:lint, 4:compile, 5:deploy, 7:test"});

    Query succeeded;
    succeeded.status = Status::succeeded;
    succeeded.sort_key = SortKey::duration;
    const auto first = guide::query::select_jobs(source, succeeded);
    GUIDE_CHECK_EQ(suite, first.size(), std::size_t{2});
    GUIDE_CHECK_EQ(suite, guide::query::summarize(first), std::string{"7:test, 4:compile"});

    Query quality;
    quality.required_tag = "quality";
    quality.maximum_duration = 20ms;
    quality.sort_key = SortKey::id;
    quality.descending = true;
    const auto second = guide::query::select_jobs(source, quality);
    GUIDE_CHECK_EQ(suite, guide::query::summarize(second), std::string{"7:test, 2:lint"});

    Query short_jobs;
    short_jobs.maximum_duration = 30ms;
    short_jobs.sort_key = SortKey::duration;
    const auto third = guide::query::select_jobs(source, short_jobs);
    GUIDE_CHECK_EQ(
        suite,
        guide::query::summarize(third),
        std::string{"2:lint, 7:test, 5:deploy"});

    short_jobs.descending = true;
    const auto fourth = guide::query::select_jobs(source, short_jobs);
    GUIDE_CHECK_EQ(
        suite,
        guide::query::summarize(fourth),
        std::string{"5:deploy, 7:test, 2:lint"});

    Query absent;
    absent.required_tag = "missing";
    GUIDE_CHECK(suite, guide::query::select_jobs(source, absent).empty());

    GUIDE_CHECK_EQ(suite, source.front().name, std::string{"compile"});
    GUIDE_CHECK_EQ(suite, source.back().name, std::string{"deploy"});
    GUIDE_CHECK(suite, !all.empty());
    if (!all.empty())
        GUIDE_CHECK(suite, std::addressof(all.front().get()) == std::addressof(source[3]));

    return suite.finish();
}
