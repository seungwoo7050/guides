#include "Errors.hpp"
#include "RequestParser.hpp"
#include "ResponseFormatter.hpp"
#include "Router.hpp"
#include "Store.hpp"

#include <cerrno>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

namespace
{
std::size_t parseCapacity(const char *text)
{
    char *end = 0;
    errno = 0;
    const unsigned long value = std::strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value == 0 ||
        value > static_cast<unsigned long>(INT_MAX))
    {
        throw std::invalid_argument("invalid capacity");
    }
    return static_cast<std::size_t>(value);
}
}

// [Implementation 8] Process composition and error translation
// The composition root translates internal failures into stable protocol responses.
int main(int argc, char **argv)
{
    if (argc > 2)
    {
        std::cerr << "usage: command_service [capacity]\n";
        return 2;
    }

    try
    {
        const std::size_t capacity = argc == 2 ? parseCapacity(argv[1]) : 1024;
        Store store(capacity);
        Router router;
        RequestParser parser;
        ResponseFormatter formatter;

        std::string line;
        while (std::getline(std::cin, line))
        {
            try
            {
                const Request request = parser.parse(line);
                const Handler *handler = router.find(request.command);
                if (handler == 0)
                    throw std::logic_error("validated command has no handler");

                const Response response = handler->handle(request, store);
                std::cout << formatter.format(response) << '\n';
                if (response.code == Response::Bye)
                    break;
            }
            catch (const ParseError &)
            {
                std::cout << "BAD_REQUEST\n";
            }
            catch (const ConflictError &)
            {
                std::cout << "CONFLICT\n";
            }
            catch (const StoreFullError &)
            {
                std::cout << "FULL\n";
            }
            catch (const std::exception &)
            {
                // 내부 진단 문자열은 protocol 응답으로 노출하지 않는다.
                std::cout << "INTERNAL_ERROR\n";
            }
        }
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << "command service startup failed: " << error.what() << '\n';
        return 2;
    }
}
