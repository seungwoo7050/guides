#ifndef HTTPPARSER_HPP
#define HTTPPARSER_HPP

#include <cstddef>
#include <map>
#include <string>

// [Implementation 1] 선행 단계의 증분 parser 계약을 통합 server의 독립 protocol module로 유지합니다.
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
