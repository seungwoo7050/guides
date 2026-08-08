#include <cerrno>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <poll.h>
#include <stdexcept>
#include <string>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

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

class ChildGuard
{
public:
    explicit ChildGuard(pid_t pid)
        : pid_(pid), reaped_(false)
    {
    }

    ~ChildGuard()
    {
        if (pid_ <= 0 || reaped_)
            return;

        int status = 0;
        pid_t result;
        do
        {
            result = ::waitpid(pid_, &status, WNOHANG);
        }
        while (result == -1 && errno == EINTR);

        if (result == 0)
        {
            ::kill(pid_, SIGKILL);
            do
            {
                result = ::waitpid(pid_, &status, 0);
            }
            while (result == -1 && errno == EINTR);
        }
    }

    bool collectIfExited(int &status)
    {
        if (reaped_)
            return true;

        pid_t result;
        do
        {
            result = ::waitpid(pid_, &status, WNOHANG);
        }
        while (result == -1 && errno == EINTR);

        if (result == pid_)
        {
            reaped_ = true;
            return true;
        }
        if (result == -1)
            throw std::runtime_error(std::string("waitpid: ")
                + std::strerror(errno));
        return false;
    }

    void terminateAndWait(int &status)
    {
        if (reaped_)
            return;

        ::kill(pid_, SIGKILL);
        pid_t result;
        do
        {
            result = ::waitpid(pid_, &status, 0);
        }
        while (result == -1 && errno == EINTR);

        if (result == -1)
            throw std::runtime_error(std::string("waitpid: ")
                + std::strerror(errno));
        reaped_ = true;
    }

private:
    ChildGuard(const ChildGuard &);
    ChildGuard &operator=(const ChildGuard &);

    pid_t pid_;
    bool reaped_;
};

static long elapsedMilliseconds(const timeval &start)
{
    timeval now;
    if (::gettimeofday(&now, 0) == -1)
        throw std::runtime_error("gettimeofday");

    const long seconds
        = static_cast<long>(now.tv_sec - start.tv_sec);
    const long microseconds
        = static_cast<long>(now.tv_usec - start.tv_usec);
    return seconds * 1000 + microseconds / 1000;
}

static void setNonblocking(int fd)
{
    const int flags = ::fcntl(fd, F_GETFL, 0);
    if (flags == -1
        || ::fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1)
    {
        throw std::runtime_error(std::string("fcntl: ")
            + std::strerror(errno));
    }
}

static void duplicateOrExit(int source, int target)
{
    if (::dup2(source, target) == -1)
        _exit(126);
}

static int parsePositiveTimeout(const char *text)
{
    char *end = 0;
    errno = 0;
    const long value = std::strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0'
        || value <= 0 || value > 600000)
    {
        throw std::invalid_argument(
            "timeout must be between 1 and 600000 milliseconds");
    }
    return static_cast<int>(value);
}

int main(int argc, char **argv)
{
    if (argc != 4)
    {
        std::cerr << "사용법: cgi_runner 실행-파일 제한-시간-ms 본문\n";
        return 2;
    }

    std::signal(SIGPIPE, SIG_IGN);

    try
    {
        const int timeoutMs = parsePositiveTimeout(argv[2]);

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
            duplicateOrExit(childInputRead.get(), STDIN_FILENO);
            duplicateOrExit(childOutputWrite.get(), STDOUT_FILENO);

            childInputRead.reset();
            parentInputWrite.reset();
            parentOutputRead.reset();
            childOutputWrite.reset();

            char *arguments[2];
            arguments[0] = argv[1];
            arguments[1] = 0;
            ::execve(argv[1], arguments, environ);
            _exit(127);
        }

        ChildGuard childGuard(child);

        // 부모는 자식 표준 입력의 쓰기 끝과 자식 표준 출력의 읽기 끝만 소유합니다.
        childInputRead.reset();
        childOutputWrite.reset();
        setNonblocking(parentInputWrite.get());
        setNonblocking(parentOutputRead.get());

        const std::string input(argv[3]);
        std::string output;
        std::size_t writeOffset = 0;
        bool outputOpen = true;
        bool childDone = false;
        int childStatus = 0;

        timeval started;
        if (::gettimeofday(&started, 0) == -1)
            throw std::runtime_error("gettimeofday");

        while (outputOpen || !childDone)
        {
            if (parentInputWrite.valid()
                && writeOffset == input.size())
            {
                // EOF를 보내야 자식이 표준 입력 읽기를 끝낼 수 있습니다.
                parentInputWrite.reset();
            }

            const long remaining
                = timeoutMs - elapsedMilliseconds(started);
            if (remaining <= 0)
            {
                childGuard.terminateAndWait(childStatus);
                std::cerr << "제한 시간을 넘었습니다\n";
                return 124;
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
                    {
                        writeOffset += static_cast<std::size_t>(written);
                    }
                    else if (written == -1
                        && errno != EAGAIN
                        && errno != EWOULDBLOCK
                        && errno != EINTR)
                    {
                        parentInputWrite.reset();
                    }
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
                            output.append(
                                buffer,
                                static_cast<std::size_t>(received));
                            if (output.size() > 1024 * 1024)
                            {
                                childGuard.terminateAndWait(childStatus);
                                std::cerr << "출력 제한을 넘었습니다\n";
                                return 1;
                            }
                        }
                        else if (received == 0)
                        {
                            parentOutputRead.reset();
                            outputOpen = false;
                            break;
                        }
                        else if (errno == EINTR)
                        {
                            continue;
                        }
                        else if (errno == EAGAIN
                            || errno == EWOULDBLOCK)
                        {
                            break;
                        }
                        else
                        {
                            throw std::runtime_error(
                                std::string("read: ")
                                + std::strerror(errno));
                        }
                    }
                }

                if (events & (POLLERR | POLLNVAL))
                    throw std::runtime_error("자식 프로세스의 출력 파이프를 읽지 못했습니다");
            }

            childDone = childGuard.collectIfExited(childStatus);
        }

        std::cout << output;
        if (!WIFEXITED(childStatus))
            return 1;
        return WEXITSTATUS(childStatus);
    }
    catch (const std::exception &error)
    {
        std::cerr << "cgi_runner: " << error.what() << '\n';
        return 1;
    }
}
