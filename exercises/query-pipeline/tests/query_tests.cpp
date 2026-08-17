#include "query.hpp"

#include <array>
#include <cassert>
#include <chrono>
#include <memory>
#include <string>
#include <vector>

using namespace std::chrono_literals;
using query::Job;
using query::JobReference;
using query::Query;
using query::SortKey;
using query::Status;

static_assert(query::JobReferenceRange<std::vector<JobReference>>);
static_assert(!query::JobReferenceRange<std::vector<Job>>);
static_assert(!query::JobReferenceRange<std::array<int, 2>>);

int main()
{
    const std::vector<Job> source{
        Job{4, "compile", Status::succeeded, 40ms, {"build", "cpu"}},
        Job{2, "lint", Status::failed, 15ms, {"quality"}},
        Job{7, "test", Status::succeeded, 15ms, {"quality", "cpu"}},
        Job{1, "package", Status::pending, 80ms, {"build"}},
        Job{5, "deploy", Status::running, 30ms, {"network"}},
    };

    const auto all = query::select_jobs(source, Query{});
    assert(query::summarize(all) ==
           "1:package, 2:lint, 4:compile, 5:deploy, 7:test");

    Query succeeded;
    succeeded.status = Status::succeeded;
    succeeded.sort_key = SortKey::duration;
    assert(query::summarize(query::select_jobs(source, succeeded)) ==
           "7:test, 4:compile");

    Query quality;
    quality.required_tag = "quality";
    quality.maximum_duration = 20ms;
    quality.descending = true;
    assert(query::summarize(query::select_jobs(source, quality)) ==
           "7:test, 2:lint");

    Query short_jobs;
    short_jobs.maximum_duration = 30ms;
    short_jobs.sort_key = SortKey::duration;
    assert(query::summarize(query::select_jobs(source, short_jobs)) ==
           "2:lint, 7:test, 5:deploy");
    short_jobs.descending = true;
    assert(query::summarize(query::select_jobs(source, short_jobs)) ==
           "5:deploy, 7:test, 2:lint");

    Query absent;
    absent.required_tag = "missing";
    assert(query::select_jobs(source, absent).empty());

    assert(source.front().name == "compile");
    assert(source.back().name == "deploy");
    assert(std::addressof(all.front().get()) == std::addressof(source[3]));
}
