#include <arpa/inet.h>
#include <cerrno>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <unistd.h>

namespace
{
ssize_t sendWithoutSigpipe(int fd, const char *data, std::size_t size)
{
#ifdef MSG_NOSIGNAL
    return ::send(fd, data, size, MSG_NOSIGNAL);
#else
    return ::send(fd, data, size, 0);
#endif
}

bool sendAll(int fd, const std::string &message)
{
    std::size_t offset = 0;
    while (offset < message.size())
    {
        const ssize_t sent = sendWithoutSigpipe(
            fd, message.data() + offset, message.size() - offset);
        if (sent > 0)
            offset += static_cast<std::size_t>(sent);
        else if (sent == -1 && errno == EINTR)
            continue;
        else
            return false;
    }
    return true;
}

int makeListener(int port)
{
    const int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (fd == -1)
        throw std::runtime_error("socket");

    const int enabled = 1;
    ::setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &enabled, sizeof(enabled));

    sockaddr_in address;
    std::memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = htons(static_cast<unsigned short>(port));

    if (::bind(fd, reinterpret_cast<sockaddr *>(&address), sizeof(address)) == -1
        || ::listen(fd, 8) == -1)
    {
        ::close(fd);
        throw std::runtime_error("bind/listen");
    }
    return fd;
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
}

int main(int argc, char **argv)
{
    if (argc != 2)
        return 1;

    std::signal(SIGPIPE, SIG_IGN);
    int listener = -1;
    int client = -1;

    try
    {
        listener = makeListener(std::atoi(argv[1]));
        std::cout << "PORT " << actualPort(listener) << std::endl;
        client = ::accept(listener, 0, 0);
        if (client == -1)
            throw std::runtime_error("accept");

        char buffer[1024];
        std::string pending;
        bool finished = false;

        while (!finished)
        {
            const ssize_t received = ::recv(client, buffer, sizeof(buffer), 0);
            if (received > 0)
            {
                pending.append(buffer, static_cast<std::size_t>(received));
                std::size_t newline;
                while ((newline = pending.find('\n')) != std::string::npos)
                {
                    std::string line = pending.substr(0, newline);
                    pending.erase(0, newline + 1);
                    if (!line.empty() && line[line.size() - 1] == '\r')
                        line.erase(line.size() - 1);

                    const std::string response = line == "QUIT"
                        ? "BYE\n"
                        : "ECHO " + line + "\n";
                    if (!sendAll(client, response))
                        throw std::runtime_error("send");
                    if (line == "QUIT")
                    {
                        finished = true;
                        break;
                    }
                }
            }
            else if (received == 0)
            {
                break;
            }
            else if (errno != EINTR)
            {
                throw std::runtime_error("recv");
            }
        }

        ::close(client);
        ::close(listener);
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << "blocking_server: " << error.what() << '\n';
        if (client != -1)
            ::close(client);
        if (listener != -1)
            ::close(listener);
        return 1;
    }
}
