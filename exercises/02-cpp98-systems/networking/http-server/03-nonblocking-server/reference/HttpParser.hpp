#ifndef HTTPPARSER_HPP
#define HTTPPARSER_HPP

#include <cstddef>
#include <map>
#include <string>

// [Implementation 1] 선행 parser 과제의 byte buffer, ready request와 sticky error 계약을 server module 경계로 가져옵니다.
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
