#include "ResponseFormatter.hpp"

std::string ResponseFormatter::format(const Response &response) const
{
    static_cast<void>(response);
    // TODO: 각 Response::Code를 안정된 외부 문자열 하나로 바꾸세요.
    return "BAD_REQUEST";
}
