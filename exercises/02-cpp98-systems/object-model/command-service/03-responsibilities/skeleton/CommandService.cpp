#include "CommandService.hpp"

Response CommandService::execute(const Request &request) const
{
    static_cast<void>(request);
    static_cast<void>(store_);
    // TODO: 각 유효한 명령을 KeyValueStore에 위임하세요.
    return Response(Response::BadRequest);
}
