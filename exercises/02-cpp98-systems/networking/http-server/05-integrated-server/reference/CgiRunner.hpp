#ifndef CGIRUNNER_HPP
#define CGIRUNNER_HPP

#include <cstddef>
#include <string>

// [Implementation 3] child process의 exit, timeout, output limit을 HTTP와 독립된 구조화 결과로 표현합니다.
struct CgiResult
{
    enum Outcome
    {
        Success,
        TimedOut,
        OutputLimit,
        Failed
    };

    Outcome outcome;
    int exitCode;
    std::string output;

    CgiResult()
        : outcome(Failed), exitCode(1), output()
    {
    }
};

class CgiRunner
{
public:
    CgiResult run(
        const std::string &executable,
        const std::string &input,
        int timeoutMs,
        std::size_t maxOutputBytes) const;
};

#endif
