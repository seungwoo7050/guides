#include <arpa/inet.h>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc != 2)
        return 1;

    int listener = -1;
    int client = -1;
    try
    {
        listener = ::socket(AF_INET, SOCK_STREAM, 0);
        if (listener == -1)
            throw std::runtime_error("socket");

        sockaddr_in address;
        std::memset(&address, 0, sizeof(address));
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        address.sin_port = htons(
            static_cast<unsigned short>(std::atoi(argv[1])));

        if (::bind(
                listener,
                reinterpret_cast<sockaddr *>(&address),
                sizeof(address)) == -1
            || ::listen(listener, 8) == -1)
        {
            throw std::runtime_error("bind/listen");
        }

        sockaddr_in actual;
        socklen_t length = sizeof(actual);
        if (::getsockname(
                listener,
                reinterpret_cast<sockaddr *>(&actual),
                &length) == -1)
        {
            throw std::runtime_error("getsockname");
        }
        std::cout << "PORT " << ntohs(actual.sin_port) << std::endl;

        client = ::accept(listener, 0, 0);
        if (client == -1)
            throw std::runtime_error("accept");

        char buffer[4096];
        ::recv(client, buffer, sizeof(buffer), 0);

        const std::string response
            = "HTTP/1.1 500 Internal Server Error\r\n"
              "Content-Length: 5\r\n"
              "Connection: close\r\n\r\nTODO\n";
        ::send(client, response.data(), response.size(), 0);

        // TODO: 증분 파서, poll 루프, 출력 버퍼와 연결 유지를 구현하세요.
        ::close(client);
        ::close(listener);
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << "http_server: " << error.what() << '\n';
        if (client != -1)
            ::close(client);
        if (listener != -1)
            ::close(listener);
        return 1;
    }
}
