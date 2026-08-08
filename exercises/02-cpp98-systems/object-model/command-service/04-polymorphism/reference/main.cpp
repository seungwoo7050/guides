#include "Router.hpp"

#include <iostream>
#include <string>

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
