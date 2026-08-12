#include "Router.hpp"

#include <iostream>
#include <string>

// [Implementation 4] main은 Request를 route한 뒤 구체 타입을 모른 채 Handler 계약으로 dispatch합니다.
int main()
{
    Router router;
    Store store;
    std::string line;

    while (std::getline(std::cin, line))
    {
        const Request request = parse(line);
        const Handler *handler = router.find(request.command);
        const std::string output = handler
            ? handler->handle(request, store)
            : "BAD_REQUEST";

        std::cout << output << '\n';
        if (output == "BYE")
            break;
    }
    return 0;
}
