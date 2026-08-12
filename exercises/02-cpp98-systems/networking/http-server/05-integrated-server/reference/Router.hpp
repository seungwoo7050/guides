#ifndef ROUTER_HPP
#define ROUTER_HPP

#include <map>
#include <stdexcept>
#include <string>
#include <vector>

// [Implementation 2] 설정 원문을 검증된 route key와 handler name의 immutable lookup 계약으로 변환합니다.
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

    bool resolve(
        const std::string &method,
        const std::string &path,
        std::string &handler) const;

private:
    static std::string key(
        const std::string &method,
        const std::string &path);

    std::map<std::string, std::string> routes_;
};

#endif
