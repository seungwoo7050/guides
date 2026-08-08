#include "HttpParser.hpp"

#include <cassert>
#include <iostream>
#include <stdexcept>
#include <string>

static void partialBodyAndNormalizedHeaders()
{
    HttpParser parser;
    const std::string first
        = "POST /echo HTTP/1.1\r\n"
          "Host: local\r\n"
          "Content-Length: 5\r\n\r\nhe";

    assert(parser.feed(first) == HttpParser::NeedMore);
    assert(parser.feed("llo", 3) == HttpParser::Complete);

    const HttpRequest request = parser.take();
    assert(request.method == "POST");
    assert(request.target == "/echo");
    assert(request.body == "hello");
    assert(request.headers.find("host") != request.headers.end());
    assert(request.headers.find("Host") == request.headers.end());
}

static void pipelinedRequests()
{
    HttpParser parser;
    const std::string both
        = "GET /a HTTP/1.1\r\nHost: x\r\n\r\n"
          "GET /b HTTP/1.1\r\nHost: x\r\n\r\n";

    assert(parser.feed(both) == HttpParser::Complete);
    assert(parser.take().target == "/a");
    assert(parser.feed("", 0) == HttpParser::Complete);
    assert(parser.take().target == "/b");
}

static void http10WithoutHost()
{
    HttpParser parser;
    assert(parser.feed("GET / HTTP/1.0\r\n\r\n")
        == HttpParser::Complete);
    assert(parser.take().version == "HTTP/1.0");
}

static void expectError(const std::string &message)
{
    HttpParser parser;
    assert(parser.feed(message) == HttpParser::Error);
    assert(!parser.error().empty());
    assert(parser.feed("", 0) == HttpParser::Error);
}

static void failureCases()
{
    expectError("GET / HTTP/1.1\r\nBroken\r\n\r\n");
    expectError("GET / HTTP/9.9\r\nHost: x\r\n\r\n");
    expectError("POST / HTTP/1.1\r\nHost: x\r\n"
                "Content-Length: nope\r\n\r\n");
    expectError("GET / HTTP/1.1\r\n\r\n");
    expectError("GET / HTTP/1.1\r\nHost: x\r\nHost: y\r\n\r\n");
    expectError("POST / HTTP/1.1\r\nHost: x\r\n"
                "Transfer-Encoding: chunked\r\n\r\n");

    HttpParser parser;
    bool threw = false;
    try
    {
        parser.take();
    }
    catch (const std::logic_error &)
    {
        threw = true;
    }
    assert(threw);
}

static std::string requestWithHeaderCount(std::size_t count)
{
    std::string request = "GET / HTTP/1.1\r\n";
    for (std::size_t index = 0; index < count; ++index)
    {
        if (index == 0)
            request += "Host: local\r\n";
        else
        {
            request += "X-Field-";
            request += static_cast<char>('a' + (index % 26));
            request += "-";
            request += static_cast<char>('0' + ((index / 26) % 10));
            request += ": value\r\n";
        }
    }
    request += "\r\n";
    return request;
}

static void sizeAndFragmentLimits()
{
    const std::string prefix
        = "GET / HTTP/1.1\r\nHost: local\r\nX-Fill: ";
    const std::size_t maximumHeaderBytes = 8192;

    HttpParser exact;
    const std::string exactRequest
        = prefix
        + std::string(maximumHeaderBytes - prefix.size(), 'a')
        + "\r\n\r\n";
    assert(exact.feed(exactRequest) == HttpParser::Complete);
    const HttpRequest exactParsed = exact.take();
    assert(exactParsed.headers.find("x-fill") !=
        exactParsed.headers.end());

    HttpParser oversized;
    const std::string oversizedRequest
        = prefix
        + std::string(maximumHeaderBytes - prefix.size() + 1, 'a')
        + "\r\n\r\n";
    assert(oversized.feed(oversizedRequest) == HttpParser::Error);

    HttpParser fragmented;
    assert(fragmented.feed(std::string(maximumHeaderBytes, 'a'))
        == HttpParser::NeedMore);
    assert(fragmented.feed("b") == HttpParser::Error);

    HttpParser maximumCount;
    assert(maximumCount.feed(requestWithHeaderCount(100))
        == HttpParser::Complete);
    maximumCount.take();

    HttpParser tooMany;
    assert(tooMany.feed(requestWithHeaderCount(101)) == HttpParser::Error);

    expectError(
        "POST / HTTP/1.1\r\nHost: x\r\n"
        "Content-Length: 184467440737095516160\r\n\r\n"
    );
    expectError(
        "POST / HTTP/1.1\r\nHost: x\r\n"
        "Content-Length: 1048577\r\n\r\n"
    );

    HttpParser nullInput;
    assert(nullInput.feed(0, 1) == HttpParser::Error);
}

int main(int argc, char **argv)
{
    static_cast<void>(argv);
    partialBodyAndNormalizedHeaders();
    pipelinedRequests();
    http10WithoutHost();
    failureCases();
    sizeAndFragmentLimits();

    std::cout << (argc > 1
        ? "HTTP 파서 실패 경로 검사: 통과"
        : "HTTP 파서 검사: 통과")
              << '\n';
}
