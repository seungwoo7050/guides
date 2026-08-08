#include "Router.hpp"

#include <iostream>

int main()
{
    ConfigParser parser;
    Router router(parser.parse(
        "route GET /health health;\n"
        "route POST /echo echo;\n"));

    const Response health = router.dispatch(Request("GET", "/health"));
    const Response echo = router.dispatch(
        Request("POST", "/echo", "payload"));

    std::cout << health.status << ' ' << health.body
              << echo.status << ' ' << echo.body << '\n';
}
