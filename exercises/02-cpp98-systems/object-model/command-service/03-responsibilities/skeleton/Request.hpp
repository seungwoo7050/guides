#ifndef REQUEST_HPP
#define REQUEST_HPP

#include <string>

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
