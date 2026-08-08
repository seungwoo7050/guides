#ifndef CGIRUNNER_HPP
#define CGIRUNNER_HPP

#include <cstddef>
#include <string>

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
