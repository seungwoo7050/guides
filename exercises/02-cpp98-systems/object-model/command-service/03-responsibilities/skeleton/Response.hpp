#ifndef RESPONSE_HPP
#define RESPONSE_HPP

#include <cstddef>
#include <string>

struct Response
{
    enum Code
    {
        Ok,
        Value,
        Full,
        Deleted,
        NotFound,
        Count,
        Bye,
        BadRequest
    };

    Code code;
    std::string value;
    std::size_t count;

    explicit Response(
        Code responseCode,
        const std::string &responseValue = "",
        std::size_t responseCount = 0)
        : code(responseCode),
          value(responseValue),
          count(responseCount)
    {
    }
};

#endif
