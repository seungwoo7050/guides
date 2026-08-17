#include "Router.hpp"

#include <set>
#include <sstream>

namespace
{
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
    return method == "GET" || method == "POST";
}

bool supportedHandler(const std::string &handler)
{
    return handler == "health" || handler == "echo" || handler == "cgi";
}
} // namespace

// [Implementation 2-1] Transactional route parsing
// Every directive and duplicate is validated before handler-name lookup becomes visible.
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
            throw ConfigError("missing semicolon");
        line.erase(line.size() - 1);

        std::istringstream row(line);
        std::string directive;
        std::string extra;
        RouteSpec spec;
        if (!(row >> directive >> spec.method >> spec.path >> spec.handler) ||
            row >> extra || directive != "route")
        {
            throw ConfigError("invalid route directive");
        }
        if (!supportedMethod(spec.method))
            throw ConfigError("unsupported HTTP method");
        if (spec.path.empty() || spec.path[0] != '/')
            throw ConfigError("route path must start with /");
        if (!supportedHandler(spec.handler))
            throw ConfigError("unknown handler");

        const std::string routeKey = spec.method + " " + spec.path;
        if (!seen.insert(routeKey).second)
            throw ConfigError("duplicate route");
        candidate.push_back(spec);
    }

    if (candidate.empty())
        throw ConfigError("configuration contains no routes");
    return candidate;
}

std::string Router::key(const std::string &method, const std::string &path)
{
    return method + " " + path;
}

Router::Router(const std::vector<RouteSpec> &specs) : routes_()
{
    for (std::size_t i = 0; i < specs.size(); ++i)
    {
        routes_.insert(std::make_pair(
            key(specs[i].method, specs[i].path), specs[i].handler));
    }
}

bool Router::resolve(const std::string &method, const std::string &path,
                     std::string &handler) const
{
    const std::map<std::string, std::string>::const_iterator found =
        routes_.find(key(method, path));
    if (found == routes_.end())
        return false;
    handler = found->second;
    return true;
}
