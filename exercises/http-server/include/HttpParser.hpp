#ifndef HTTP_SERVER_HTTP_PARSER_HPP
#define HTTP_SERVER_HTTP_PARSER_HPP

#include <cstddef>
#include <map>
#include <string>

// [Implementation 1] Incremental HTTP request contract
// The incremental parser exposes a committed request independently from socket ownership.
struct HttpRequest
{
    std::string method;
    std::string target;
    std::string version;
    std::map<std::string, std::string> headers;
    std::string body;
};

class HttpParser
{
public:
    enum Result
    {
        NeedMore,
        Complete,
        Error
    };

    HttpParser();

    Result feed(const char *data, std::size_t size);
    Result feed(const std::string &data)
    {
        return feed(data.data(), data.size());
    }

    HttpRequest take();
    const std::string &error() const;

private:
    std::string buffer_;
    std::string error_;
    HttpRequest ready_;
    bool hasReady_;

    Result parseAvailable();
    Result fail(const std::string &message);
};

#endif
