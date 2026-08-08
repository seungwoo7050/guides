#include "HttpParser.hpp"

#include <stdexcept>

HttpParser::HttpParser()
    : buffer_(), error_(), ready_(), hasReady_(false)
{
}

HttpParser::Result HttpParser::feed(
    const char *data,
    std::size_t size)
{
    if (size != 0)
        buffer_.append(data, size);

    // TODO:
    // 1. CRLF로 끝나는 요청 줄과 헤더를 찾으세요.
    // 2. 헤더 이름과 Content-Length를 검증하세요.
    // 3. 본문이 모두 도착할 때까지 기다리세요.
    // 4. 다음 요청에 속한 바이트를 보존하세요.
    return NeedMore;
}

HttpRequest HttpParser::take()
{
    if (!hasReady_)
        throw std::logic_error("완성된 요청이 없습니다");

    hasReady_ = false;
    return ready_;
}

const std::string &HttpParser::error() const
{
    return error_;
}
