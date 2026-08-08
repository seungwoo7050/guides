#include "job_runner.hpp"
#include "test.hpp"

#include <chrono>
#include <condition_variable>
#include <concepts>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <future>
#include <iterator>
#include <mutex>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <type_traits>
#include <utility>

using namespace std::chrono_literals;
using guide::jobs::JobId;
using guide::jobs::JobRunner;
using guide::jobs::JobStatus;
using guide::jobs::SubmitError;
using guide::jobs::Work;

static_assert(!std::is_convertible_v<std::uint64_t, JobId>);
static_assert(std::three_way_comparable<JobId>);
static_assert(!std::is_copy_constructible_v<JobRunner>);
static_assert(!std::is_copy_assignable_v<JobRunner>);
static_assert(!std::is_move_constructible_v<JobRunner>);
static_assert(!std::is_move_assignable_v<JobRunner>);

namespace
{
template <typename Callable>
bool throws_logic_error(Callable&& callable)
{
    try
    {
        std::forward<Callable>(callable)();
    }
    catch (const std::logic_error&)
    {
        return true;
    }
    catch (...)
    {
        return false;
    }
    return false;
}

std::string read_text(const std::filesystem::path& path)
{
    std::ifstream input{path};
    return {std::istreambuf_iterator<char>{input}, std::istreambuf_iterator<char>{}};
}
} // namespace

int main()
{
    guide::test::Suite suite{"local-job-runner"};
    guide::test::TempDirectory temp{"guide-cpp-job-runner"};

    const auto successful_result = guide::Result<int, std::string>::success(7);
    GUIDE_CHECK(suite, successful_result.has_value());
    if (successful_result.has_value())
        GUIDE_CHECK_EQ(suite, successful_result.value(), 7);
    GUIDE_CHECK(
        suite,
        throws_logic_error([&successful_result] {
            static_cast<void>(successful_result.error());
        }));

    const auto failed_result =
        guide::Result<int, std::string>::failure("rejected");
    GUIDE_CHECK(suite, !failed_result.has_value());
    if (!failed_result.has_value())
        GUIDE_CHECK_EQ(suite, failed_result.error(), std::string{"rejected"});
    GUIDE_CHECK(
        suite,
        throws_logic_error([&failed_result] {
            static_cast<void>(failed_result.value());
        }));

    bool rejected_zero_capacity = false;
    try
    {
        static_cast<void>(JobRunner{temp.path() / "zero.tsv", 0});
    }
    catch (const std::invalid_argument&)
    {
        rejected_zero_capacity = true;
    }
    GUIDE_CHECK(suite, rejected_zero_capacity);

    const auto journal_directory = temp.path() / "journal-is-directory";
    std::filesystem::create_directories(journal_directory);
    bool rejected_unwritable_journal = false;
    try
    {
        static_cast<void>(JobRunner{journal_directory, 1});
    }
    catch (const std::runtime_error&)
    {
        rejected_unwritable_journal = true;
    }
    GUIDE_CHECK(suite, rejected_unwritable_journal);

    JobRunner runner{temp.path() / "jobs.tsv", 1};
    GUIDE_CHECK(suite, runner.journal_healthy());
    GUIDE_CHECK_EQ(
        suite,
        guide::jobs::to_string(JobStatus::queued),
        std::string_view{"queued"});
    GUIDE_CHECK_EQ(
        suite,
        guide::jobs::to_string(JobStatus::running),
        std::string_view{"running"});
    GUIDE_CHECK_EQ(
        suite,
        guide::jobs::to_string(JobStatus::succeeded),
        std::string_view{"succeeded"});
    GUIDE_CHECK_EQ(
        suite,
        guide::jobs::to_string(JobStatus::failed),
        std::string_view{"failed"});
    GUIDE_CHECK_EQ(
        suite,
        guide::jobs::to_string(JobStatus::cancelled),
        std::string_view{"cancelled"});

    const auto empty_name = runner.submit("", [](std::stop_token) {
        return std::string{"never"};
    });
    GUIDE_CHECK(suite, !empty_name.has_value());
    if (!empty_name)
        GUIDE_CHECK_EQ(suite, empty_name.error(), SubmitError::empty_name);

    const auto empty_work = runner.submit("empty-work", Work{});
    GUIDE_CHECK(suite, !empty_work.has_value());
    if (!empty_work)
        GUIDE_CHECK_EQ(suite, empty_work.error(), SubmitError::empty_work);

    GUIDE_CHECK(suite, !runner.snapshot(JobId{999}).has_value());
    GUIDE_CHECK(suite, !runner.cancel(JobId{999}));
    const auto missing_wait_started = std::chrono::steady_clock::now();
    GUIDE_CHECK(suite, !runner.wait_for_terminal(JobId{999}, 500ms));
    GUIDE_CHECK(
        suite,
        std::chrono::steady_clock::now() - missing_wait_started < 250ms);

    const auto completed = runner.submit("complete", [](std::stop_token) {
        return std::string{"done"};
    });
    GUIDE_CHECK(suite, completed.has_value());
    if (completed)
    {
        GUIDE_CHECK(suite, runner.wait_for_terminal(completed.value(), 2s));
        const auto state = runner.snapshot(completed.value());
        GUIDE_CHECK(suite, state.has_value());
        if (state)
        {
            GUIDE_CHECK_EQ(suite, state->status, JobStatus::succeeded);
            GUIDE_CHECK_EQ(suite, state->output, std::string{"done"});
        }
        GUIDE_CHECK(suite, !runner.cancel(completed.value()));
    }

    const auto failed = runner.submit("fail", [](std::stop_token) -> std::string {
        throw std::runtime_error("boom");
    });
    GUIDE_CHECK(suite, failed.has_value());
    if (failed)
    {
        GUIDE_CHECK(suite, runner.wait_for_terminal(failed.value(), 2s));
        const auto state = runner.snapshot(failed.value());
        GUIDE_CHECK(suite, state.has_value());
        if (state)
        {
            GUIDE_CHECK_EQ(suite, state->status, JobStatus::failed);
            GUIDE_CHECK_EQ(suite, state->error, std::string{"boom"});
        }
    }

    const auto unknown_failure = runner.submit(
        "unknown-failure",
        [](std::stop_token) -> std::string { throw 7; });
    GUIDE_CHECK(suite, unknown_failure.has_value());
    if (unknown_failure)
    {
        GUIDE_CHECK(suite, runner.wait_for_terminal(unknown_failure.value(), 2s));
        const auto state = runner.snapshot(unknown_failure.value());
        GUIDE_CHECK(suite, state.has_value());
        if (state)
        {
            GUIDE_CHECK_EQ(suite, state->status, JobStatus::failed);
            GUIDE_CHECK_EQ(suite, state->error, std::string{"unknown exception"});
        }
    }

    const auto normalized = runner.submit(
        "line\tbreak\nname",
        [](std::stop_token) { return std::string{"out\tline\nvalue"}; });
    GUIDE_CHECK(suite, normalized.has_value());
    if (normalized)
        GUIDE_CHECK(suite, runner.wait_for_terminal(normalized.value(), 2s));

    std::promise<void> started_promise;
    std::promise<void> release_promise;
    const std::shared_future<void> release = release_promise.get_future().share();

    const auto blocking = runner.submit(
        "blocking",
        [&started_promise, release](std::stop_token) {
            started_promise.set_value();
            release.wait();
            return std::string{"released"};
        });
    GUIDE_CHECK(suite, blocking.has_value());
    if (blocking)
        GUIDE_CHECK_EQ(suite, started_promise.get_future().wait_for(2s), std::future_status::ready);

    const auto queued = runner.submit("queued", [](std::stop_token) {
        return std::string{"queued-done"};
    });
    GUIDE_CHECK(suite, queued.has_value());

    const auto overflow = runner.submit("overflow", [](std::stop_token) {
        return std::string{"never"};
    });
    GUIDE_CHECK(suite, !overflow.has_value());
    if (!overflow)
        GUIDE_CHECK_EQ(suite, overflow.error(), SubmitError::queue_full);

    release_promise.set_value();
    if (blocking)
        GUIDE_CHECK(suite, runner.wait_for_terminal(blocking.value(), 2s));
    if (queued)
        GUIDE_CHECK(suite, runner.wait_for_terminal(queued.value(), 2s));

    {
        JobRunner queued_cancellation{temp.path() / "queued-cancellation.tsv", 1};
        std::promise<void> queue_started;
        std::promise<void> queue_release;
        const std::shared_future<void> queue_gate = queue_release.get_future().share();

        const auto running = queued_cancellation.submit(
            "running",
            [&queue_started, queue_gate](std::stop_token) {
                queue_started.set_value();
                queue_gate.wait();
                return std::string{"running-done"};
            });
        GUIDE_CHECK(suite, running.has_value());
        GUIDE_CHECK_EQ(
            suite,
            queue_started.get_future().wait_for(2s),
            std::future_status::ready);

        const auto queued_job = queued_cancellation.submit(
            "cancel-before-run",
            [](std::stop_token) { return std::string{"must-not-run"}; });
        GUIDE_CHECK(suite, queued_job.has_value());
        if (queued_job)
        {
            GUIDE_CHECK(suite, queued_cancellation.cancel(queued_job.value()));
            GUIDE_CHECK(suite, !queued_cancellation.cancel(queued_job.value()));
            GUIDE_CHECK(
                suite,
                queued_cancellation.wait_for_terminal(queued_job.value(), 2s));
            const auto state = queued_cancellation.snapshot(queued_job.value());
            GUIDE_CHECK(suite, state.has_value());
            if (state)
            {
                GUIDE_CHECK_EQ(suite, state->status, JobStatus::cancelled);
                GUIDE_CHECK_EQ(suite, state->output, std::string{});
            }
        }

        const auto replacement = queued_cancellation.submit(
            "replacement",
            [](std::stop_token) { return std::string{"replacement-done"}; });
        GUIDE_CHECK(suite, replacement.has_value());
        queue_release.set_value();
        if (running)
            GUIDE_CHECK(
                suite,
                queued_cancellation.wait_for_terminal(running.value(), 2s));
        if (replacement)
        {
            GUIDE_CHECK(
                suite,
                queued_cancellation.wait_for_terminal(replacement.value(), 2s));
            const auto state = queued_cancellation.snapshot(replacement.value());
            GUIDE_CHECK(suite, state.has_value());
            if (state)
                GUIDE_CHECK_EQ(suite, state->status, JobStatus::succeeded);
        }
        queued_cancellation.stop();
    }

    std::promise<void> cancellation_started;
    const auto cancellable = runner.submit(
        "cancellable",
        [&cancellation_started](std::stop_token token) {
            cancellation_started.set_value();
            std::mutex mutex;
            std::condition_variable_any changed;
            std::unique_lock lock{mutex};
            changed.wait(lock, token, [] { return false; });
            return std::string{"cancel observed"};
        });
    GUIDE_CHECK(suite, cancellable.has_value());
    if (cancellable)
    {
        GUIDE_CHECK_EQ(
            suite,
            cancellation_started.get_future().wait_for(2s),
            std::future_status::ready);
        GUIDE_CHECK(suite, runner.cancel(cancellable.value()));
        GUIDE_CHECK(suite, !runner.cancel(cancellable.value()));
        GUIDE_CHECK(suite, runner.wait_for_terminal(cancellable.value(), 2s));
        const auto state = runner.snapshot(cancellable.value());
        GUIDE_CHECK(suite, state.has_value());
        if (state)
            GUIDE_CHECK_EQ(suite, state->status, JobStatus::cancelled);
    }

    runner.stop();
    runner.stop();
    const auto after_stop = runner.submit("late", [](std::stop_token) {
        return std::string{"late"};
    });
    GUIDE_CHECK(suite, !after_stop.has_value());
    if (!after_stop)
        GUIDE_CHECK_EQ(suite, after_stop.error(), SubmitError::stopped);

    const std::string journal = read_text(temp.path() / "jobs.tsv");
    GUIDE_CHECK(suite, journal.find("\tqueued\tcomplete\t") != std::string::npos);
    GUIDE_CHECK(suite, journal.find("\tsucceeded\tcomplete\tdone") != std::string::npos);
    GUIDE_CHECK(suite, journal.find("\tfailed\tfail\tboom") != std::string::npos);
    GUIDE_CHECK(
        suite,
        journal.find("\tfailed\tunknown-failure\tunknown exception") !=
            std::string::npos);
    GUIDE_CHECK(
        suite,
        journal.find("\tsucceeded\tline break name\tout line value") !=
            std::string::npos);
    GUIDE_CHECK(suite, journal.find("\tcancelled\tcancellable\t") != std::string::npos);
    GUIDE_CHECK(suite, runner.journal_healthy());

    {
        const auto directory = temp.path() / "journal-failure";
        JobRunner resilient{directory / "jobs.tsv", 2};
        std::filesystem::remove_all(directory);
        const auto accepted = resilient.submit("still-runs", [](std::stop_token) {
            return std::string{"ok"};
        });
        GUIDE_CHECK(suite, accepted.has_value());
        if (accepted)
        {
            GUIDE_CHECK(suite, resilient.wait_for_terminal(accepted.value(), 2s));
            const auto state = resilient.snapshot(accepted.value());
            GUIDE_CHECK(suite, state.has_value());
            if (state)
                GUIDE_CHECK_EQ(suite, state->status, JobStatus::succeeded);
        }
        GUIDE_CHECK(suite, !resilient.journal_healthy());

        std::filesystem::create_directories(directory);
        const auto after_recovery = resilient.submit(
            "health-stays-false",
            [](std::stop_token) { return std::string{"ok-again"}; });
        GUIDE_CHECK(suite, after_recovery.has_value());
        if (after_recovery)
        {
            GUIDE_CHECK(
                suite,
                resilient.wait_for_terminal(after_recovery.value(), 2s));
        }
        GUIDE_CHECK(suite, !resilient.journal_healthy());
        resilient.stop();
    }

    {
        JobRunner synchronous{temp.path() / "synchronous.tsv", 2};
        std::promise<void> started;
        const auto work = synchronous.submit(
            "wait-for-stop",
            [&started](std::stop_token token) {
                started.set_value();
                std::mutex mutex;
                std::condition_variable_any changed;
                std::unique_lock lock{mutex};
                changed.wait(lock, token, [] { return false; });
                return std::string{"stopped"};
            });
        GUIDE_CHECK(suite, work.has_value());
        GUIDE_CHECK_EQ(suite, started.get_future().wait_for(2s), std::future_status::ready);
        synchronous.stop();
        if (work)
        {
            const auto state = synchronous.snapshot(work.value());
            GUIDE_CHECK(suite, state.has_value());
            if (state)
                GUIDE_CHECK_EQ(suite, state->status, JobStatus::cancelled);
        }
    }


    {
        JobRunner concurrent{temp.path() / "concurrent-stop.tsv", 2};
        std::promise<void> started;
        const auto work = concurrent.submit(
            "concurrent-stop",
            [&started](std::stop_token token) {
                started.set_value();
                std::mutex mutex;
                std::condition_variable_any changed;
                std::unique_lock lock{mutex};
                changed.wait(lock, token, [] { return false; });
                return std::string{"stopped"};
            });
        GUIDE_CHECK(suite, work.has_value());
        GUIDE_CHECK_EQ(suite, started.get_future().wait_for(2s), std::future_status::ready);

        std::jthread first{[&concurrent] { concurrent.stop(); }};
        std::jthread second{[&concurrent] { concurrent.stop(); }};
        first.join();
        second.join();

        if (work)
        {
            const auto state = concurrent.snapshot(work.value());
            GUIDE_CHECK(suite, state.has_value());
            if (state)
                GUIDE_CHECK_EQ(suite, state->status, JobStatus::cancelled);
        }
    }

    {
        JobRunner reentrant{temp.path() / "reentrant.tsv", 1};
        const auto self_stop = reentrant.submit(
            "self-stop",
            [&reentrant](std::stop_token) {
                reentrant.stop();
                return std::string{"returned"};
            });
        GUIDE_CHECK(suite, self_stop.has_value());
        if (self_stop)
        {
            GUIDE_CHECK(suite, reentrant.wait_for_terminal(self_stop.value(), 2s));
            const auto state = reentrant.snapshot(self_stop.value());
            GUIDE_CHECK(suite, state.has_value());
            if (state)
                GUIDE_CHECK_EQ(suite, state->status, JobStatus::cancelled);
        }
        reentrant.stop();
    }

    return suite.finish();
}
