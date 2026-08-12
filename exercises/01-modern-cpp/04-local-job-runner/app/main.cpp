#include "job_runner.hpp"

#include <array>
#include <chrono>
#include <exception>
#include <filesystem>
#include <iostream>
#include <stop_token>
#include <string>
#include <utility>
#include <vector>

using namespace std::chrono_literals;

// [Implementation 10] 공개 JobRunner API를 실행 파일 흐름으로 조립하고 제출·대기·snapshot 실패를 process exit로 번역합니다.
int main(int argc, char* argv[])
{
    if (argc != 2)
    {
        std::cerr << "usage: local_job_runner <journal-path>\n";
        return 2;
    }

    try
    {
        guide::jobs::JobRunner runner{std::filesystem::path{argv[1]}, 4};
        const std::array jobs{
            std::pair{std::string{"compile"}, std::string{"compile-ready"}},
            std::pair{std::string{"test"}, std::string{"tests-passed"}},
            std::pair{std::string{"package"}, std::string{"package-ready"}},
        };

        std::vector<guide::jobs::JobId> ids;
        ids.reserve(jobs.size());
        for (const auto& [name, output] : jobs)
        {
            auto submitted = runner.submit(
                name,
                [output](std::stop_token) { return output; });
            if (!submitted)
            {
                std::cerr << "submission rejected\n";
                return 1;
            }
            ids.push_back(submitted.value());
        }

        for (const guide::jobs::JobId id : ids)
        {
            if (!runner.wait_for_terminal(id, 2s))
            {
                std::cerr << "job did not reach a terminal state: " << id.value() << '\n';
                return 1;
            }

            const auto state = runner.snapshot(id);
            if (!state)
            {
                std::cerr << "job disappeared: " << id.value() << '\n';
                return 1;
            }

            std::cout << state->id.value() << ' ' << guide::jobs::to_string(state->status);
            if (!state->output.empty())
                std::cout << ' ' << state->output;
            if (!state->error.empty())
                std::cout << ' ' << state->error;
            std::cout << '\n';

            if (state->status != guide::jobs::JobStatus::succeeded)
                return 1;
        }

        runner.stop();
        return 0;
    }
    catch (const std::exception& exception)
    {
        std::cerr << "local job runner failed: " << exception.what() << '\n';
        return 1;
    }
}
