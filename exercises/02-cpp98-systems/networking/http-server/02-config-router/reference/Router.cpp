#include "Router.hpp"

#include <set>
#include <sstream>

namespace
{
class HealthHandler : public Handler
{
public:
    Response handle(const Request &request) const
    {
        static_cast<void>(request);
        return Response(200, "ok\n");
    }
};

class EchoHandler : public Handler
{
public:
    Response handle(const Request &request) const
    {
        return Response(200, request.body);
    }
};

std::string trim(const std::string &text)
{
    const std::size_t first = text.find_first_not_of(" \t\r\n");
    if (first == std::string::npos)
        return "";
    const std::size_t last = text.find_last_not_of(" \t\r\n");
    return text.substr(first, last - first + 1);
}

bool supportedMethod(const std::string &method)
{
    return method == "GET" || method == "POST" || method == "DELETE";
}
}

std::vector<RouteSpec> ConfigParser::parse(const std::string &text) const
{
    std::istringstream input(text);
    std::vector<RouteSpec> candidate;
    std::set<std::string> seen;
    std::string line;

    while (std::getline(input, line))
    {
        line = trim(line);
        if (line.empty() || line[0] == '#')
            continue;

        if (line[line.size() - 1] != ';')
            throw ConfigError("세미콜론이 없습니다");
        line.erase(line.size() - 1);

        std::istringstream row(line);
        std::string directive;
        std::string extra;
        RouteSpec spec;

        if (!(row >> directive >> spec.method >> spec.path >> spec.handler)
            || row >> extra
            || directive != "route")
        {
            throw ConfigError("route 지시문의 형식이 올바르지 않습니다");
        }

        if (!supportedMethod(spec.method))
            throw ConfigError("지원하지 않는 HTTP 메서드입니다");
        if (spec.path.empty() || spec.path[0] != '/')
            throw ConfigError("경로는 /로 시작해야 합니다");
        if (spec.handler != "health" && spec.handler != "echo")
            throw ConfigError("알 수 없는 처리기입니다");

        const std::string routeKey = spec.method + " " + spec.path;
        if (!seen.insert(routeKey).second)
            throw ConfigError("라우트가 중복되었습니다");

        candidate.push_back(spec);
    }

    if (candidate.empty())
        throw ConfigError("라우트가 하나도 없습니다");
    return candidate;
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
    try
    {
        health_ = new HealthHandler();
        echo_ = new EchoHandler();

        for (std::size_t i = 0; i < specs.size(); ++i)
        {
            routes_.insert(std::make_pair(
                key(specs[i].method, specs[i].path),
                specs[i].handler == "health" ? health_ : echo_));
        }
    }
    catch (...)
    {
        delete health_;
        delete echo_;
        health_ = 0;
        echo_ = 0;
        throw;
    }
}

Router::~Router()
{
    delete health_;
    delete echo_;
}

Response Router::dispatch(const Request &request) const
{
    const std::map<std::string, const Handler *>::const_iterator found
        = routes_.find(key(request.method, request.target));
    if (found == routes_.end())
        return Response(404, "찾을 수 없습니다\n");
    return found->second->handle(request);
}
