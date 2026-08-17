#include "CgiRunner.hpp"
#include "HttpParser.hpp"
#include "Router.hpp"

#include <arpa/inet.h>
#include <cerrno>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <fstream>
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
const std::size_t MaxCgiOutput = 1024 * 1024;
const std::size_t MaxPendingOutput = MaxCgiOutput + 16384;
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

void setNonblockingAndCloseOnExec(int fd)
{
    const int statusFlags = ::fcntl(fd, F_GETFL, 0);
    if (statusFlags == -1 ||
        ::fcntl(fd, F_SETFL, statusFlags | O_NONBLOCK) == -1)
    {
        throw std::runtime_error("fcntl O_NONBLOCK");
    }

    const int descriptorFlags = ::fcntl(fd, F_GETFD, 0);
    if (descriptorFlags == -1 ||
        ::fcntl(fd, F_SETFD, descriptorFlags | FD_CLOEXEC) == -1)
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
        if (::setsockopt(fd, SOL_SOCKET, SO_REUSEADDR,
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
        if (::bind(fd, reinterpret_cast<sockaddr *>(&address),
                   sizeof(address)) == -1)
        {
            throw std::runtime_error(std::string("bind: ") + std::strerror(errno));
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
    if (::getsockname(fd, reinterpret_cast<sockaddr *>(&address), &length) == -1)
        throw std::runtime_error("getsockname");
    return ntohs(address.sin_port);
}

// [Implementation 4] Validated server startup
// CLI values, configuration, and listener startup are validated before the event loop begins.
long parseLong(const char *text, long minimum, long maximum, const char *label)
{
    char *end = 0;
    errno = 0;
    const long value = std::strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' ||
        value < minimum || value > maximum)
    {
        throw std::invalid_argument(std::string(label) + " is out of range");
    }
    return value;
}

std::string readTextFile(const char *path)
{
    std::ifstream input(path);
    if (!input)
        throw std::runtime_error(std::string("cannot open configuration: ") + path);
    std::ostringstream text;
    text << input.rdbuf();
    if (input.bad())
        throw std::runtime_error(std::string("cannot read configuration: ") + path);
    return text.str();
}

ssize_t sendWithoutSigpipe(int fd, const char *data, std::size_t size)
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

// [Implementation 5] HTTP response mapping
// Route and CGI outcomes become status/body values before wire serialization.
std::string reasonPhrase(int status)
{
    switch (status)
    {
    case 200: return "OK";
    case 201: return "Created";
    case 202: return "Accepted";
    case 204: return "No Content";
    case 400: return "Bad Request";
    case 404: return "Not Found";
    case 502: return "Bad Gateway";
    case 504: return "Gateway Timeout";
    default: return "Response";
    }
}

std::string serializeResponse(int status, const std::string &body, bool keepAlive)
{
    std::ostringstream output;
    output << "HTTP/1.1 " << status << ' ' << reasonPhrase(status)
           << "\r\nContent-Length: " << body.size()
           << "\r\nContent-Type: text/plain"
           << "\r\nConnection: " << (keepAlive ? "keep-alive" : "close")
           << "\r\n\r\n" << body;
    return output.str();
}

bool requestKeepsConnection(const HttpRequest &request)
{
    const std::map<std::string, std::string>::const_iterator connection =
        request.headers.find("connection");
    const std::string value = connection == request.headers.end()
        ? ""
        : lowercase(connection->second);
    if (request.version == "HTTP/1.1")
        return value != "close";
    return value == "keep-alive";
}

struct DispatchResult
{
    int status;
    std::string body;

    DispatchResult(int responseStatus, const std::string &responseBody)
        : status(responseStatus), body(responseBody)
    {
    }
};

DispatchResult parseCgiOutput(const CgiResult &cgi)
{
    if (cgi.outcome == CgiResult::TimedOut)
        return DispatchResult(504, "CGI execution timed out\n");
    if (cgi.outcome == CgiResult::OutputLimit)
        return DispatchResult(502, "CGI output limit exceeded\n");
    if (cgi.outcome != CgiResult::Success)
        return DispatchResult(502, "CGI process failed\n");

    const std::size_t separator = cgi.output.find("\r\n\r\n");
    if (separator == std::string::npos)
        return DispatchResult(502, "invalid CGI response headers\n");

    int status = 200;
    const std::string headers = cgi.output.substr(0, separator);
    std::istringstream lines(headers);
    std::string line;
    while (std::getline(lines, line))
    {
        if (!line.empty() && line[line.size() - 1] == '\r')
            line.erase(line.size() - 1);
        if (line.compare(0, 8, "Status: ") == 0)
        {
            const std::string value = line.substr(8);
            char *end = 0;
            errno = 0;
            const long parsed = std::strtol(value.c_str(), &end, 10);
            if (errno != 0 || end == value.c_str() ||
                (*end != '\0' && *end != ' ') || parsed < 100 || parsed > 599)
            {
                return DispatchResult(502, "invalid CGI Status header\n");
            }
            status = static_cast<int>(parsed);
        }
    }
    return DispatchResult(status, cgi.output.substr(separator + 4));
}

// [Implementation 6] Connection ownership
// Connection owns the socket, parser, shared dispatch dependencies, and response lifecycle.
class Connection
{
public:
    Connection(int fd, const Router &router, const std::string &cgiExecutable,
               int cgiTimeoutMs)
        : fd_(fd), parser_(), output_(), writeOffset_(0),
          closeAfterWrite_(false), dead_(false), router_(router),
          cgiExecutable_(cgiExecutable), cgiTimeoutMs_(cgiTimeoutMs), cgiRunner_()
    {
    }

    ~Connection()
    {
        if (fd_ != -1)
            ::close(fd_);
    }

    int fd() const { return fd_; }
    bool wantsWrite() const { return writeOffset_ < output_.size(); }
    bool closeAfterWrite() const { return closeAfterWrite_; }
    bool dead() const { return dead_; }
    void markDead() { dead_ = true; }

    void requestCloseAfterWrite()
    {
        closeAfterWrite_ = true;
        if (!wantsWrite())
            dead_ = true;
    }

    void readReady()
    {
        char buffer[4096];
        for (;;)
        {
            const ssize_t received = ::recv(fd_, buffer, sizeof(buffer), 0);
            if (received > 0)
            {
                processParserResult(
                    parser_.feed(buffer, static_cast<std::size_t>(received)));
                if (dead_ || closeAfterWrite_)
                    return;
            }
            else if (received == 0)
            {
                requestCloseAfterWrite();
                return;
            }
            else if (errno == EINTR)
                continue;
            else if (errno == EAGAIN || errno == EWOULDBLOCK)
                return;
            else
            {
                dead_ = true;
                return;
            }
        }
    }

    // [Implementation 6-3] Partial output lifecycle
    // Partial sends, output compaction, the queue cap, and close-after-write stay coordinated.
    void writeReady()
    {
        while (writeOffset_ < output_.size())
        {
            const ssize_t sent = sendWithoutSigpipe(
                fd_, output_.data() + writeOffset_, output_.size() - writeOffset_);
            if (sent > 0)
                writeOffset_ += static_cast<std::size_t>(sent);
            else if (sent == -1 && errno == EINTR)
                continue;
            else if (sent == -1 && (errno == EAGAIN || errno == EWOULDBLOCK))
                return;
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
    const Router &router_;
    std::string cgiExecutable_;
    int cgiTimeoutMs_;
    CgiRunner cgiRunner_;

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
        if (pending > MaxPendingOutput || message.size() > MaxPendingOutput - pending)
        {
            dead_ = true;
            return false;
        }
        output_.append(message);
        return true;
    }

    // [Implementation 6-1] Handler dispatch
    // Handler names resolve to health, echo, or CGI execution with normalized results.
    DispatchResult dispatch(const HttpRequest &request)
    {
        std::string handler;
        if (!router_.resolve(request.method, request.target, handler))
            return DispatchResult(404, "not found\n");
        if (handler == "health")
            return DispatchResult(200, "ok\n");
        if (handler == "echo")
            return DispatchResult(200, request.body);
        if (handler == "cgi")
        {
            return parseCgiOutput(cgiRunner_.run(
                cgiExecutable_, request.body, cgiTimeoutMs_, MaxCgiOutput));
        }
        return DispatchResult(500, "invalid router state\n");
    }

    // [Implementation 6-2] Parser, pipeline, and keep-alive integration
    // Completed parser state drives dispatch, pipelining, keep-alive, and error closure.
    void processParserResult(HttpParser::Result result)
    {
        while (result == HttpParser::Complete && !dead_)
        {
            const HttpRequest request = parser_.take();
            const DispatchResult response = dispatch(request);
            const bool keepAlive = requestKeepsConnection(request);
            if (!queue(serializeResponse(response.status, response.body, keepAlive)))
                return;
            if (!keepAlive)
            {
                closeAfterWrite_ = true;
                return;
            }
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

// [Implementation 7] Accepted connection transaction
// Accepted descriptor ownership transfers only after socket setup and map insertion succeed.
void acceptAll(int listener, ConnectionMap &connections, const Router &router,
               const std::string &cgiExecutable, int cgiTimeoutMs)
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
            throw std::runtime_error(std::string("accept: ") + std::strerror(errno));
        }

        Connection *connection = 0;
        try
        {
            setNonblockingAndCloseOnExec(fd);
            connection = new Connection(fd, router, cgiExecutable, cgiTimeoutMs);
            const std::pair<ConnectionMap::iterator, bool> inserted =
                connections.insert(std::make_pair(fd, connection));
            if (!inserted.second)
                throw std::logic_error("duplicate connection descriptor");
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

void closeListener(int &listener)
{
    if (listener != -1)
    {
        ::close(listener);
        listener = -1;
    }
}
} // namespace

// [Implementation 8] Poll-loop composition and shutdown
// Startup, the poll loop, typed exits, signal shutdown, and descriptor cleanup form one process boundary.
int main(int argc, char **argv)
{
    if (argc != 5)
    {
        std::cerr << "usage: http_server port routes.conf cgi-executable timeout-ms\n";
        return 2;
    }

    std::signal(SIGPIPE, SIG_IGN);
    int listener = -1;
    ConnectionMap connections;

    try
    {
        const int port = static_cast<int>(parseLong(argv[1], 0, 65535, "port"));
        const int timeoutMs = static_cast<int>(
            parseLong(argv[4], 1, 600000, "timeout"));
        const std::vector<RouteSpec> specs =
            ConfigParser().parse(readTextFile(argv[2]));
        const Router router(specs);
        const std::string cgiExecutable(argv[3]);

        installSignalHandler(SIGTERM);
        installSignalHandler(SIGINT);
        listener = makeListener(port);
        std::cout << "PORT " << actualPort(listener) << std::endl;

        while (!stopRequested)
        {
            std::vector<pollfd> pollFds;
            pollFds.reserve(connections.size() + 1);

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
                clientPoll.revents = 0;
                if (!it->second->closeAfterWrite())
                    clientPoll.events |= POLLIN;
                if (it->second->wantsWrite())
                    clientPoll.events |= POLLOUT;
                pollFds.push_back(clientPoll);
            }

            int ready;
            do
            {
                ready = ::poll(&pollFds[0], pollFds.size(), 100);
            }
            while (ready == -1 && errno == EINTR && !stopRequested);
            if (ready == -1 && errno == EINTR && stopRequested)
                break;
            if (ready == -1)
                throw std::runtime_error(std::string("poll: ") + std::strerror(errno));
            if (ready == 0)
                continue;

            std::set<int> closing;
            if (pollFds[0].revents & POLLIN)
                acceptAll(listener, connections, router, cgiExecutable, timeoutMs);
            if (pollFds[0].revents & (POLLERR | POLLHUP | POLLNVAL))
                throw std::runtime_error("listener poll failure");

            for (std::size_t i = 1; i < pollFds.size(); ++i)
            {
                ConnectionMap::iterator found = connections.find(pollFds[i].fd);
                if (found == connections.end())
                    continue;
                Connection *connection = found->second;
                const short events = pollFds[i].revents;

                if ((events & POLLIN) && !connection->closeAfterWrite())
                    connection->readReady();
                if ((events & POLLOUT) && !connection->dead())
                    connection->writeReady();
                if (events & (POLLERR | POLLNVAL))
                    connection->markDead();
                else if (events & POLLHUP)
                    connection->requestCloseAfterWrite();

                if (connection->dead())
                    closing.insert(connection->fd());
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
        closeListener(listener);
        return 0;
    }
    catch (const ConfigError &error)
    {
        std::cerr << "configuration error: " << error.what() << '\n';
        destroyConnections(connections);
        closeListener(listener);
        return 2;
    }
    catch (const std::invalid_argument &error)
    {
        std::cerr << "argument error: " << error.what() << '\n';
        destroyConnections(connections);
        closeListener(listener);
        return 2;
    }
    catch (const std::exception &error)
    {
        std::cerr << "fatal: " << error.what() << '\n';
        destroyConnections(connections);
        closeListener(listener);
        return 1;
    }
}
