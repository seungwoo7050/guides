#include "HttpParser.hpp"
#include "Router.hpp"

#include <cassert>
#include <string>
#include <vector>

int main()
{
    HttpParser parser;
    const std::string firstFragment = "POST /echo HTTP/1.1\r\nHost: local";
    assert(parser.feed(firstFragment) == HttpParser::NeedMore);
    assert(parser.feed("host\r\nContent-Length: 5\r\n\r\nhello"
                       "GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n") ==
           HttpParser::Complete);
    const HttpRequest first = parser.take();
    assert(first.method == "POST" && first.target == "/echo");
    assert(first.body == "hello");
    assert(parser.feed("", 0) == HttpParser::Complete);
    const HttpRequest second = parser.take();
    assert(second.method == "GET" && second.target == "/health");

    HttpParser invalid;
    assert(invalid.feed("GET / HTTP/1.1\r\n\r\n") == HttpParser::Error);
    assert(!invalid.error().empty());

    const std::vector<RouteSpec> specs = ConfigParser().parse(
        "route GET /health health;\n"
        "route POST /echo echo;\n"
        "route POST /cgi cgi;\n");
    const Router router(specs);
    std::string handler;
    assert(router.resolve("POST", "/echo", handler));
    assert(handler == "echo");
    assert(!router.resolve("GET", "/missing", handler));

    bool duplicateRejected = false;
    try
    {
        ConfigParser().parse(
            "route GET /health health;\n"
            "route GET /health health;\n");
    }
    catch (const ConfigError &)
    {
        duplicateRejected = true;
    }
    assert(duplicateRejected);
}
