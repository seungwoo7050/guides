#ifndef HTTP_SERVER_CGI_RUNNER_HPP
#define HTTP_SERVER_CGI_RUNNER_HPP

#include <cstddef>
#include <string>

// [Implementation 3] Structured CGI outcome
// Process exit, timeout, and output limits are represented independently from HTTP.
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

    CgiResult() : outcome(Failed), exitCode(1), output() {}
};

class CgiRunner
{
public:
    CgiResult run(const std::string &executable, const std::string &input,
                  int timeoutMs, std::size_t maxOutputBytes) const;
};

#endif
