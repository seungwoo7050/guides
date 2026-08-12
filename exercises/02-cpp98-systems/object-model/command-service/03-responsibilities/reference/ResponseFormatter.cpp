#include "ResponseFormatter.hpp"

#include <sstream>

// [Implementation 5] 구조화된 Response를 외부 protocol 문자열로 바꾸는 책임을 상태 규칙과 분리합니다.
std::string ResponseFormatter::format(const Response &response) const
{
    std::ostringstream output;

    switch (response.code)
    {
    case Response::Ok:
        output << "OK";
        break;
    case Response::Value:
        output << "VALUE " << response.value;
        break;
    case Response::Full:
        output << "FULL";
        break;
    case Response::Deleted:
        output << "DELETED";
        break;
    case Response::NotFound:
        output << "NOT_FOUND";
        break;
    case Response::Count:
        output << "COUNT " << response.count;
        break;
    case Response::Bye:
        output << "BYE";
        break;
    default:
        output << "BAD_REQUEST";
        break;
    }

    return output.str();
}
