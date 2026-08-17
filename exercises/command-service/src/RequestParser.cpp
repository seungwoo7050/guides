#include "RequestParser.hpp"
#include "Errors.hpp"

#include <sstream>

namespace
{
void requireArity(const Request &request, std::size_t expected)
{
    if (request.arguments.size() != expected)
        throw ParseError("invalid command arity");
}
}

// [Implementation 4] Validated request parsing
// The parser consumes one line and returns only supported commands with valid arity.
Request RequestParser::parse(const std::string &line) const
{
    Request request;
    std::istringstream input(line);
    if (!(input >> request.command))
        throw ParseError("empty request");

    std::string argument;
    while (input >> argument)
        request.arguments.push_back(argument);

    if (request.command == "PUT")
        requireArity(request, 2);
    else if (request.command == "GET" || request.command == "DELETE")
        requireArity(request, 1);
    else if (request.command == "COUNT" || request.command == "LIST" ||
             request.command == "QUIT")
        requireArity(request, 0);
    else
        throw ParseError("unsupported command");

    return request;
}
