#ifndef COMMANDSERVICE_HPP
#define COMMANDSERVICE_HPP

#include "KeyValueStore.hpp"
#include "Request.hpp"
#include "Response.hpp"

class CommandService
{
public:
    explicit CommandService(KeyValueStore &store)
        : store_(store)
    {
    }

    Response execute(const Request &request) const;

private:
    KeyValueStore &store_;
};

#endif
