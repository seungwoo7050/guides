#ifndef COMMAND_SERVICE_RESPONSE_HPP
#define COMMAND_SERVICE_RESPONSE_HPP

#include "Store.hpp"

#include <cstddef>
#include <string>
#include <vector>

// [Implementation 5] Structured response model
// Response carries protocol meaning without coupling handlers to wire formatting.
struct Response
{
    enum Code
    {
        Ok,
        Value,
        Deleted,
        NotFound,
        Count,
        Listing,
        Bye
    };

    Code code;
    std::string value;
    std::size_t count;
    std::vector<StoreEntry> entries;

    explicit Response(Code responseCode)
        : code(responseCode), value(), count(0), entries()
    {
    }
};

#endif
