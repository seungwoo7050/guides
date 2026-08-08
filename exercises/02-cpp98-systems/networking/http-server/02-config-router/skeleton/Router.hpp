#ifndef ROUTER_HPP
#define ROUTER_HPP

#include <map>
#include <stdexcept>
#include <string>
#include <vector>

struct Request
{
    std::string method;
    std::string target;
    std::string body;

    Request(
        const std::string &requestMethod = "",
        const std::string &requestTarget = "",
        const std::string &requestBody = "")
        : method(requestMethod),
          target(requestTarget),
          body(requestBody)
    {
    }
};

struct Response
{
    int status;
    std::string body;

    Response(int responseStatus = 500, const std::string &responseBody = "")
        : status(responseStatus), body(responseBody)
    {
    }
};

class Handler
{
public:
    virtual ~Handler() {}
    virtual Response handle(const Request &request) const = 0;
};

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
    ~Router();

    Response dispatch(const Request &request) const;

private:
    Router(const Router &);
    Router &operator=(const Router &);

    static std::string key(
        const std::string &method,
        const std::string &path);

    std::map<std::string, const Handler *> routes_;
    Handler *health_;
    Handler *echo_;
};

#endif
