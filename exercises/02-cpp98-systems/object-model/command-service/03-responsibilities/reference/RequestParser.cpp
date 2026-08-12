#include "RequestParser.hpp"

#include <sstream>
#include <vector>

// [Implementation 3] 외부 문자열 문법을 검증해 유효한 Request 또는 Invalid 값으로만 변환합니다.
Request RequestParser::parse(const std::string &line) const
{
    std::istringstream input(line);
    std::vector<std::string> parts;
    std::string part;

    while (input >> part)
        parts.push_back(part);

    if (parts.size() == 3 && parts[0] == "PUT")
        return Request(Request::Put, parts[1], parts[2]);
    if (parts.size() == 2 && parts[0] == "GET")
        return Request(Request::Get, parts[1]);
    if (parts.size() == 2 && parts[0] == "DELETE")
        return Request(Request::Delete, parts[1]);
    if (parts.size() == 1 && parts[0] == "COUNT")
        return Request(Request::Count);
    if (parts.size() == 1 && parts[0] == "QUIT")
        return Request(Request::Quit);

    return Request();
}
