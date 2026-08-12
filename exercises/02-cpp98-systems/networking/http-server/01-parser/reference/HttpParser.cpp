#include "HttpParser.hpp"

#include <cctype>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace
{
// [Implementation 2] protocol 상한과 header token/value/body-length helper를 socket과 독립된 순수 검증 계층으로 둡니다.
const std::size_t MaxHeaderBytes = 8192;
const std::size_t MaxBodyBytes = 1024 * 1024;
const std::size_t MaxHeaderCount = 100;

std::string lowercase(std::string text)
{
    for (std::size_t i = 0; i < text.size(); ++i)
    {
        text[i] = static_cast<char>(
            std::tolower(static_cast<unsigned char>(text[i])));
    }
    return text;
}

std::string trimOptionalWhitespace(const std::string &text)
{
    const std::size_t first = text.find_first_not_of(" \t");
    if (first == std::string::npos)
        return "";
    const std::size_t last = text.find_last_not_of(" \t");
    return text.substr(first, last - first + 1);
}

bool isTokenCharacter(char character)
{
    const unsigned char value = static_cast<unsigned char>(character);
    if (std::isalnum(value))
        return true;
    return std::string("!#$%&'*+-.^_`|~").find(character)
        != std::string::npos;
}

bool validHeaderName(const std::string &name)
{
    if (name.empty())
        return false;
    for (std::size_t i = 0; i < name.size(); ++i)
    {
        if (!isTokenCharacter(name[i]))
            return false;
    }
    return true;
}

bool validHeaderValue(const std::string &value)
{
    for (std::size_t i = 0; i < value.size(); ++i)
    {
        const unsigned char character
            = static_cast<unsigned char>(value[i]);
        if ((character < 32 && character != '\t') || character == 127)
            return false;
    }
    return true;
}

bool parseBodyLength(const std::string &text, std::size_t &result)
{
    if (text.empty())
        return false;

    std::size_t value = 0;
    for (std::size_t i = 0; i < text.size(); ++i)
    {
        if (text[i] < '0' || text[i] > '9')
            return false;

        const std::size_t digit
            = static_cast<std::size_t>(text[i] - '0');
        if (value > (std::numeric_limits<std::size_t>::max() - digit) / 10)
            return false;
        value = value * 10 + digit;
    }

    if (value > MaxBodyBytes)
        return false;
    result = value;
    return true;
}
}

HttpParser::HttpParser()
    : buffer_(), error_(), ready_(), hasReady_(false)
{
}

// [Implementation 3] ready/error 상태를 보존하면서 새 byte만 buffer에 추가하고 가능한 만큼 parsing을 진행합니다.
HttpParser::Result HttpParser::feed(
    const char *data,
    std::size_t size)
{
    if (hasReady_)
        return Complete;
    if (!error_.empty())
        return Error;
    if (size != 0)
    {
        if (data == 0)
            return fail("입력 포인터가 비어 있습니다");
        buffer_.append(data, size);
    }
    return parseAvailable();
}

// [Implementation 4] 요청 줄·header·body를 모두 검증한 뒤에만 request를 commit하고 pipeline 나머지는 buffer에 남깁니다.
HttpParser::Result HttpParser::parseAvailable()
{
    const std::size_t headerEnd = buffer_.find("\r\n\r\n");
    if (headerEnd == std::string::npos)
    {
        if (buffer_.size() > MaxHeaderBytes)
            return fail("헤더가 허용 크기를 넘었습니다");
        return NeedMore;
    }
    if (headerEnd > MaxHeaderBytes)
        return fail("헤더가 허용 크기를 넘었습니다");

    const std::string headerBlock = buffer_.substr(0, headerEnd);
    const std::size_t requestLineEnd = headerBlock.find("\r\n");
    const std::string requestLine = requestLineEnd == std::string::npos
        ? headerBlock
        : headerBlock.substr(0, requestLineEnd);

    HttpRequest request;
    std::istringstream requestInput(requestLine);
    std::string extra;
    if (!(requestInput >> request.method >> request.target >> request.version)
        || requestInput >> extra)
    {
        return fail("요청 줄이 올바르지 않습니다");
    }

    if (request.version != "HTTP/1.1"
        && request.version != "HTTP/1.0")
    {
        return fail("지원하지 않는 HTTP 버전입니다");
    }
    if (request.target.empty() || request.target[0] != '/')
        return fail("지원하지 않는 요청 대상입니다");

    std::size_t position = requestLineEnd == std::string::npos
        ? headerBlock.size()
        : requestLineEnd + 2;
    std::size_t headerCount = 0;

    while (position < headerBlock.size())
    {
        const std::size_t next = headerBlock.find("\r\n", position);
        const std::string line = headerBlock.substr(
            position,
            next == std::string::npos
                ? std::string::npos
                : next - position);

        const std::size_t colon = line.find(':');
        if (colon == std::string::npos || colon == 0)
            return fail("헤더 줄이 올바르지 않습니다");

        const std::string rawName = line.substr(0, colon);
        if (!validHeaderName(rawName))
            return fail("헤더 이름이 올바르지 않습니다");

        const std::string name = lowercase(rawName);
        const std::string value = trimOptionalWhitespace(
            line.substr(colon + 1));
        if (!validHeaderValue(value))
            return fail("헤더 값이 올바르지 않습니다");
        if (request.headers.find(name) != request.headers.end())
            return fail("헤더가 중복되었습니다");

        request.headers.insert(std::make_pair(name, value));
        ++headerCount;
        if (headerCount > MaxHeaderCount)
            return fail("헤더 수가 허용 범위를 넘었습니다");

        if (next == std::string::npos)
            break;
        position = next + 2;
    }

    if (request.version == "HTTP/1.1"
        && request.headers.find("host") == request.headers.end())
    {
        return fail("Host 헤더가 없습니다");
    }

    if (request.headers.find("transfer-encoding")
        != request.headers.end())
    {
        return fail("Transfer-Encoding은 지원하지 않습니다");
    }

    std::size_t bodyLength = 0;
    const std::map<std::string, std::string>::const_iterator lengthHeader
        = request.headers.find("content-length");
    if (lengthHeader != request.headers.end()
        && !parseBodyLength(lengthHeader->second, bodyLength))
    {
        return fail("Content-Length가 올바르지 않습니다");
    }

    const std::size_t messageSize = headerEnd + 4 + bodyLength;
    if (buffer_.size() < messageSize)
        return NeedMore;

    request.body = buffer_.substr(headerEnd + 4, bodyLength);
    buffer_.erase(0, messageSize);
    ready_ = request;
    hasReady_ = true;
    return Complete;
}

HttpParser::Result HttpParser::fail(const std::string &message)
{
    error_ = message;
    return Error;
}

// [Implementation 5] 완성된 request의 소유 값을 반환하고 parser를 다음 pipeline message를 받을 상태로 되돌립니다.
HttpRequest HttpParser::take()
{
    if (!hasReady_)
        throw std::logic_error("완성된 요청이 없습니다");

    const HttpRequest result = ready_;
    ready_ = HttpRequest();
    hasReady_ = false;
    return result;
}

const std::string &HttpParser::error() const
{
    return error_;
}
