#include "CommandService.hpp"
#include "KeyValueStore.hpp"
#include "RequestParser.hpp"
#include "ResponseFormatter.hpp"

#include <cassert>
#include <string>

int main()
{
    KeyValueStore store(2);
    RequestParser parser;
    CommandService service(store);
    ResponseFormatter formatter;

    assert(formatter.format(service.execute(parser.parse("PUT a 1"))) == "OK");
    assert(formatter.format(service.execute(parser.parse("PUT b 2"))) == "OK");
    assert(formatter.format(service.execute(parser.parse("PUT c 3"))) == "FULL");
    assert(formatter.format(service.execute(parser.parse("GET a"))) == "VALUE 1");
    assert(formatter.format(service.execute(parser.parse("DELETE a"))) == "DELETED");
    assert(formatter.format(service.execute(parser.parse("COUNT"))) == "COUNT 1");
    assert(formatter.format(service.execute(parser.parse("PUT only-key")))
        == "BAD_REQUEST");
}
