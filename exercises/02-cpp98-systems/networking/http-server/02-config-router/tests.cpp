#include "Router.hpp"

#include <cassert>
#include <iostream>
#include <string>

static const char *ValidConfig
    = "route GET /health health;\n"
      "route POST /echo echo;\n";

static void normalCases()
{
    ConfigParser parser;
    const std::vector<RouteSpec> specs = parser.parse(ValidConfig);
    Router router(specs);

    const Response health = router.dispatch(Request("GET", "/health"));
    assert(health.status == 200 && health.body == "ok\n");

    const Response echo = router.dispatch(
        Request("POST", "/echo", "abc"));
    assert(echo.status == 200 && echo.body == "abc");

    assert(router.dispatch(Request("GET", "/missing")).status == 404);
}

static void expectConfigError(const std::string &config)
{
    ConfigParser parser;
    bool threw = false;
    try
    {
        parser.parse(config);
    }
    catch (const ConfigError &)
    {
        threw = true;
    }
    assert(threw);
}

static void failureCases()
{
    expectConfigError("route GET /x nope;\n");
    expectConfigError(
        "route GET /x health;\n"
        "route GET /x echo;\n");
    expectConfigError("route GET relative health;\n");
    expectConfigError("route PATCH /x echo;\n");
    expectConfigError("route GET /x health\n");
    expectConfigError("# comments only\n");
}

int main(int argc, char **argv)
{
    static_cast<void>(argv);
    normalCases();
    failureCases();

    std::cout << (argc > 1
        ? "설정 파서 실패 경로 검사: 통과"
        : "설정과 라우터 검사: 통과")
              << '\n';
}
