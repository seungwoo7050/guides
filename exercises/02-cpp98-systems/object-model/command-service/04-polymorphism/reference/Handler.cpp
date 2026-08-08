#include "Handler.hpp"

#include <sstream>

std::string PutHandler::handle(
    const Request &request,
    Store &store) const
{
    if (request.args.size() != 2)
        return "BAD_REQUEST";

    store.put(request.args[0], request.args[1]);
    return "OK";
}

std::string GetHandler::handle(
    const Request &request,
    Store &store) const
{
    if (request.args.size() != 1)
        return "BAD_REQUEST";

    std::string value;
    return store.get(request.args[0], value)
        ? "VALUE " + value
        : "NOT_FOUND";
}

std::string DeleteHandler::handle(
    const Request &request,
    Store &store) const
{
    if (request.args.size() != 1)
        return "BAD_REQUEST";

    return store.erase(request.args[0])
        ? "DELETED"
        : "NOT_FOUND";
}

std::string CountHandler::handle(
    const Request &request,
    Store &store) const
{
    if (!request.args.empty())
        return "BAD_REQUEST";

    std::ostringstream output;
    output << "COUNT " << store.size();
    return output.str();
}

std::string QuitHandler::handle(
    const Request &request,
    Store &store) const
{
    static_cast<void>(store);
    return request.args.empty() ? "BYE" : "BAD_REQUEST";
}
