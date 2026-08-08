#include "Handler.hpp"

std::string PutHandler::handle(
    const Request &request,
    Store &store) const
{
    static_cast<void>(request);
    static_cast<void>(store);
    // TODO: 인자 개수를 검증한 뒤 Store를 갱신하세요.
    return "BAD_REQUEST";
}

std::string GetHandler::handle(
    const Request &request,
    Store &store) const
{
    static_cast<void>(request);
    static_cast<void>(store);
    // TODO: VALUE 또는 NOT_FOUND를 반환하세요.
    return "BAD_REQUEST";
}

std::string DeleteHandler::handle(
    const Request &request,
    Store &store) const
{
    static_cast<void>(request);
    static_cast<void>(store);
    // TODO: DELETED 또는 NOT_FOUND를 반환하세요.
    return "BAD_REQUEST";
}

std::string CountHandler::handle(
    const Request &request,
    Store &store) const
{
    static_cast<void>(request);
    static_cast<void>(store);
    // TODO: Store 내부를 노출하지 않고 현재 개수를 문자열로 만드세요.
    return "BAD_REQUEST";
}

std::string QuitHandler::handle(
    const Request &request,
    Store &store) const
{
    static_cast<void>(request);
    static_cast<void>(store);
    // TODO: 인자가 없을 때만 QUIT을 허용하세요.
    return "BAD_REQUEST";
}
