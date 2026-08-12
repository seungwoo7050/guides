#include "HttpParser.hpp"

#include <iostream>
#include <string>

// [Implementation 6] 하나의 요청을 두 feed로 나눠 NeedMore에서 Complete로 바뀌는 증분 상태를 관찰합니다.
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
