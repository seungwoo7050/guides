#include "Router.hpp"

std::vector<RouteSpec> ConfigParser::parse(const std::string &text) const
{
    static_cast<void>(text);
    // TODO: 별도 후보 설정으로 파싱하고 잘못된 지시어를 거부하세요.
    return std::vector<RouteSpec>();
}

std::string Router::key(
    const std::string &method,
    const std::string &path)
{
    return method + " " + path;
}

Router::Router(const std::vector<RouteSpec> &specs)
    : routes_(), health_(0), echo_(0)
{
    static_cast<void>(specs);
    // TODO: 핸들러를 만들고 검증된 라우트를 연결하세요.
}

Router::~Router()
{
    delete health_;
    delete echo_;
}

Response Router::dispatch(const Request &request) const
{
    static_cast<void>(request);
    // TODO: 선택한 핸들러의 응답이나 404 응답을 반환하세요.
    return Response(500, "TODO\n");
}
