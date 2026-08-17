#ifndef HTTP_SERVER_ROUTER_HPP
#define HTTP_SERVER_ROUTER_HPP

#include <map>
#include <stdexcept>
#include <string>
#include <vector>

// [Implementation 2] Route configuration contract
// Configuration becomes an immutable exact route-key to handler-name contract.
class ConfigError : public std::runtime_error
{
public:
    explicit ConfigError(const std::string &message)
        : std::runtime_error(message)
    {
    }
};

struct RouteSpec
{
    std::string method;
    std::string path;
    std::string handler;
};

class ConfigParser
{
public:
    std::vector<RouteSpec> parse(const std::string &text) const;
};

class Router
{
public:
    explicit Router(const std::vector<RouteSpec> &specs);

    bool resolve(const std::string &method, const std::string &path,
                 std::string &handler) const;

private:
    static std::string key(const std::string &method, const std::string &path);
    std::map<std::string, std::string> routes_;
};

#endif
