#ifndef RESPONSEFORMATTER_HPP
#define RESPONSEFORMATTER_HPP

#include "Response.hpp"

#include <string>

class ResponseFormatter
{
public:
    std::string format(const Response &response) const;
};

#endif
