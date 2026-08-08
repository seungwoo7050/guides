#include "CgiRunner.hpp"

#include <cerrno>
#include <csignal>
#include <cstring>
#include <fcntl.h>
#include <poll.h>
#include <stdexcept>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

namespace
{
class ScopedFd
{
public:
    ScopedFd() : fd_(-1) {}
    explicit ScopedFd(int fd) : fd_(fd) {}

    ~ScopedFd()
    {
        reset();
    }

    int get() const
    {
        return fd_;
    }

    bool valid() const
    {
        return fd_ != -1;
    }

    void reset(int fd = -1)
    {
        if (fd_ != -1)
            ::close(fd_);
        fd_ = fd;
    }

private:
    ScopedFd(const ScopedFd &);
    ScopedFd &operator=(const ScopedFd &);

    int fd_;
};

void setNonblocking(int fd)
{
    const int flags = ::fcntl(fd, F_GETFL, 0);
    if (flags == -1
        || ::fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1)
    {
        throw std::runtime_error(std::string("fcntl: ")
            + std::strerror(errno));
    }
}

long elapsedMilliseconds(const timeval &start)
{
    timeval now;
    if (::gettimeofday(&now, 0) == -1)
        throw std::runtime_error("gettimeofday");
    const long seconds = static_cast<long>(now.tv_sec - start.tv_sec);
    const long microseconds
        = static_cast<long>(now.tv_usec - start.tv_usec);
    return seconds * 1000 + microseconds / 1000;
}

void waitForChild(pid_t child, int &status)
{
    pid_t result;
    do
    {
        result = ::waitpid(child, &status, 0);
    }
    while (result == -1 && errno == EINTR);
    if (result == -1)
        throw std::runtime_error(std::string("waitpid: ")
            + std::strerror(errno));
}

void terminateChild(pid_t child, int &status)
{
    if (::kill(-child, SIGKILL) == -1 && errno != ESRCH)
        ::kill(child, SIGKILL);
    waitForChild(child, status);
}

bool collectChild(pid_t child, int &status)
{
    pid_t result;
    do
    {
        result = ::waitpid(child, &status, WNOHANG);
    }
    while (result == -1 && errno == EINTR);
    if (result == child)
        return true;
    if (result == -1)
        throw std::runtime_error(std::string("waitpid: ")
            + std::strerror(errno));
    return false;
}

void duplicateOrExit(int source, int target)
{
    if (::dup2(source, target) == -1)
        _exit(126);
}
}

CgiResult CgiRunner::run(
    const std::string &executable,
    const std::string &input,
    int timeoutMs,
    std::size_t maxOutputBytes) const
{
    int inputPipe[2];
    if (::pipe(inputPipe) == -1)
        throw std::runtime_error(std::string("pipe: ")
            + std::strerror(errno));
    ScopedFd childInputRead(inputPipe[0]);
    ScopedFd parentInputWrite(inputPipe[1]);

    int outputPipe[2];
    if (::pipe(outputPipe) == -1)
        throw std::runtime_error(std::string("pipe: ")
            + std::strerror(errno));
    ScopedFd parentOutputRead(outputPipe[0]);
    ScopedFd childOutputWrite(outputPipe[1]);

    const pid_t child = ::fork();
    if (child == -1)
        throw std::runtime_error(std::string("fork: ")
            + std::strerror(errno));
    if (child == 0)
    {
        ::setpgid(0, 0);
        duplicateOrExit(childInputRead.get(), STDIN_FILENO);
        duplicateOrExit(childOutputWrite.get(), STDOUT_FILENO);
        childInputRead.reset();
        parentInputWrite.reset();
        parentOutputRead.reset();
        childOutputWrite.reset();

        char *arguments[2];
        arguments[0] = const_cast<char *>(executable.c_str());
        arguments[1] = 0;
        ::execve(arguments[0], arguments, environ);
        _exit(127);
    }

    if (::setpgid(child, child) == -1
        && errno != EACCES
        && errno != ESRCH)
    {
        int ignoredStatus = 0;
        terminateChild(child, ignoredStatus);
        throw std::runtime_error(std::string("setpgid: ")
            + std::strerror(errno));
    }

    childInputRead.reset();
    childOutputWrite.reset();
    setNonblocking(parentInputWrite.get());
    setNonblocking(parentOutputRead.get());

    CgiResult result;
    std::size_t writeOffset = 0;
    bool outputOpen = true;
    bool childDone = false;
    int childStatus = 0;
    timeval started;
    if (::gettimeofday(&started, 0) == -1)
    {
        terminateChild(child, childStatus);
        throw std::runtime_error("gettimeofday");
    }

    try
    {
        while (outputOpen || !childDone)
        {
            if (parentInputWrite.valid()
                && writeOffset == input.size())
            {
                parentInputWrite.reset();
            }

            const long remaining
                = timeoutMs - elapsedMilliseconds(started);
            if (remaining <= 0)
            {
                terminateChild(child, childStatus);
                result.outcome = CgiResult::TimedOut;
                return result;
            }

            pollfd pollFds[2];
            nfds_t count = 0;
            int inputIndex = -1;
            int outputIndex = -1;
            if (parentInputWrite.valid())
            {
                inputIndex = static_cast<int>(count);
                pollFds[count].fd = parentInputWrite.get();
                pollFds[count].events = POLLOUT;
                pollFds[count].revents = 0;
                ++count;
            }
            if (outputOpen)
            {
                outputIndex = static_cast<int>(count);
                pollFds[count].fd = parentOutputRead.get();
                pollFds[count].events = POLLIN;
                pollFds[count].revents = 0;
                ++count;
            }

            const int pollTimeout = remaining < 50
                ? static_cast<int>(remaining)
                : 50;
            int ready;
            do
            {
                ready = ::poll(pollFds, count, pollTimeout);
            }
            while (ready == -1 && errno == EINTR);
            if (ready == -1)
                throw std::runtime_error(std::string("poll: ")
                    + std::strerror(errno));

            if (inputIndex != -1)
            {
                const short events = pollFds[inputIndex].revents;
                if (events & POLLOUT)
                {
                    const ssize_t written = ::write(
                        parentInputWrite.get(),
                        input.data() + writeOffset,
                        input.size() - writeOffset);
                    if (written > 0)
                        writeOffset += static_cast<std::size_t>(written);
                    else if (written == -1
                        && errno != EAGAIN
                        && errno != EWOULDBLOCK
                        && errno != EINTR)
                        parentInputWrite.reset();
                }
                if (events & (POLLERR | POLLHUP | POLLNVAL))
                    parentInputWrite.reset();
            }

            if (outputIndex != -1)
            {
                const short events = pollFds[outputIndex].revents;
                if (events & (POLLIN | POLLHUP))
                {
                    char buffer[4096];
                    for (;;)
                    {
                        const ssize_t received = ::read(
                            parentOutputRead.get(),
                            buffer,
                            sizeof(buffer));
                        if (received > 0)
                        {
                            result.output.append(
                                buffer,
                                static_cast<std::size_t>(received));
                            if (result.output.size() > maxOutputBytes)
                            {
                                terminateChild(child, childStatus);
                                result.output.clear();
                                result.outcome = CgiResult::OutputLimit;
                                return result;
                            }
                        }
                        else if (received == 0)
                        {
                            parentOutputRead.reset();
                            outputOpen = false;
                            break;
                        }
                        else if (errno == EINTR)
                            continue;
                        else if (errno == EAGAIN || errno == EWOULDBLOCK)
                            break;
                        else
                            throw std::runtime_error(std::string("read: ")
                                + std::strerror(errno));
                    }
                }
                if (events & (POLLERR | POLLNVAL))
                    throw std::runtime_error(
                        "자식 프로세스의 출력 파이프를 읽지 못했습니다");
            }

            if (!childDone)
                childDone = collectChild(child, childStatus);
        }
    }
    catch (...)
    {
        if (!childDone)
            terminateChild(child, childStatus);
        throw;
    }

    if (!WIFEXITED(childStatus))
    {
        result.outcome = CgiResult::Failed;
        return result;
    }
    result.exitCode = WEXITSTATUS(childStatus);
    result.outcome = result.exitCode == 0
        ? CgiResult::Success
        : CgiResult::Failed;
    return result;
}
