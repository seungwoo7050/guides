#include "CommandService.hpp"
#include "RequestParser.hpp"
#include "ResponseFormatter.hpp"

#include <iostream>
#include <string>

// [Implementation 6] composition root에서 parser, service, formatter를 연결하고 main은 I/O와 종료만 소유합니다.
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
