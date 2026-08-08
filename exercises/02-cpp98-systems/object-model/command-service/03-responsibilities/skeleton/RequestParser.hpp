#ifndef REQUESTPARSER_HPP
#define REQUESTPARSER_HPP

#include "Request.hpp"

#include <string>

class RequestParser
{
public:
    Request parse(const std::string &line) const;
};

#endif
