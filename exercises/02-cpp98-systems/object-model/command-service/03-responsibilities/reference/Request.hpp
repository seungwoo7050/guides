#ifndef REQUEST_HPP
#define REQUEST_HPP

#include <string>

// [Implementation 1] Request와 대응 Response를 파싱·저장·표현 책임 사이에서 전달할 도메인 message로 정의합니다.
struct Request
{
    enum Type
    {
        Put,
        Get,
        Delete,
        Count,
        Quit,
        Invalid
    };

    Type type;
    std::string key;
    std::string value;

    Request(
        Type requestType = Invalid,
        const std::string &requestKey = "",
        const std::string &requestValue = "")
        : type(requestType),
          key(requestKey),
          value(requestValue)
    {
    }
};

#endif
