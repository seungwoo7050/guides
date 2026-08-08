#include "job_runner.hpp"

#include <fstream>
#include <stdexcept>
#include <utility>

namespace guide::jobs
{
std::string_view to_string(JobStatus status) noexcept
{
    // TODO: 모든 상태를 안정된 journal 문자열로 변환합니다.
    static_cast<void>(status);
    return "unknown";
}

JobRunner::JobRunner(std::filesystem::path journal_path, std::size_t queue_capacity)
    : journal_path_(std::move(journal_path)), queue_capacity_(queue_capacity)
{
    if (queue_capacity_ == 0)
        throw std::invalid_argument("queue capacity must be greater than zero");
    // TODO: journal을 검증하고 jthread worker와 stop source를 초기화합니다.
    static_cast<void>(next_id_);
    static_cast<void>(journal_healthy_);
}

JobRunner::~JobRunner()
{
    stop();
}

SubmitResult JobRunner::submit(std::string name, Work work)
{
    // TODO: 입력, 종료 상태와 bounded queue를 검사한 뒤 작업을 등록합니다.
    static_cast<void>(work);
    if (name.empty())
        return SubmitResult::failure(SubmitError::empty_name);
    return SubmitResult::failure(SubmitError::stopped);
}

bool JobRunner::cancel(JobId id)
{
    // TODO: queued 작업은 제거하고 running 작업은 stop을 요청합니다.
    static_cast<void>(id);
    return false;
}

std::optional<JobSnapshot> JobRunner::snapshot(JobId id) const
{
    // TODO: 잠금 아래에서 값 snapshot을 복사합니다.
    static_cast<void>(id);
    return std::nullopt;
}

bool JobRunner::wait_for_terminal(JobId id, std::chrono::milliseconds timeout)
{
    // TODO: 존재하지 않는 ID는 즉시 거부하고 condition-variable predicate로 기다립니다.
    static_cast<void>(id);
    static_cast<void>(timeout);
    return false;
}

bool JobRunner::journal_healthy() const
{
    // TODO: journal 상태를 data race 없이 반환합니다.
    return false;
}

void JobRunner::stop()
{
    // TODO: 새 제출을 닫고 queued/running 작업에 취소를 전파한 뒤 안전하게 join합니다.
    accepting_ = false;
}

bool JobRunner::is_terminal(JobStatus status) noexcept
{
    return status == JobStatus::succeeded || status == JobStatus::failed ||
           status == JobStatus::cancelled;
}

void JobRunner::run(std::stop_token stop_token)
{
    // TODO: predicate wait, 상태 전이, 예외 경계와 종료 통지를 구현합니다.
    static_cast<void>(stop_token);
}

void JobRunner::append_transition_locked(const JobSnapshot& snapshot) noexcept
{
    // TODO: tab/newline을 정규화하고 runtime journal 실패를 health 상태로 드러냅니다.
    static_cast<void>(snapshot);
}

void JobRunner::join_worker()
{
    // TODO: self-join을 피하고 동시에 들어온 stop 호출을 하나의 join으로 수렴시킵니다.
    static_cast<void>(join_started_);
    static_cast<void>(joined_);
}
} // namespace guide::jobs
