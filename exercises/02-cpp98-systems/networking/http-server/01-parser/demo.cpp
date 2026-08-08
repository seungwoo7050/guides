#include "HttpParser.hpp"

#include <iostream>
#include <string>

int main()
{
    HttpParser parser;
    const std::string first = "GET /health HTTP/1.1\r\nHo";
    const std::string second = "st: local\r\n\r\n";

    std::cout << (parser.feed(first) == HttpParser::NeedMore
        ? "need more"
        : "unexpected")
              << '\n';
    std::cout << (parser.feed(second) == HttpParser::Complete
        ? "complete"
        : "unexpected")
              << '\n';

    const HttpRequest request = parser.take();
    std::cout << request.method << ' '
              << request.target << ' '
              << request.version << '\n';
}
