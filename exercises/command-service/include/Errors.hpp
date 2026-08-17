#ifndef COMMAND_SERVICE_ERRORS_HPP
#define COMMAND_SERVICE_ERRORS_HPP

#include <stdexcept>
#include <string>

// [Implementation 1] Domain failure taxonomy
// Parse, conflict, and capacity failures are distinct domain boundaries.
class ParseError : public std::runtime_error
{
public:
    explicit ParseError(const std::string &message)
        : std::runtime_error(message)
    {
    }
};

class ConflictError : public std::runtime_error
{
public:
    explicit ConflictError(const std::string &message)
        : std::runtime_error(message)
    {
    }
};

class StoreFullError : public std::runtime_error
{
public:
    explicit StoreFullError(const std::string &message)
        : std::runtime_error(message)
    {
    }
};

#endif
