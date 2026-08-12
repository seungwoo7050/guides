#include "Router.hpp"

#include <iostream>

// [Implementation 6] 짧은 설정을 실제 Router로 구성해 health와 echo 선택 결과를 관찰합니다.
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
