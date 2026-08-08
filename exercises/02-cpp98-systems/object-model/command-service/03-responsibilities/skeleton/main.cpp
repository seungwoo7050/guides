#include "CommandService.hpp"
#include "RequestParser.hpp"
#include "ResponseFormatter.hpp"

#include <iostream>
#include <string>

int main()
{
    KeyValueStore store(2);
    CommandService service(store);
    RequestParser parser;
    ResponseFormatter formatter;

    std::string line;
    while (std::getline(std::cin, line))
    {
        const Request request = parser.parse(line);
        const Response response = service.execute(request);
        std::cout << formatter.format(response) << '\n';

        if (response.code == Response::Bye)
            break;
    }
    return 0;
}
