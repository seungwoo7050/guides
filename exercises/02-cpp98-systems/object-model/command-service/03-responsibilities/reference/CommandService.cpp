#include "CommandService.hpp"

Response CommandService::execute(const Request &request) const
{
    std::string value;

    switch (request.type)
    {
    case Request::Put:
        return Response(
            store_.put(request.key, request.value)
                ? Response::Ok
                : Response::Full);
    case Request::Get:
        return store_.get(request.key, value)
            ? Response(Response::Value, value)
            : Response(Response::NotFound);
    case Request::Delete:
        return Response(
            store_.erase(request.key)
                ? Response::Deleted
                : Response::NotFound);
    case Request::Count:
        return Response(Response::Count, "", store_.size());
    case Request::Quit:
        return Response(Response::Bye);
    default:
        return Response(Response::BadRequest);
    }
}
