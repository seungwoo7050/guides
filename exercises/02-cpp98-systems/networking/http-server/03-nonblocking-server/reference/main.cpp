#include "HttpParser.hpp"

#include <arpa/inet.h>
#include <cerrno>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <map>
#include <poll.h>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <unistd.h>
#include <utility>
#include <vector>

namespace
{
const std::size_t MaxPendingOutput = 65536;
volatile sig_atomic_t stopRequested = 0;

void onSignal(int)
{
    stopRequested = 1;
}

void installSignalHandler(int signalNumber)
{
    struct sigaction action;
    std::memset(&action, 0, sizeof(action));
    action.sa_handler = onSignal;
    sigemptyset(&action.sa_mask);
    action.sa_flags = 0;
    if (::sigaction(signalNumber, &action, 0) == -1)
        throw std::runtime_error("sigaction");
}

// [Implementation 2] signal, listener와 accepted fd의 nonblocking/CLOEXEC 초기화 및 실패 cleanup 경계를 세웁니다.
void setNonblockingAndCloseOnExec(int fd)
{
    const int statusFlags = ::fcntl(fd, F_GETFL, 0);
    if (statusFlags == -1
        || ::fcntl(fd, F_SETFL, statusFlags | O_NONBLOCK) == -1)
    {
        throw std::runtime_error("fcntl O_NONBLOCK");
    }

    const int descriptorFlags = ::fcntl(fd, F_GETFD, 0);
    if (descriptorFlags == -1
        || ::fcntl(fd, F_SETFD, descriptorFlags | FD_CLOEXEC) == -1)
    {
        throw std::runtime_error("fcntl FD_CLOEXEC");
    }
}

int makeListener(int port)
{
    const int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (fd == -1)
        throw std::runtime_error("socket");

    try
    {
        const int enabled = 1;
        if (::setsockopt(
                fd, SOL_SOCKET, SO_REUSEADDR,
                &enabled, sizeof(enabled)) == -1)
        {
            throw std::runtime_error("setsockopt SO_REUSEADDR");
        }

        setNonblockingAndCloseOnExec(fd);

        sockaddr_in address;
        std::memset(&address, 0, sizeof(address));
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        address.sin_port = htons(static_cast<unsigned short>(port));

        if (::bind(
                fd,
                reinterpret_cast<sockaddr *>(&address),
                sizeof(address)) == -1)
        {
            throw std::runtime_error(
                std::string("bind: ") + std::strerror(errno));
        }
        if (::listen(fd, 64) == -1)
            throw std::runtime_error("listen");
        return fd;
    }
    catch (...)
    {
        ::close(fd);
        throw;
    }
}

int actualPort(int fd)
{
    sockaddr_in address;
    socklen_t length = sizeof(address);
    if (::getsockname(
            fd,
            reinterpret_cast<sockaddr *>(&address),
            &length) == -1)
    {
        throw std::runtime_error("getsockname");
    }
    return ntohs(address.sin_port);
}

ssize_t sendWithoutSigpipe(
    int fd,
    const char *data,
    std::size_t size)
{
#ifdef MSG_NOSIGNAL
    return ::send(fd, data, size, MSG_NOSIGNAL);
#else
    return ::send(fd, data, size, 0);
#endif
}

std::string lowercase(std::string text)
{
    for (std::size_t i = 0; i < text.size(); ++i)
    {
        if (text[i] >= 'A' && text[i] <= 'Z')
            text[i] = static_cast<char>(text[i] - 'A' + 'a');
    }
    return text;
}

// [Implementation 3] route 결과와 connection policy를 wire-level HTTP 응답으로 직렬화하는 순수 계층을 만듭니다.
std::string reasonPhrase(int status)
{
    switch (status)
    {
    case 200:
        return "OK";
    case 204:
        return "No Content";
    case 400:
        return "Bad Request";
    case 404:
        return "Not Found";
    default:
        return "Internal Server Error";
    }
}

std::string serializeResponse(
    int status,
    const std::string &body,
    bool keepAlive)
{
    std::ostringstream output;
    output << "HTTP/1.1 " << status << ' ' << reasonPhrase(status)
           << "\r\nContent-Length: " << body.size()
           << "\r\nContent-Type: text/plain"
           << "\r\nConnection: "
           << (keepAlive ? "keep-alive" : "close")
           << "\r\n\r\n"
           << body;
    return output.str();
}

bool requestKeepsConnection(const HttpRequest &request)
{
    const std::map<std::string, std::string>::const_iterator connection
        = request.headers.find("connection");
    const std::string value = connection == request.headers.end()
        ? ""
        : lowercase(connection->second);

    if (request.version == "HTTP/1.1")
        return value != "close";
    return value == "keep-alive";
}

std::string dispatch(const HttpRequest &request, int &status)
{
    if (request.method == "GET" && request.target == "/health")
    {
        status = 200;
        return "ok\n";
    }
    if (request.method == "GET" && request.target == "/")
    {
        status = 200;
        return "hello\n";
    }
    if (request.method == "POST" && request.target == "/echo")
    {
        status = 200;
        return request.body;
    }
    if (request.method == "DELETE" && request.target == "/resource")
    {
        status = 204;
        return "";
    }

    status = 404;
    return "찾을 수 없습니다\n";
}

// [Implementation 4] Connection이 client fd, parser, pending output와 close/dead lifecycle의 단일 owner가 됩니다.
class Connection
{
public:
    explicit Connection(int fd)
        : fd_(fd),
          parser_(),
          output_(),
          writeOffset_(0),
          closeAfterWrite_(false),
          dead_(false)
    {
    }

    ~Connection()
    {
        if (fd_ != -1)
            ::close(fd_);
    }

    int fd() const
    {
        return fd_;
    }

    bool wantsWrite() const
    {
        return writeOffset_ < output_.size();
    }

    bool closeAfterWrite() const
    {
        return closeAfterWrite_;
    }

    bool dead() const
    {
        return dead_;
    }

    void markDead()
    {
        dead_ = true;
    }

    void requestCloseAfterWrite()
    {
        closeAfterWrite_ = true;
        if (!wantsWrite())
            dead_ = true;
    }

    // [Implementation 4-1] recv 조각을 parser에 공급해 완성된 요청만 dispatch하고 pipeline과 keep-alive 상태를 이어 갑니다.
    void readReady()
    {
        char buffer[4096];
        for (;;)
        {
            const ssize_t received = ::recv(fd_, buffer, sizeof(buffer), 0);
            if (received > 0)
            {
                processParserResult(parser_.feed(
                    buffer, static_cast<std::size_t>(received)));
                if (dead_ || closeAfterWrite_)
                    return;
            }
            else if (received == 0)
            {
                requestCloseAfterWrite();
                return;
            }
            else if (errno == EINTR)
            {
                continue;
            }
            else if (errno == EAGAIN || errno == EWOULDBLOCK)
            {
                return;
            }
            else
            {
                dead_ = true;
                return;
            }
        }
    }

    // [Implementation 4-2] partial send offset과 output 상한을 관리해 write readiness와 close-after-write를 결정합니다.
    void writeReady()
    {
        while (writeOffset_ < output_.size())
        {
            const ssize_t sent = sendWithoutSigpipe(
                fd_,
                output_.data() + writeOffset_,
                output_.size() - writeOffset_);

            if (sent > 0)
            {
                writeOffset_ += static_cast<std::size_t>(sent);
            }
            else if (sent == -1 && errno == EINTR)
            {
                continue;
            }
            else if (sent == -1
                && (errno == EAGAIN || errno == EWOULDBLOCK))
            {
                return;
            }
            else
            {
                dead_ = true;
                return;
            }
        }

        output_.clear();
        writeOffset_ = 0;
        if (closeAfterWrite_)
            dead_ = true;
    }

private:
    int fd_;
    HttpParser parser_;
    std::string output_;
    std::size_t writeOffset_;
    bool closeAfterWrite_;
    bool dead_;

    std::size_t pendingOutput() const
    {
        return output_.size() - writeOffset_;
    }

    bool queue(const std::string &message)
    {
        if (writeOffset_ > 32768)
        {
            output_.erase(0, writeOffset_);
            writeOffset_ = 0;
        }

        const std::size_t pending = pendingOutput();
        if (message.size() > MaxPendingOutput - pending)
        {
            dead_ = true;
            return false;
        }

        output_.append(message);
        return true;
    }

    void processParserResult(HttpParser::Result result)
    {
        while (result == HttpParser::Complete && !dead_)
        {
            const HttpRequest request = parser_.take();
            int status = 500;
            const std::string body = dispatch(request, status);
            const bool keepAlive = requestKeepsConnection(request);

            if (!queue(serializeResponse(status, body, keepAlive)))
                return;
            if (!keepAlive)
            {
                closeAfterWrite_ = true;
                return;
            }

            // 버퍼에 이미 들어온 다음 파이프라인 요청을 확인합니다.
            result = parser_.feed("", 0);
        }

        if (result == HttpParser::Error)
        {
            if (queue(serializeResponse(400, "bad request\n", false)))
                closeAfterWrite_ = true;
        }
    }
};

typedef std::map<int, Connection *> ConnectionMap;

// [Implementation 5] accepted fd의 설정과 Connection 생성을 완료한 뒤 map으로 소유권을 넘기며 실패는 역순 정리합니다.
void acceptAll(int listener, ConnectionMap &connections)
{
    for (;;)
    {
        const int fd = ::accept(listener, 0, 0);
        if (fd == -1)
        {
            if (errno == EINTR)
                continue;
            if (errno == EAGAIN || errno == EWOULDBLOCK)
                return;
            throw std::runtime_error("accept");
        }

        Connection *connection = 0;
        try
        {
            setNonblockingAndCloseOnExec(fd);
            connection = new Connection(fd);
            const std::pair<ConnectionMap::iterator, bool> inserted
                = connections.insert(std::make_pair(fd, connection));
            if (!inserted.second)
                throw std::logic_error("연결 파일 디스크립터가 중복되었습니다");
            connection = 0;
        }
        catch (...)
        {
            if (connection != 0)
                delete connection;
            else
                ::close(fd);
            throw;
        }
    }
}

void destroyConnections(ConnectionMap &connections)
{
    while (!connections.empty())
    {
        ConnectionMap::iterator current = connections.begin();
        Connection *connection = current->second;
        connections.erase(current);
        delete connection;
    }
}
}

// [Implementation 6] poll interest를 connection 상태에서 재구성하고 event·signal·오류 종료마다 모든 socket을 회수합니다.
int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cerr << "사용법: http_server 포트\n";
        return 1;
    }

    std::signal(SIGPIPE, SIG_IGN);
    int listener = -1;
    ConnectionMap connections;

    try
    {
        installSignalHandler(SIGTERM);
        installSignalHandler(SIGINT);

        listener = makeListener(std::atoi(argv[1]));
        std::cout << "PORT " << actualPort(listener) << std::endl;

        while (!stopRequested)
        {
            std::vector<pollfd> pollFds;
            pollfd listenerPoll;
            listenerPoll.fd = listener;
            listenerPoll.events = POLLIN;
            listenerPoll.revents = 0;
            pollFds.push_back(listenerPoll);

            for (ConnectionMap::const_iterator it = connections.begin();
                 it != connections.end(); ++it)
            {
                pollfd clientPoll;
                clientPoll.fd = it->first;
                clientPoll.events = 0;
                if (!it->second->closeAfterWrite())
                    clientPoll.events |= POLLIN;
                if (it->second->wantsWrite())
                    clientPoll.events |= POLLOUT;
                clientPoll.revents = 0;
                pollFds.push_back(clientPoll);
            }

            int ready;
            do
            {
                ready = ::poll(&pollFds[0], pollFds.size(), 100);
            }
            while (ready == -1 && errno == EINTR && !stopRequested);

            if (ready == -1)
            {
                if (errno == EINTR && stopRequested)
                    break;
                throw std::runtime_error("poll");
            }
            if (stopRequested)
                break;

            if (pollFds[0].revents & POLLIN)
                acceptAll(listener, connections);

            std::set<int> closing;
            for (std::size_t i = 1; i < pollFds.size(); ++i)
            {
                ConnectionMap::iterator found
                    = connections.find(pollFds[i].fd);
                if (found == connections.end())
                    continue;

                Connection *connection = found->second;
                const short events = pollFds[i].revents;

                if (events & POLLIN)
                    connection->readReady();
                if ((events & POLLOUT) && !connection->dead())
                    connection->writeReady();
                if (events & (POLLERR | POLLNVAL))
                    connection->markDead();
                else if (events & POLLHUP)
                    connection->requestCloseAfterWrite();

                if (connection->dead()
                    || (connection->closeAfterWrite()
                        && !connection->wantsWrite()))
                {
                    closing.insert(connection->fd());
                }
            }

            for (std::set<int>::const_iterator it = closing.begin();
                 it != closing.end(); ++it)
            {
                ConnectionMap::iterator found = connections.find(*it);
                if (found == connections.end())
                    continue;
                Connection *connection = found->second;
                connections.erase(found);
                delete connection;
            }
        }

        destroyConnections(connections);
        ::close(listener);
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << "치명적 오류: " << error.what() << '\n';
        destroyConnections(connections);
        if (listener != -1)
            ::close(listener);
        return 1;
    }
}
